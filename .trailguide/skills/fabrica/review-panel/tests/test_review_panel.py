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

SKILL = Path(__file__).resolve().parent.parent
SCRIPT = SKILL / 'scripts' / 'review_panel.py'
sys.path.insert(0, str(SCRIPT.parent))
import review_panel  # noqa: E402  (imported after the path is set)

REVIEW = {
    'verdict': 'blocking', 'summary': 'Checked the parser.',
    'findings': [{'id': 'F1', 'severity': 'blocking', 'category': 'defect', 'title': 'Off by one',
                  'file': 'app.py', 'line': '2', 'body': 'Drops the last item.', 'fix': 'Use <=.'}],
    'unverified': [],
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
        value = {'verdict': 'fix-first', 'summary': 'One blocking defect.', 'findings': [
            {'id': 'S1', 'severity': 'blocking', 'category': 'defect', 'title': 'Off by one', 'file': 'app.py',
             'line': '2', 'body': 'Confirmed.', 'fix': 'Use <=.', 'raised_by': names}],
            'dropped': [], 'questions': [{'question': 'Keep the old format?', 'why': 'Clients parse it.'}]}
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

    def test_validate_review_reports_an_unknown_severity(self):
        bad = json.loads(json.dumps(REVIEW))
        bad['findings'][0]['severity'] = 'critical'
        self.assertIn('findings[0].severity must be one of blocking, advisory', review_panel.validate_review(bad))

    def test_validate_synthesis_rejects_a_reviewer_not_in_the_run(self):
        value = {'verdict': 'ready', 'summary': 's', 'findings': [
            {'id': 'S1', 'severity': 'advisory', 'title': 't', 'body': 'b', 'raised_by': ['check-made-up']}]}
        problems = review_panel.validate_synthesis(value, {'check-docs'})
        self.assertTrue(any('check-made-up' in p for p in problems), problems)

    def test_normalize_derives_a_reviewers_verdict_from_its_findings(self):
        self.assertEqual(review_panel.normalize(dict(REVIEW, verdict='pass'))['verdict'], 'blocking')
        self.assertEqual(review_panel.normalize(dict(REVIEW, verdict='blocking', findings=[]))['verdict'], 'pass')

    def test_extract_json_skips_an_example_before_another_language_block(self):
        text = 'Example:\n```json\n{"example": true}\n```\nCode:\n```python\nx = 1\n```\nResult:\n```json\n{"final": 1}\n```'
        self.assertEqual(review_panel.extract_json(text), {'final': 1})

    def test_validate_synthesis_rejects_a_raised_by_entry_that_is_not_a_name(self):
        value = {'verdict': 'ready', 'summary': 's', 'findings': [
            {'id': 'S1', 'severity': 'advisory', 'category': 'defect', 'title': 't', 'body': 'b',
             'raised_by': [{'reviewer': 'check-docs'}]}]}
        self.assertTrue(review_panel.validate_synthesis(value, {'check-docs'}))

    def test_validate_synthesis_rejects_fix_first_without_a_blocking_finding(self):
        value = {'verdict': 'fix-first', 'summary': 's', 'findings': []}
        self.assertIn("verdict 'fix-first' needs a blocking finding", review_panel.validate_synthesis(value, set()))

    def test_validate_synthesis_rejects_questions_that_are_not_objects(self):
        value = {'verdict': 'needs-decision', 'summary': 's', 'findings': [], 'questions': ['Keep it?']}
        self.assertIn('questions[0].question must be a non-empty string', review_panel.validate_synthesis(value, set()))

    def test_validate_synthesis_rejects_ready_with_a_blocking_finding(self):
        value = {'verdict': 'ready', 'summary': 's', 'findings': [
            {'id': 'S1', 'severity': 'blocking', 'category': 'defect', 'title': 't', 'body': 'b', 'raised_by': ['check-docs']}]}
        self.assertIn("verdict can't be 'ready' while a finding is blocking", review_panel.validate_synthesis(value, {'check-docs'}))

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
