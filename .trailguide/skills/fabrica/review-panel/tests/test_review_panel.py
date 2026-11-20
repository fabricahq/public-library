#!/usr/bin/env python3
"""Tests for review_panel.py, with fake `claude` and `codex` commands standing in for real sessions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import urllib.error
import urllib.request

SKILL = Path(__file__).resolve().parent.parent
SCRIPT = SKILL / 'scripts' / 'review_panel.py'
sys.path.insert(0, str(SCRIPT.parent))
import review_panel  # noqa: E402  (imported after the path is set)

REVIEW = {
    'verdict': 'blocking', 'summary': 'Checked the parser.',
    'findings': [{'id': 'F1', 'severity': 'blocking', 'category': 'defect', 'title': 'Off by one',
                  'file': 'app.py', 'line': '2', 'body': 'Drops the last item.', 'fix': 'Use <=.'}],
    'unverified': [],
    'checks': [{'check': 'AC1: prints every item', 'result': 'not-met', 'evidence': 'The loop stops one short (F1).'}],
}

# The fake commands read their instructions from environment variables the tests set:
# FAKE_LOG (append each invocation's argv), FAKE_BAD_FIRST (reply without JSON until told the
# contract), FAKE_CODEX_FAIL (exit 1).
FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, re, sys
    if sys.argv[1:] == ['--help']:
        print('  --restricted  Restricted mode\\n  --tools <tools...>\\n  choices: "dontAsk"')
        sys.exit(0)
    prompt = sys.stdin.read()
    with open(os.environ['FAKE_LOG'], 'a') as log:
        log.write(json.dumps(['claude'] + sys.argv[1:]) + '\\n')
    print(json.dumps({'type': 'assistant', 'session_id': 'sess-1', 'message': {'content': [
        {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'app.py'}}]}}))
    if os.environ.get('FAKE_SEEN') and 'You are the synthesis step' not in prompt:
        with open(os.environ['FAKE_SEEN'], 'a') as seen:
            seen.write(json.dumps({'cwd': os.getcwd(), 'app': open('app.py').read()}) + '\\n')
    failing = os.environ.get('FAKE_FAIL_REVIEWER')
    if failing and f'You are **{failing}**' in prompt:
        print('rate limited', flush=True)
        sys.exit(1)
    if 'You are the synthesis step' in prompt and os.environ.get('FAKE_SYNTH_FAIL'):
        print('overloaded', flush=True)
        sys.exit(1)
    if 'You are the synthesis step' in prompt:
        names = re.findall(r'^## (check-[a-z-]+)$', prompt, re.M)
        value = {'verdict': 'fix-first', 'summary': 'One blocking defect.',
            'conclusions': [{'kind': 'fix', 'headline': 'Loop drops the last item', 'detail': None, 'findings': ['S1']}], 'findings': [
            {'id': 'S1', 'severity': 'blocking', 'category': 'defect', 'title': 'Off by one', 'file': 'app.py',
             'line': '2', 'body': 'Confirmed.', 'fix': 'Use <=.', 'merges': [n + ':F1' for n in names]}],
            'dropped': [], 'questions': [{'question': 'Keep the old format?', 'why': 'Clients parse it.', 'blocking': True}]}
        text = 'Done.\\n```json\\n' + json.dumps(value) + '\\n```'
    elif os.environ.get('FAKE_BAD_FIRST') and 'did not meet the output contract' not in prompt:
        text = 'I looked and it seems fine.'
    else:
        text = '```json\\n' + os.environ['FAKE_REVIEW'] + '\\n```'
    print(json.dumps({'type': 'result', 'subtype': 'success', 'session_id': 'sess-1', 'result': text,
                      'usage': {'input_tokens': 1000, 'output_tokens': 200}}))
''')

FAKE_CODEX = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    sys.stdin.read()
    with open(os.environ['FAKE_LOG'], 'a') as log:
        log.write(json.dumps(['codex'] + sys.argv[1:]) + '\\n')
    if os.environ.get('FAKE_CODEX_FAIL'):
        print('codex: not signed in', flush=True)
        sys.exit(1)
    out = sys.argv[sys.argv.index('-o') + 1]
    print(json.dumps({'type': 'thread.started', 'thread_id': 't-1'}))
    print(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'git diff'}}))
    print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 500, 'output_tokens': 50}}))
    with open(out, 'w') as f:
        f.write('```json\\n' + os.environ['FAKE_REVIEW'] + '\\n```')
''')


class PureHelpers(unittest.TestCase):
    def test_extract_json_takes_the_last_fenced_object(self):
        text = 'first\n```json\n{"a": 1}\n```\nthen\n```json\n{"b": 2}\n```'
        self.assertEqual(review_panel.extract_json(text), {'b': 2})

    def test_extract_json_falls_back_to_a_bare_object(self):
        self.assertEqual(review_panel.extract_json('Here: {"verdict": "pass"} done'), {'verdict': 'pass'})

    def test_extract_json_rejects_a_reply_without_an_object(self):
        with self.assertRaises(ValueError):
            review_panel.extract_json('looks fine to me')

    def test_validate_review_accepts_the_contract_example(self):
        self.assertEqual(review_panel.validate_review(REVIEW), [])

    def test_validate_review_rejects_a_long_summary_and_an_unknown_check_result(self):
        bad = dict(REVIEW, summary='x' * 401, checks=[{'check': 'AC1', 'result': 'mostly'}])
        problems = review_panel.validate_review(bad)
        self.assertIn('summary must be under 400 characters; put the detail in checks and findings', problems)
        self.assertIn('checks[0].result must be one of met, not-met, partly, unverified', problems)

    def test_validate_review_reports_an_unknown_severity(self):
        bad = json.loads(json.dumps(REVIEW))
        bad['findings'][0]['severity'] = 'critical'
        self.assertIn('findings[0].severity must be one of blocking, advisory', review_panel.validate_review(bad))

    def synthesis(self, **changes):
        value = {'verdict': 'fix-first', 'summary': 's', 'conclusions': [{'kind': 'fix', 'headline': 'Off by one', 'detail': 'Use <=.', 'findings': ['S1']}], 'findings': [
            {'id': 'S1', 'severity': 'blocking', 'category': 'defect', 'title': 't', 'body': 'b',
             'merges': ['check-docs:F1', 'check-rules:F1']}]}
        value.update(changes)
        return value

    def test_validate_synthesis_accepts_merged_duplicates(self):
        self.assertEqual(review_panel.validate_synthesis(self.synthesis(), {'check-docs': REVIEW, 'check-rules': REVIEW}), [])

    def test_validate_synthesis_rejects_a_merge_of_a_finding_no_reviewer_raised(self):
        value = self.synthesis()
        value['findings'][0]['merges'] = ['check-made-up:F1', 'check-docs:F1']
        problems = review_panel.validate_synthesis(value, {'check-docs': REVIEW})
        self.assertTrue(any('check-made-up:F1' in p for p in problems), problems)

    def test_validate_synthesis_rejects_a_reviewer_finding_left_unaccounted(self):
        value = self.synthesis()
        value['findings'][0]['merges'] = ['check-docs:F1']
        problems = review_panel.validate_synthesis(value, {'check-docs': REVIEW, 'check-rules': REVIEW})
        self.assertTrue(any('missing: check-rules:F1' in p for p in problems), problems)
        value['dropped'] = [{'reviewer': 'check-rules', 'finding': 'F1', 'reason': 'Already handled.'}]
        self.assertEqual(review_panel.validate_synthesis(value, {'check-docs': REVIEW, 'check-rules': REVIEW}), [])

    def test_validate_review_rejects_repeated_finding_ids(self):
        bad = json.loads(json.dumps(REVIEW))
        bad['findings'].append(dict(bad['findings'][0]))
        self.assertIn('finding ids must be unique; repeated: F1', review_panel.validate_review(bad))

    def test_validate_synthesis_rejects_a_finding_both_merged_and_dropped(self):
        value = self.synthesis(dropped=[{'reviewer': 'check-docs', 'finding': 'F1', 'reason': 'Duplicate.'}])
        problems = review_panel.validate_synthesis(value, {'check-docs': REVIEW, 'check-rules': REVIEW})
        self.assertTrue(any('listed more than once: check-docs:F1' in p for p in problems), problems)

    def test_validate_synthesis_rejects_a_drop_of_a_finding_no_reviewer_raised(self):
        value = self.synthesis(dropped=[{'reviewer': 'check-docs', 'finding': 'F9', 'reason': 'Wrong.'}])
        problems = review_panel.validate_synthesis(value, {'check-docs': REVIEW, 'check-rules': REVIEW})
        self.assertTrue(any("dropped names 'check-docs:F9'" in p for p in problems), problems)

    def test_validate_synthesis_ties_the_verdict_to_blocking_questions(self):
        reviews = {'check-docs': REVIEW, 'check-rules': REVIEW}
        merged = self.synthesis()['findings'][0]
        advisory = dict(merged, severity='advisory')
        ready = self.synthesis(verdict='ready', findings=[advisory], questions=[{'question': 'Q?', 'blocking': True}])
        self.assertIn("verdict can't be 'ready' while a question is blocking", review_panel.validate_synthesis(ready, reviews))
        decide = self.synthesis(verdict='needs-decision', findings=[advisory], questions=[{'question': 'Q?', 'blocking': False}])
        self.assertIn("verdict 'needs-decision' needs at least one blocking question", review_panel.validate_synthesis(decide, reviews))
        missing = self.synthesis(verdict='ready', findings=[advisory], questions=[{'question': 'Q?'}])
        self.assertIn('questions[0].blocking must be true or false', review_panel.validate_synthesis(missing, reviews))

    def test_report_lists_dropped_findings_blocking_first(self):
        advisory = dict(REVIEW['findings'][0], id='F2', severity='advisory', title='Minor')
        blocking = dict(REVIEW['findings'][0], severity='blocking', title='Major')
        state = {'target': {'label': 'x'}, 'reviewers': {'check-docs': {'status': 'done', 'result': {'findings': [blocking, advisory]}}},
                 'synthesis': {'result': {'verdict': 'ready', 'summary': 's', 'conclusions': ['c'], 'findings': [], 'questions': [],
                                          'dropped': [{'reviewer': 'check-docs', 'finding': 'F2', 'reason': 'Style only.'},
                                                      {'reviewer': 'check-docs', 'finding': 'F1', 'reason': 'Handled in tests.'}]}}}
        report = review_panel.report_markdown(state)
        self.assertIn('## Dropped by the synthesis', report)
        self.assertLess(report.index('check-docs:F1 [blocking] Major: Handled in tests.'), report.index('check-docs:F2 [advisory] Minor'))

    def test_live_server_needs_the_token_and_serves_the_fallback_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / 'reviewers' / 'check-docs' / 'fallback').mkdir(parents=True)
            (run_dir / 'reviewers' / 'check-docs' / 'events.jsonl').write_text('codex failed')
            (run_dir / 'reviewers' / 'check-docs' / 'fallback' / 'events.jsonl').write_text('claude ran')
            state = review_panel.State(run_dir / 'state.json', {'status': 'running'})
            server = review_panel.serve(state, run_dir, 0, 'tok')
            try:
                base = f'http://127.0.0.1:{server.server_address[1]}'
                get = lambda path: urllib.request.urlopen(base + path, timeout=5)
                self.assertEqual(get('/tok/').status, 200)
                self.assertEqual(json.loads(get('/tok/state.json').read())['status'], 'running')
                self.assertEqual(get('/tok/log/check-docs').read(), b'claude ran')
                for path in ('/wrong/', '/wrong/state.json', '/tok/log/..', '/tok/log/check-none'):
                    with self.assertRaises(urllib.error.HTTPError, msg=path) as caught:
                        get(path)
                    self.assertEqual(caught.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()

    def test_line_ranges_reads_the_shapes_reviewers_write(self):
        self.assertEqual(review_panel.line_ranges('42'), [(42, 42)])
        self.assertEqual(review_panel.line_ranges('472-484, 528'), [(472, 484), (528, 528)])
        self.assertEqual(review_panel.line_ranges(None), [])
        self.assertEqual(review_panel.line_ranges('1-500'), [(1, review_panel.SNIPPET_MAX_LINES)])

    def test_code_snippets_stay_inside_the_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'code'
            root.mkdir()
            (root / 'a.py').write_text(''.join(f'line {n}\n' for n in range(1, 11)))
            (Path(folder) / 'secret.txt').write_text('no')
            found = review_panel.code_snippets(root, [{'file': 'a.py', 'line': '5'}, {'file': '../secret.txt', 'line': '1'},
                                                      {'file': 'missing.py', 'line': '1'}])
        self.assertEqual(list(found), ['a.py:5'])
        self.assertEqual(found['a.py:5'][0]['lines'], ['line 3', 'line 4', 'line 5', 'line 6', 'line 7'])

    def test_parse_yaml_reads_scalars_lists_and_maps(self):
        text = 'reviewers:   # in order\n  - check-security\n  - "check-payments"\nsynthesis:\n  model: opus\n  effort: high\nflag: true\nsummary: "Checks #1: payments"\n'
        self.assertEqual(review_panel.parse_yaml(text, 'panel.yaml'),
                         {'reviewers': ['check-security', 'check-payments'], 'synthesis': {'model': 'opus', 'effort': 'high'}, 'flag': True,
                          'summary': 'Checks #1: payments'})

    def test_parse_yaml_names_the_line_it_cannot_read(self):
        with self.assertRaisesRegex(review_panel.PanelError, 'panel.yaml:2'):
            review_panel.parse_yaml('reviewers:\n  just text\n', 'panel.yaml')

    def roster(self):
        return {'reviewers': {'check-docs': {'summary': 'Docs', 'agent': {'harness': 'codex', 'model': 'm', 'effort': 'high'},
                                             'focus_text': 'Built-in docs focus.', 'source': 'built-in'},
                              'check-rules': {'summary': 'Rules', 'agent': {'harness': 'claude-code', 'model': 'opus', 'effort': 'default'},
                                              'focus_text': 'Built-in rules focus.', 'source': 'built-in'}},
                'synthesize': {'agent': {'harness': 'claude-code', 'model': 'opus', 'effort': 'high'}},
                'codex_fallback': {'harness': 'claude-code', 'model': 'opus', 'effort': 'high'}}

    def config_folder(self, files):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(folder)]))
        for name, text in files.items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text)
        return folder

    def test_repo_config_replaces_extends_adds_and_orders_reviewers(self):
        roster = self.roster()
        folder = self.config_folder({
            'panel.yaml': 'reviewers:\n  - check-payments\n  - check-docs\n  - check-rules\nsynthesis:\n  effort: max\n',
            'reviewers/check-docs.md': '---\nmodel: gpt-x\n---\nOur docs focus.\n',
            'reviewers/check-rules.md': '---\nmode: append\n---\nAlso check our ADRs.\n',
            'reviewers/check-payments.md': '---\nsummary: Checks payment flows\n---\nLook for double charges.\n',
        })
        review_panel.apply_repo_config(roster, folder, '.fabrica/review-panel')
        reviewers = roster['reviewers']
        self.assertEqual(list(reviewers), ['check-payments', 'check-docs', 'check-rules'])
        self.assertEqual(reviewers['check-docs']['focus_text'], 'Our docs focus.')
        self.assertEqual(reviewers['check-docs']['agent'], {'harness': 'codex', 'model': 'gpt-x', 'effort': 'high'})
        self.assertEqual(reviewers['check-docs']['source'], 'replaced by .fabrica/review-panel/reviewers/check-docs.md')
        self.assertIn('Built-in rules focus.', reviewers['check-rules']['focus_text'])
        self.assertIn('Also check our ADRs.', reviewers['check-rules']['focus_text'])
        self.assertEqual(reviewers['check-payments']['summary'], 'Checks payment flows')
        self.assertEqual(reviewers['check-payments']['agent']['harness'], 'claude-code')
        self.assertEqual(roster['synthesize']['agent']['effort'], 'max')

    def test_repo_config_errors_name_the_problem(self):
        cases = {
            'no reviewer named check-nope': {'panel.yaml': 'reviewers:\n  - check-nope\n'},
            'a new reviewer needs a summary': {'reviewers/check-new.md': 'Prompt only.\n'},
            'harness must be one of': {'reviewers/check-docs.md': '---\nharness: gemini\n---\nX\n'},
            'unknown setting colour': {'panel.yaml': 'colour: blue\n'},
            'mode append needs a built-in': {'reviewers/check-new.md': '---\nsummary: S\nmode: append\n---\nX\n'},
        }
        for message, files in cases.items():
            with self.subTest(message), self.assertRaisesRegex(review_panel.PanelError, message):
                review_panel.apply_repo_config(self.roster(), self.config_folder(files), '.fabrica/review-panel')

    def test_save_settings_writes_only_a_folder_the_next_run_accepts(self):
        repo = Path(tempfile.mkdtemp())
        folder = repo / '.fabrica' / 'review-panel'
        roster = review_panel.save_settings(repo, None, {'reviewers/check-docs.md': '---\nmodel: sonnet\n---\nOur docs.\n'}, [])
        self.assertTrue((folder / 'reviewers' / 'check-docs.md').exists())
        docs = roster['all']['reviewers']['check-docs']
        self.assertEqual((docs['file'], docs['agent']['model'], docs['file_body']), ('.fabrica/review-panel/reviewers/check-docs.md', 'sonnet', 'Our docs.'))
        self.assertTrue(docs['builtin'])
        with self.assertRaisesRegex(review_panel.PanelError, 'a new reviewer needs a summary'):
            review_panel.save_settings(repo, None, {'reviewers/check-new.md': 'Prompt only.\n'}, [])
        self.assertFalse((folder / 'reviewers' / 'check-new.md').exists())
        with self.assertRaisesRegex(review_panel.PanelError, 'can only write'):
            review_panel.save_settings(repo, None, {'../escape.md': 'x'}, [])
        roster = review_panel.save_settings(repo, None, {}, ['reviewers/check-docs.md'])
        self.assertFalse((folder / 'reviewers' / 'check-docs.md').exists())
        self.assertEqual(roster['all']['reviewers']['check-docs']['source'], 'built-in')

    def test_front_matter_only_keeps_the_built_in_prompt(self):
        roster = self.roster()
        review_panel.apply_repo_config(roster, self.config_folder({'reviewers/check-docs.md': '---\nmodel: sonnet\n---\n'}), '.fabrica/review-panel')
        self.assertEqual(roster['reviewers']['check-docs']['agent']['model'], 'sonnet')
        self.assertIn('Built-in docs focus.', roster['reviewers']['check-docs']['focus_text'])
        with self.assertRaisesRegex(review_panel.PanelError, 'a new reviewer needs a prompt'):
            review_panel.apply_repo_config(self.roster(), self.config_folder({'reviewers/check-new.md': '---\nsummary: S\n---\n'}), '.fabrica/review-panel')

    def test_roster_summary_keeps_reviewers_panel_yaml_leaves_out(self):
        repo = Path(tempfile.mkdtemp())
        roster = review_panel.save_settings(repo, None, {'panel.yaml': 'reviewers:\n  - check-docs\n'}, [])
        everyone = roster['all']['reviewers']
        self.assertEqual(list(everyone)[0], 'check-docs')
        self.assertTrue(everyone['check-docs']['included'])
        self.assertFalse(everyone['check-security']['included'])
        self.assertEqual(list(roster['reviewers']), ['check-docs'])

    def test_settings_endpoint_needs_its_token_and_a_json_body(self):
        repo = Path(tempfile.mkdtemp())
        state = review_panel.State(repo / 'state.json', {'roster': None, 'config': None})
        server = review_panel.serve(state, repo, 0, 'tok', repo, None)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_address[1]}'
        def post(path, body, kind='application/json'):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={'Content-Type': kind}, method='POST')
            try:
                with urllib.request.urlopen(request) as response:
                    return response.status, json.loads(response.read())
            except urllib.error.HTTPError as error:
                return error.code, None
        self.assertEqual(post('/wrong/settings', {})[0], 404)
        self.assertEqual(post('/tok/settings', {}, 'text/plain')[0], 415)
        status, reply = post('/tok/settings', {'files': {'reviewers/check-docs.md': '---\neffort: max\n---\nDocs.\n'}})
        self.assertEqual(status, 200)
        self.assertEqual(reply['roster']['reviewers']['check-docs']['agent']['effort'], 'max')
        self.assertTrue(reply['config']['found'])
        self.assertTrue((repo / '.fabrica' / 'review-panel' / 'reviewers' / 'check-docs.md').exists())

    def test_validate_synthesis_requires_scannable_conclusions(self):
        reviews = {'check-docs': REVIEW, 'check-rules': REVIEW}
        bad = [{'kind': 'maybe', 'headline': 'x' * 61, 'detail': 'y' * 201, 'findings': ['S9']}, 'A plain string']
        problems = review_panel.validate_synthesis(self.synthesis(conclusions=bad), reviews)
        for message in ('conclusions[0].kind must be one of fix, decide, check, note',
                        'conclusions[0].headline must be a few words under 60 characters',
                        'conclusions[0].detail must be one sentence under 200 characters, or null',
                        "conclusions[0].findings names 'S9', which is not one of your findings",
                        'conclusions[1] must be an object with kind, headline, detail, and findings'):
            self.assertIn(message, problems)

    def test_report_writes_conclusions_old_and_new(self):
        self.assertEqual(review_panel.conclusion_line('Old style.'), '- Old style.')
        item = {'kind': 'decide', 'headline': 'Who owns retries', 'detail': 'Both layers retry today.', 'findings': ['S2', 'S3']}
        self.assertEqual(review_panel.conclusion_line(item), '- **Decide:** Who owns retries. Both layers retry today. (S2, S3)')

    def test_normalize_synthesis_derives_raised_by_from_merges(self):
        value = review_panel.normalize_synthesis(self.synthesis())
        self.assertEqual(value['findings'][0]['raised_by'], ['check-docs', 'check-rules'])

    def test_normalize_derives_a_reviewers_verdict_from_its_findings(self):
        self.assertEqual(review_panel.normalize(dict(REVIEW, verdict='pass'))['verdict'], 'blocking')
        self.assertEqual(review_panel.normalize(dict(REVIEW, verdict='blocking', findings=[]))['verdict'], 'pass')

    def test_extract_json_skips_an_example_before_another_language_block(self):
        text = 'Example:\n```json\n{"example": true}\n```\nCode:\n```python\nx = 1\n```\nResult:\n```json\n{"final": 1}\n```'
        self.assertEqual(review_panel.extract_json(text), {'final': 1})

    def test_validate_synthesis_rejects_a_merge_entry_that_is_not_a_name(self):
        value = self.synthesis()
        value['findings'][0]['merges'] = [{'reviewer': 'check-docs'}]
        self.assertTrue(review_panel.validate_synthesis(value, {'check-docs': REVIEW}))

    def test_validate_synthesis_rejects_fix_first_without_a_blocking_finding(self):
        value = self.synthesis(findings=[])
        self.assertIn("verdict 'fix-first' needs a blocking finding", review_panel.validate_synthesis(value, {}))

    def test_validate_synthesis_rejects_questions_that_are_not_objects(self):
        value = self.synthesis(verdict='needs-decision', findings=[], questions=['Keep it?'])
        self.assertIn('questions[0].question must be a non-empty string', review_panel.validate_synthesis(value, {}))

    def test_validate_synthesis_rejects_ready_with_a_blocking_finding(self):
        problems = review_panel.validate_synthesis(self.synthesis(verdict='ready'), {'check-docs': REVIEW, 'check-rules': REVIEW})
        self.assertIn("verdict can't be 'ready' while a finding is blocking", problems)

    def test_normalize_turns_a_whole_number_line_into_a_string(self):
        value = review_panel.normalize({'findings': [{'line': 42}]})
        self.assertEqual(value['findings'][0]['line'], '42')

    def test_codex_failure_event_raises_with_its_message(self):
        with self.assertRaisesRegex(RuntimeError, 'quota'):
            review_panel.codex_event(json.dumps({'type': 'turn.failed', 'error': {'message': 'quota'}}), {})


class PanelRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.bin = root / 'bin'
        self.bin.mkdir()
        self.repo = root / 'repo'
        self.repo.mkdir()
        self.log = root / 'calls.jsonl'
        git = lambda *args: subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True)
        git('init', '-q', '-b', 'main')
        git('config', 'user.email', 'test@example.com')
        git('config', 'user.name', 'Test')
        (self.repo / 'app.py').write_text('items = [1, 2, 3]\n')
        git('add', '.')
        git('commit', '-qm', 'base')
        git('checkout', '-qb', 'feature')
        (self.repo / 'app.py').write_text('items = [1, 2, 3]\nfor i in range(len(items) - 1): print(items[i])\n')
        git('commit', '-qam', 'Print items')

    def tearDown(self):
        self.temp.cleanup()

    def install(self, name, source):
        path = self.bin / name
        path.write_text(source)
        path.chmod(0o755)

    def run_panel(self, *args, **env):
        environment = {**os.environ, 'PATH': f"{self.bin}:{os.path.dirname(sys.executable)}:/usr/bin:/bin",
                       'FAKE_LOG': str(self.log), 'FAKE_REVIEW': json.dumps(REVIEW), **env}
        result = subprocess.run([sys.executable, str(SCRIPT), 'run', '--base', 'main', '--no-serve', *args],
                                cwd=self.repo, env=environment, capture_output=True, text=True, timeout=120)
        runs = sorted((self.repo / '.git' / 'review-panel').iterdir())
        state = json.loads((runs[-1] / 'state.json').read_text())
        return result, state, runs[-1]

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_panel_runs_claude_and_codex_reviewers_then_synthesizes(self):
        self.install('claude', FAKE_CLAUDE)
        self.install('codex', FAKE_CODEX)
        result, state, run_dir = self.run_panel('--only', 'check-correctness,check-docs')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(state['status'], 'done')
        self.assertEqual({r['status'] for r in state['reviewers'].values()}, {'done'})
        self.assertEqual(state['reviewers']['check-correctness']['agent']['harness'], 'codex')
        self.assertEqual(state['synthesis']['result']['findings'][0]['raised_by'], ['check-correctness', 'check-docs'])
        report = (run_dir / 'report.md').read_text()
        self.assertIn('Verdict: **fix-first**', report)
        self.assertIn('Keep the old format?', report)
        self.assertIn('"status": "done"', (run_dir / 'report.html').read_text())
        self.assertEqual((run_dir / 'base' / 'app.py').read_text(), 'items = [1, 2, 3]\n')
        codex_call = next(c for c in self.calls() if c[0] == 'codex')
        self.assertIn('read-only', codex_call)
        # The finding window shows the cited code, read from the reviewed snapshot.
        excerpt = state['snippets']['app.py:2'][0]
        self.assertEqual((excerpt['start'], excerpt['focus']), (1, [2, 2]))
        self.assertIn('range(len(items) - 1)', excerpt['lines'][1])
        self.assertEqual(state['target']['repo_name'], 'repo')
        self.assertIsNone(state['target']['github'])
        self.assertIn('review_panel.py run --base main', state['target']['rerun'])

    def test_repo_panel_folder_customizes_the_run(self):
        self.install('claude', FAKE_CLAUDE)
        folder = self.repo / '.fabrica' / 'review-panel' / 'reviewers'
        folder.mkdir(parents=True)
        (folder.parent / 'panel.yaml').write_text('reviewers:\n  - check-team\n')
        (folder / 'check-team.md').write_text('---\nsummary: Checks our team conventions\n---\nUse snake_case everywhere.\n')
        result, state, run_dir = self.run_panel()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(list(state['reviewers']), ['check-team'])
        entry = state['reviewers']['check-team']
        self.assertEqual(entry['source'], 'added by .fabrica/review-panel/reviewers/check-team.md')
        self.assertEqual(entry['focus'], 'Checks our team conventions')
        self.assertTrue(state['config']['found'])
        self.assertIn('Use snake_case everywhere.', (run_dir / 'reviewers' / 'check-team' / 'prompt-1.md').read_text())

    def test_claude_reviewers_get_read_only_tools(self):
        self.install('claude', FAKE_CLAUDE)
        self.run_panel('--only', 'check-docs')
        call = self.calls()[0]
        self.assertIn('--restricted', call)
        self.assertIn('--strict-mcp-config', call)
        self.assertEqual(call[call.index('--tools') + 1], 'Read,Grep,Glob')
        denied = call[call.index('--disallowedTools') + 1:]
        for tool in ('Bash', 'Edit', 'Write'):
            self.assertIn(tool, denied)

    def test_codex_reviewers_run_on_claude_when_codex_is_missing(self):
        self.install('claude', FAKE_CLAUDE)
        result, state, _ = self.run_panel('--only', 'check-correctness')
        self.assertEqual(result.returncode, 0, result.stderr)
        reviewer = state['reviewers']['check-correctness']
        self.assertEqual(reviewer['agent']['harness'], 'claude-code')
        self.assertIn('codex is not installed', reviewer['note'])

    def test_reply_that_breaks_the_contract_is_retried_in_the_same_claude_session(self):
        self.install('claude', FAKE_CLAUDE)
        result, state, _ = self.run_panel('--only', 'check-docs', FAKE_BAD_FIRST='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state['reviewers']['check-docs']['status'], 'done')
        reviewer_calls = self.calls()[:2]
        self.assertNotIn('--resume', reviewer_calls[0])
        self.assertEqual(reviewer_calls[1][reviewer_calls[1].index('--resume') + 1], 'sess-1')

    def test_a_failed_reviewer_is_reported_while_the_rest_of_the_panel_finishes(self):
        self.install('claude', FAKE_CLAUDE)
        result, state, run_dir = self.run_panel('--only', 'check-rules,check-docs', FAKE_FAIL_REVIEWER='check-rules')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state['reviewers']['check-rules']['status'], 'failed')
        self.assertIn('rate limited', state['reviewers']['check-rules']['error'])
        self.assertEqual(state['synthesis']['status'], 'done')
        self.assertEqual(state['synthesis']['result']['findings'][0]['raised_by'], ['check-docs'])
        self.assertIn('check-rules did not report', (run_dir / 'report.md').read_text())

    def test_a_failed_codex_session_reruns_the_reviewer_on_claude(self):
        self.install('claude', FAKE_CLAUDE)
        self.install('codex', FAKE_CODEX)
        result, state, _ = self.run_panel('--only', 'check-correctness', FAKE_CODEX_FAIL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        reviewer = state['reviewers']['check-correctness']
        self.assertEqual(reviewer['status'], 'done')
        self.assertEqual(reviewer['agent']['harness'], 'claude-code')
        self.assertIn('codex failed', reviewer['note'])
        self.assertIn('not signed in', reviewer['note'])

    def test_context_note_and_commit_messages_reach_the_reviewers(self):
        self.install('claude', FAKE_CLAUDE)
        spec = Path(self.temp.name) / 'spec.md'
        spec.write_text('AC1: print every item.\n')
        result, _, run_dir = self.run_panel('--only', 'check-docs', '--context', str(spec), '--note', 'Watch the loop bound.')
        self.assertEqual(result.returncode, 0, result.stderr)
        context = (run_dir / 'context.md').read_text()
        for text in ('AC1: print every item.', 'Watch the loop bound.', 'Print items'):
            self.assertIn(text, context)
        self.assertIn('AC1: print every item.', (run_dir / 'reviewers' / 'check-docs' / 'prompt-1.md').read_text())

    def test_a_reply_that_never_meets_the_contract_fails_after_the_retries(self):
        self.install('claude', FAKE_CLAUDE)
        result, state, _ = self.run_panel('--only', 'check-docs', '--retries', '1', FAKE_REVIEW='{"verdict": "pass"}')
        self.assertEqual(result.returncode, 1)
        reviewer = state['reviewers']['check-docs']
        self.assertEqual(reviewer['status'], 'failed')
        self.assertIn('invalid output', reviewer['error'])
        self.assertEqual(state['synthesis']['status'], 'skipped')

    def test_a_session_past_its_timeout_is_stopped(self):
        self.install('claude', '#!/bin/sh\n[ "$1" = --help ] && exit 0\nexec sleep 30\n')
        started = time.monotonic()
        result, state, _ = self.run_panel('--only', 'check-docs', '--timeout', '1')
        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual(result.returncode, 1)
        self.assertIn('timed out after 1 seconds', state['reviewers']['check-docs']['error'])

    def test_an_unreadable_context_file_is_a_usage_error(self):
        self.install('claude', FAKE_CLAUDE)
        environment = {**os.environ, 'PATH': f"{self.bin}:/usr/bin:/bin"}
        result = subprocess.run([sys.executable, str(SCRIPT), 'run', '--base', 'main', '--no-serve', '--context', '/nonexistent'],
                                cwd=self.repo, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('cannot read --context', result.stderr)

    def test_local_review_reads_a_snapshot_with_uncommitted_changes(self):
        self.install('claude', FAKE_CLAUDE)
        (self.repo / 'app.py').write_text('uncommitted\n')
        (self.repo / 'new.py').write_text('untracked\n')
        seen = Path(self.temp.name) / 'seen.jsonl'
        result, state, run_dir = self.run_panel('--only', 'check-docs', FAKE_SEEN=str(seen))
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(seen.read_text().splitlines()[0])
        self.assertEqual(view['cwd'], str(run_dir / 'worktree'))
        self.assertEqual(view['app'], 'uncommitted\n')
        self.assertIn('new.py', (run_dir / 'diff.patch').read_text())
        self.assertEqual(subprocess.run(['git', 'status', '--porcelain'], cwd=self.repo, capture_output=True, text=True).stdout,
                         ' M app.py\n?? new.py\n')
        self.assertFalse((run_dir / 'worktree').exists())
        self.assertEqual(subprocess.run(['git', 'stash', 'list'], cwd=self.repo, capture_output=True, text=True).stdout, '')

    def test_report_lists_reviewer_findings_when_synthesis_fails(self):
        self.install('claude', FAKE_CLAUDE)
        result, state, run_dir = self.run_panel('--only', 'check-docs', FAKE_SYNTH_FAIL='1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(state['synthesis']['status'], 'failed', state['reviewers'])
        report = (run_dir / 'report.md').read_text()
        self.assertIn('Synthesis failed', report)
        self.assertIn('F1 [blocking] Off by one app.py:2', report)

    def test_nothing_to_review_is_a_usage_error(self):
        self.install('claude', FAKE_CLAUDE)
        environment = {**os.environ, 'PATH': f"{self.bin}:/usr/bin:/bin"}
        subprocess.run(['git', 'checkout', '-q', 'main'], cwd=self.repo, check=True)
        result = subprocess.run([sys.executable, str(SCRIPT), 'run', '--base', 'main', '--no-serve'],
                                cwd=self.repo, env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('nothing to review', result.stderr)
        self.assertEqual(list((self.repo / '.git' / 'review-panel').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
