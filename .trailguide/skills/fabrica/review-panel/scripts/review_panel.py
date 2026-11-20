#!/usr/bin/env python3
"""Run a panel of reviewer sessions on a change, synthesize their findings, and show progress live.

Each reviewer is a separate headless Claude Code (`claude -p`) or Codex (`codex exec`) session with
read-only tools. The panel writes everything to a run directory: state.json (what the live page
polls), each reviewer's prompt, event log, and findings, the synthesis, and a standalone report.html.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL = Path(__file__).resolve().parent.parent
PAGE = SKILL / 'assets' / 'panel.html'
ROSTER = SKILL / 'panel.json'
SEVERITIES = ('blocking', 'advisory')
CATEGORIES = ('defect', 'policy', 'negligible-likelihood')
CHECK_RESULTS = ('met', 'not-met', 'partly', 'unverified')
REVIEW_VERDICTS = ('pass', 'concerns', 'blocking')
SYNTHESIS_VERDICTS = ('ready', 'fix-first', 'needs-decision')
# Claude sessions read untrusted text (the diff, a pull request's description, the files it adds), so they
# get file-reading tools only: no shell, no project settings or hooks, no MCP servers. The run directory
# holds the patch and the base versions of changed files, so reviewers need no Git commands.
# Codex sessions can run shell commands, inside a sandbox that blocks writes and network access; that is
# an accepted risk. --claude-only gives the stricter no-shell setup for untrusted pull requests.
CLAUDE_TOOLS = ['Read', 'Grep', 'Glob']
CLAUDE_DENIED = ['Bash', 'Edit', 'Write', 'NotebookEdit', 'WebFetch', 'WebSearch', 'Agent', 'Task']


class PanelError(Exception):
    """A problem the person running the panel can fix, reported without a traceback."""


# ---------------------------------------------------------------------------------------------
# Pure helpers: parsing and validating what sessions return.

def extract_json(text):
    """Return the JSON object a session ended its reply with.

    Sessions are asked for one fenced ```json block; take the last one, else the last balanced
    top-level object in the text.
    """
    if not text:
        raise ValueError('the session returned no text')
    fenced = re.findall(r'^```[^\n`]*\n(.*?)\n```[ \t]*$', text, re.S | re.M)
    for block in reversed(fenced):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    decoder = json.JSONDecoder()
    found = None
    index = text.find('{')
    while index != -1:
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            index = text.find('{', index + 1)
            continue
        if isinstance(value, dict):
            found = value
        index = text.find('{', end)
    if found is None:
        raise ValueError('the reply has no JSON object')
    return found


def _require(condition, message, problems):
    if not condition:
        problems.append(message)


def _check_finding(finding, where, problems):
    if not isinstance(finding, dict):
        problems.append(f'{where} is not an object')
        return
    for key in ('id', 'severity', 'category', 'title', 'body'):
        _require(isinstance(finding.get(key), str) and finding[key].strip(), f'{where}.{key} must be a non-empty string', problems)
    _require(finding.get('severity') in SEVERITIES, f'{where}.severity must be one of {", ".join(SEVERITIES)}', problems)
    _require(finding.get('category') in CATEGORIES, f'{where}.category must be one of {", ".join(CATEGORIES)}', problems)
    for key in ('file', 'line', 'fix'):
        if key in finding:
            _require(finding[key] is None or isinstance(finding[key], str), f'{where}.{key} must be a string or null', problems)


def validate_review(value):
    """Return the list of ways a reviewer's JSON breaks the reviewer contract (empty when valid)."""
    problems = []
    if not isinstance(value, dict):
        return ['the reply is not a JSON object']
    _require(value.get('verdict') in REVIEW_VERDICTS, f'verdict must be one of {", ".join(REVIEW_VERDICTS)}', problems)
    _require(isinstance(value.get('summary'), str) and value['summary'].strip(), 'summary must be a non-empty string', problems)
    findings = value.get('findings')
    _require(isinstance(findings, list), 'findings must be a list', problems)
    for index, finding in enumerate(findings if isinstance(findings, list) else []):
        _check_finding(finding, f'findings[{index}]', problems)
    _check_unique_ids(findings, problems)
    _check_items(value, 'unverified', ('claim', 'reason'), problems)
    _check_items(value, 'checks', ('check', 'result'), problems)
    for index, check in enumerate(value.get('checks') if isinstance(value.get('checks'), list) else []):
        if isinstance(check, dict):
            _require(check.get('result') in CHECK_RESULTS, f'checks[{index}].result must be one of {", ".join(CHECK_RESULTS)}', problems)
    _require(len(value.get('summary') or '') <= 400, 'summary must be under 400 characters; put the detail in checks and findings', problems)
    return problems


def _check_unique_ids(findings, problems):
    ids = [f.get('id') for f in findings if isinstance(f, dict)] if isinstance(findings, list) else []
    repeated = sorted({i for i in ids if isinstance(i, str) and ids.count(i) > 1})
    _require(not repeated, 'finding ids must be unique; repeated: ' + ', '.join(repeated), problems)


def _check_items(value, key, fields, problems):
    items = value.get(key, [])
    if not isinstance(items, list):
        problems.append(f'{key} must be a list')
        return
    for index, item in enumerate(items):
        for field in fields:
            _require(isinstance(item, dict) and isinstance(item.get(field), str) and item[field].strip(),
                     f'{key}[{index}].{field} must be a non-empty string', problems)


def validate_synthesis(value, reviews):
    """Return the list of ways the synthesis JSON breaks its contract (empty when valid).

    `reviews` maps each reviewer that reported to its review. Every reviewer finding must end up either
    merged into a synthesis finding or dropped with a reason, so nothing a reviewer raised goes missing.
    """
    known = {f'{name}:{f["id"]}' for name, review in reviews.items() for f in review.get('findings', [])}
    accounted = set()
    seen = []
    problems = []
    if not isinstance(value, dict):
        return ['the reply is not a JSON object']
    _require(value.get('verdict') in SYNTHESIS_VERDICTS, f'verdict must be one of {", ".join(SYNTHESIS_VERDICTS)}', problems)
    _require(isinstance(value.get('summary'), str) and value['summary'].strip(), 'summary must be a non-empty string', problems)
    findings = value.get('findings')
    _require(isinstance(findings, list), 'findings must be a list', problems)
    for index, finding in enumerate(findings if isinstance(findings, list) else []):
        where = f'findings[{index}]'
        _check_finding(finding, where, problems)
        merges = finding.get('merges') if isinstance(finding, dict) else None
        _require(isinstance(merges, list) and merges, f'{where}.merges must list the reviewer findings it covers, as "reviewer:F1"', problems)
        for ref in merges if isinstance(merges, list) else []:
            valid = isinstance(ref, str) and ref in known
            _require(valid, f'{where}.merges names {ref!r}, which is not a reviewer finding in the reports', problems)
            if valid:
                accounted.add(ref)
                seen.append(ref)
    _check_unique_ids(findings, problems)
    _require(len(value.get('summary') or '') <= 600, 'summary must be under 600 characters; put the detail in findings and questions', problems)
    conclusions = value.get('conclusions')
    _require(isinstance(conclusions, list) and 1 <= len(conclusions) <= 5, 'conclusions must list one to five short statements', problems)
    for index, line in enumerate(conclusions if isinstance(conclusions, list) else []):
        _require(isinstance(line, str) and line.strip() and len(line) <= 200, f'conclusions[{index}] must be a statement under 200 characters', problems)
    _check_items(value, 'dropped', ('reviewer', 'finding', 'reason'), problems)
    for item in value.get('dropped') if isinstance(value.get('dropped'), list) else []:
        if isinstance(item, dict):
            ref = f"{item.get('reviewer')}:{item.get('finding')}"
            _require(ref in known, f'dropped names {ref!r}, which is not a reviewer finding in the reports', problems)
            accounted.add(ref)
            seen.append(ref)
    repeated = sorted({ref for ref in seen if seen.count(ref) > 1})
    _require(not repeated, 'each reviewer finding belongs in exactly one finding\'s merges or in dropped; listed more than once: '
             + ', '.join(repeated[:10]), problems)
    missing = sorted(known - accounted)
    _require(not missing, 'every reviewer finding must be merged into a finding or dropped with a reason; missing: ' + ', '.join(missing[:10]), problems)
    _check_items(value, 'questions', ('question',), problems)
    questions = value.get('questions') if isinstance(value.get('questions'), list) else []
    for index, question in enumerate(questions):
        _require(isinstance(question, dict) and isinstance(question.get('blocking'), bool),
                 f'questions[{index}].blocking must be true or false', problems)
    blocking_question = any(isinstance(q, dict) and q.get('blocking') is True for q in questions)
    if isinstance(findings, list):
        blocking = any(isinstance(f, dict) and f.get('severity') == 'blocking' for f in findings)
        verdict = value.get('verdict')
        _require(not (verdict == 'ready' and blocking), "verdict can't be 'ready' while a finding is blocking", problems)
        _require(not (verdict == 'fix-first' and not blocking), "verdict 'fix-first' needs a blocking finding", problems)
        _require(not (verdict == 'needs-decision' and not blocking_question),
                 "verdict 'needs-decision' needs at least one blocking question", problems)
        _require(not (verdict == 'ready' and blocking_question), "verdict can't be 'ready' while a question is blocking", problems)
    return problems


def normalize_synthesis(value):
    """Derive each synthesis finding's raised_by from the reviewer findings it merges."""
    for finding in value.get('findings', []) if isinstance(value, dict) and isinstance(value.get('findings'), list) else []:
        if isinstance(finding, dict) and isinstance(finding.get('merges'), list):
            names = [ref.split(':', 1)[0] for ref in finding['merges'] if isinstance(ref, str)]
            finding['raised_by'] = list(dict.fromkeys(names))
    return value


def normalize(value):
    """Fix what the script can decide itself instead of asking a session again.

    A whole-number line becomes a string, and a reviewer's verdict follows from its findings' severities.
    """
    if not isinstance(value, dict) or not isinstance(value.get('findings'), list):
        return value
    findings = value['findings']
    for finding in findings:
        if isinstance(finding, dict) and isinstance(finding.get('line'), int):
            finding['line'] = str(finding['line'])
    if value.get('verdict') in REVIEW_VERDICTS:
        if any(isinstance(f, dict) and f.get('severity') == 'blocking' for f in findings):
            value['verdict'] = 'blocking'
        else:
            value['verdict'] = 'concerns' if findings else 'pass'
    return value


def summarize_tool_input(name, data):
    """A short label for what a session is doing, shown on its reviewer card."""
    if not isinstance(data, dict):
        return name
    for key in ('file_path', 'path', 'pattern', 'command', 'query'):
        if isinstance(data.get(key), str):
            return f'{name} {data[key]}'[:160]
    return name


def claude_event(line, usage):
    """Read one stream-json line from `claude -p`; return (activity, result_text, session_id).

    `usage` is updated in place with token counts.
    """
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None, None, None
    kind = event.get('type')
    if kind == 'assistant':
        message = event.get('message') or {}
        activity = None
        for part in message.get('content') or []:
            if part.get('type') == 'tool_use':
                activity = summarize_tool_input(part.get('name', 'tool'), part.get('input'))
        return activity, None, event.get('session_id')
    if kind == 'result':
        totals = event.get('usage') or {}
        usage['input'] = sum(int(totals.get(key) or 0) for key in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
        usage['output'] = int(totals.get('output_tokens') or 0)
        if event.get('is_error') or event.get('subtype') not in (None, 'success'):
            raise RuntimeError(f"claude ended with {event.get('subtype') or 'an error'}: {event.get('result') or ''}".strip())
        return None, event.get('result') or '', event.get('session_id')
    return None, None, event.get('session_id')


def codex_event(line, usage):
    """Read one --json line from `codex exec`; return (activity, final_text, thread_id)."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None, None, None
    kind = event.get('type', '')
    item = event.get('item') or {}
    if kind == 'thread.started':
        return None, None, event.get('thread_id')
    if kind == 'turn.completed':
        totals = event.get('usage') or {}
        usage['input'] = usage.get('input', 0) + int(totals.get('input_tokens') or 0)
        usage['output'] = usage.get('output', 0) + int(totals.get('output_tokens') or 0)
    if kind in ('turn.failed', 'error'):
        error = event.get('error') or {}
        raise RuntimeError(f"codex failed: {error.get('message') or event.get('message') or line.strip()}")
    if kind == 'item.started' and item.get('type') == 'command_execution':
        return f"$ {item.get('command', '')}"[:160], None, None
    if kind == 'item.completed' and item.get('type') == 'agent_message':
        return None, item.get('text'), None
    return None, None, None


# ---------------------------------------------------------------------------------------------
# Run state, shared with the live page.

class State:
    def __init__(self, path, data):
        self.path = path
        self.data = data
        self.lock = threading.Lock()
        self.version = 0
        self.served_version = None  # The version the live page last fetched; None until it fetches one.
        self.save()

    def update(self, change):
        with self.lock:
            change(self.data)
            self.data['updated_at'] = now()
            self.version += 1
            self._write()

    def save(self):
        with self.lock:
            self._write()

    def snapshot(self):
        with self.lock:
            return json.dumps(self.data, ensure_ascii=False)

    def serve_snapshot(self):
        with self.lock:
            self.served_version = self.version
            return json.dumps(self.data, ensure_ascii=False)

    def _write(self):
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.state-')
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.data, stream, ensure_ascii=False, indent=2)
        os.replace(name, self.path)


def add_usage(first, second):
    return {key: first.get(key, 0) + second.get(key, 0) for key in set(first) | set(second)}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


# ---------------------------------------------------------------------------------------------
# Git: what is being reviewed.

# Plain unified diffs whatever the person's Git configuration says (external diff tools, textconv, color).
DIFF = ['diff', '--no-ext-diff', '--no-textconv', '--no-color']


def git(args, cwd, check=True, env=None, raw=False):
    result = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, errors='replace', env=env)
    if check and result.returncode != 0:
        raise PanelError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout if raw else result.stdout.strip()


def default_base(repo):
    ref = git(['symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD'], repo, check=False)
    if ref:
        return ref.replace('refs/remotes/', '')
    for candidate in ('origin/main', 'origin/master', 'main', 'master'):
        if git(['rev-parse', '--verify', '--quiet', candidate], repo, check=False):
            return candidate
    raise PanelError('could not find a base branch; pass --base')


def snapshot_commit(repo):
    """Record the working tree, with uncommitted and new untracked files, as a commit on top of HEAD.

    It uses a temporary index, so the person's index, working tree, branches, and stash are untouched;
    the commit is unreferenced, and Git's garbage collection removes it later. Ignored files are left out.
    """
    with tempfile.TemporaryDirectory() as temp:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temp) / 'index'),
               'GIT_AUTHOR_NAME': 'review-panel', 'GIT_AUTHOR_EMAIL': 'review-panel@localhost',
               'GIT_COMMITTER_NAME': 'review-panel', 'GIT_COMMITTER_EMAIL': 'review-panel@localhost'}
        git(['read-tree', 'HEAD'], repo, env=env)
        git(['add', '--all'], repo, env=env)
        tree = git(['write-tree'], repo, env=env)
        return git(['commit-tree', tree, '-p', 'HEAD', '-m', 'review-panel snapshot'], repo, env=env)


def prepare_target(args, repo, run_dir):
    """Return the target description and the worktree reviewers read code from.

    Both kinds of target come down to one commit range, merge_base..head, checked out in a worktree.
    """
    if args.pr:
        if not shutil.which('gh'):
            raise PanelError('--pr needs the GitHub CLI (gh), signed in')
        result = subprocess.run(
            ['gh', 'pr', 'view', str(args.pr), '--json', 'number,title,body,baseRefName,headRefOid,url'],
            cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            raise PanelError(f'gh pr view {args.pr} failed: {result.stderr.strip()}')
        pr = json.loads(result.stdout)
        git(['fetch', '--quiet', 'origin', pr['baseRefName'], f"refs/pull/{pr['number']}/head"], repo)
        base, head = f"origin/{pr['baseRefName']}", pr['headRefOid']
        target = {'kind': 'pr', 'label': f"PR #{pr['number']}: {pr['title']}", 'url': pr['url'],
                  'description': pr.get('body') or ''}
    else:
        base = args.base or default_base(repo)
        branch = git(['branch', '--show-current'], repo, check=False) or git(['rev-parse', '--short', 'HEAD'], repo)
        # Reviewers read a snapshot, so the person can keep working while the panel runs.
        head = snapshot_commit(repo)
        target = {'kind': 'local', 'label': f'{branch} against {base}', 'url': None, 'description': ''}
    merge_base = git(['merge-base', base, head], repo)
    worktree = run_dir / 'worktree'
    git(['worktree', 'add', '--quiet', '--detach', str(worktree), head], repo)
    log = git(['log', '--no-color', '--format=%h %s%n%n%b', f'{merge_base}..{head}'], repo)
    target.update(base=base, merge_base=merge_base, head=head, commits=log[:20_000],
                  diff_command=f'git diff {merge_base} {head}')
    return target, worktree, git([*DIFF, merge_base, head], repo, raw=True)


def changed_files(repo, target):
    names = git([*DIFF, '--name-only', '--no-renames', '-z', target['merge_base'], target['head']], repo, raw=True)
    return [name for name in names.split('\0') if name]


def context_markdown(target, files, stat, extra_context, note):
    lines = [
        '# The change under review', '',
        f"- Target: {target['label']}",
        f"- Base: `{target['base']}` (merge base `{target['merge_base']}`)",
        f"- Head: `{target['head']}`" + (', a snapshot of the working tree including uncommitted and new files' if target['kind'] == 'local' else ''),
        f"- Patch: `{files['diff']}`. Where you can run Git, `{target['diff_command']}` in the working directory shows the same diff.",
        f"- Each changed file as it was at the merge base: under `{files['base']}/`, at its repository path.",
    ]
    lines += ['', '## Diff stat', '', '```', stat or '(empty)', '```']
    if extra_context:
        lines += ['', '## Spec, acceptance criteria, and decisions supplied by the requester', '', extra_context.strip()]
    if note:
        lines += ['', '## Note from the requester', '', note.strip()]
    # The change's author wrote these; they state intent but are not the requester's decisions.
    if target['description'].strip():
        lines += ['', '## Pull request description, written by the change\'s author', '', '```text',
                  target['description'].strip().replace('```', "'''"), '```']
    if target['commits'].strip():
        lines += ['', '## Commit messages, written by the change\'s author', '', '```text',
                  target['commits'].strip().replace('```', "'''"), '```']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------------------------
# Sessions.

class Session:
    """One headless agent session whose process group can be stopped from another thread."""

    def __init__(self, cancelled):
        self.cancelled = cancelled
        self.process = None
        self.timed_out = False
        self.lock = threading.RLock()  # Reentrant: Ctrl-C can call stop() on the thread that holds it.

    def run(self, command, prompt, cwd, log_path, timeout, on_line):
        with self.lock:
            if self.cancelled.is_set():
                raise RuntimeError('cancelled')
            self.process = subprocess.Popen(
                command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, start_new_session=True)
        timer = threading.Timer(timeout, self._time_out)
        timer.start()
        try:
            self.process.stdin.write(prompt)
            self.process.stdin.close()
            with log_path.open('a') as log:
                for line in self.process.stdout:
                    log.write(line)
                    log.flush()
                    on_line(line)
            code = self.process.wait()
        except BaseException:
            self.stop()
            raise
        finally:
            timer.cancel()
        if self.cancelled.is_set():
            raise RuntimeError('cancelled')
        if self.timed_out:
            raise RuntimeError(f'timed out after {timeout} seconds (--timeout)')
        return code

    def _time_out(self):
        self.timed_out = True
        self.stop()

    def stop(self):
        with self.lock:
            process = self.process
        if process and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


_claude_help = None


def claude_supports(flag):
    """Whether this Claude Code's --help lists `flag`; older versions lack some hardening options."""
    global _claude_help
    if _claude_help is None:
        _claude_help = subprocess.run(['claude', '--help'], capture_output=True, text=True).stdout
    return flag in _claude_help


def claude_command(agent, run_dir, resume=None):
    command = ['claude', '-p', '--output-format', 'stream-json', '--verbose', '--model', agent['model'],
               '--strict-mcp-config', '--add-dir', str(run_dir)]
    # Layered, so each holds where the installed version lacks another: no project settings or hooks; only the
    # file tools exist; anything else is denied rather than asked about; and the deny list as a last layer.
    command += ['--setting-sources', 'user']
    if claude_supports('--restricted'):
        command += ['--restricted']
    if claude_supports('--tools'):
        command += ['--tools', ','.join(CLAUDE_TOOLS)]
    if claude_supports('dontAsk'):
        command += ['--permission-mode', 'dontAsk']
    command += ['--allowedTools', *CLAUDE_TOOLS, '--disallowedTools', *CLAUDE_DENIED]
    if agent.get('effort', 'default') != 'default':
        command += ['--effort', agent['effort']]
    if resume:
        command += ['--resume', resume]
    return command


def codex_command(agent, cwd, last_message):
    # No MCP servers from the person's Codex config, matching Claude's --strict-mcp-config.
    command = ['codex', 'exec', '--json', '--skip-git-repo-check', '-s', 'read-only', '-C', str(cwd),
               '-c', 'mcp_servers={}', '-m', agent['model'], '-o', str(last_message)]
    if agent.get('effort', 'default') != 'default':
        command += ['-c', f"model_reasoning_effort=\"{agent['effort']}\""]
    return command + ['-']


class Panel:
    """What every session in one run shares: where it runs, its limits, and how to stop it."""

    def __init__(self, run_dir, code_dir, state, timeout, retries):
        self.run_dir = run_dir
        self.code_dir = code_dir
        self.state = state
        self.timeout = timeout
        self.retries = retries
        self.cancelled = threading.Event()
        self.sessions = []

    def cancel(self):
        self.cancelled.set()
        for session in list(self.sessions):
            session.stop()

    def run_agent(self, agent, prompt, folder, attempt, report, earlier, resume=None):
        """Run one session to completion; return (final_text, session_id, usage). Raises on failure.

        `earlier` is the usage of the stage's earlier attempts, which reports add this attempt's to.
        `resume` continues an earlier Claude session instead of starting a new one.
        """
        session = Session(self.cancelled)
        self.sessions.append(session)
        usage = {}
        final = {'text': None, 'id': None}
        log_path = folder / 'events.jsonl'
        (folder / f'prompt-{attempt}.md').write_text(prompt)
        if agent['harness'] == 'claude-code':
            command, parse, last_message = claude_command(agent, self.run_dir, resume), claude_event, None
        else:
            last_message = folder / f'last-message-{attempt}.txt'
            command, parse = codex_command(agent, self.code_dir, last_message), codex_event
        (folder / f'command-{attempt}.json').write_text(json.dumps(command))  # How this session ran.

        def on_line(line):
            if '"subtype":"init"' in line.replace(' ', ''):  # Claude's first event names the model it resolved.
                try:
                    report(None, None, json.loads(line).get('model'))
                except (json.JSONDecodeError, AttributeError):
                    pass
            activity, text, ident = parse(line, usage)
            if ident:
                final['id'] = ident
            if text is not None:
                final['text'] = text
            if activity:
                usage['steps'] = usage.get('steps', 0) + 1
                activity = activity.replace(f'{self.code_dir}/', '').replace(f'{self.run_dir}/', '')
            report(activity, add_usage(earlier, usage))

        code = session.run(command, prompt, self.code_dir, log_path, self.timeout, on_line)
        if last_message and last_message.exists():
            final['text'] = last_message.read_text() or final['text']
        if code != 0 and not final['text']:
            tail = log_path.read_text().strip().splitlines()[-3:]
            raise RuntimeError(f"{agent['harness']} exited with status {code}: {' | '.join(tail)[:400]}")
        return final['text'], final['id'], usage

    def run_until_valid(self, agent, prompt, validator, folder, report):
        """Run a session, and when its JSON breaks the contract, ask again with the problems quoted."""
        attempt = 0
        current, resume, totals = prompt, None, {}
        while True:
            attempt += 1
            text, ident, usage = self.run_agent(agent, current, folder, attempt, report, totals, resume)
            totals = add_usage(totals, usage)
            (folder / f'reply-{attempt}.md').write_text(text or '')
            try:
                value = normalize(extract_json(text))
                problems = validator(value)
            except ValueError as error:
                value, problems = None, [str(error)]
            if not problems:
                return value
            if attempt > self.retries:
                raise RuntimeError('invalid output: ' + '; '.join(problems[:5]))
            report(f'retrying: {problems[0]}'[:160], None)
            fix = ('Your reply did not meet the output contract:\n' + '\n'.join(f'- {p}' for p in problems) +
                   '\n\nReply again with only the corrected JSON object in one ```json block.')
            if agent['harness'] == 'claude-code' and ident:
                current, resume = fix, ident  # A Claude session keeps its context, so it only needs the problems.
            else:  # A fresh session: give it the reply to correct rather than asking it to review again.
                current, resume = (prompt + '\n\n---\n\nYou already reviewed this change. Your reply was:\n\n'
                                   + (text or '(empty)') + '\n\n' + fix), None

    def run_stage(self, entry, agent, prompt, validator, folder):
        """Run one reviewer or the synthesis, keeping its entry in the run state current.

        `entry` picks the state entry from the run state. A failure ends this stage only, and is recorded.
        """
        folder.mkdir(parents=True, exist_ok=True)

        def report(activity, usage, model=None):
            def change(data):
                if model:
                    entry(data)['served_model'] = model
                if activity:
                    entry(data)['activity'] = activity
                if usage is not None:
                    entry(data)['usage'] = usage
            self.state.update(change)

        self.state.update(lambda data: entry(data).update(status='running', started_at=now(), prompt=prompt))
        try:
            result = self.run_until_valid(agent, prompt, validator, folder, report)
        except Exception as error:  # Any failure ends this stage only; the rest of the panel goes on.
            message = str(error) if isinstance(error, (RuntimeError, PanelError)) else f'{type(error).__name__}: {error}'
            (folder / 'error.txt').write_text(traceback.format_exc())
            status = 'cancelled' if self.cancelled.is_set() else 'failed'
            self.state.update(lambda data: entry(data).update(status=status, ended_at=now(), error=message, activity=None))
            return None
        (folder / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
        self.state.update(lambda data: entry(data).update(status='done', ended_at=now(), result=result, activity=None))
        return result


# ---------------------------------------------------------------------------------------------
# The panel.

def load_roster(only, claude_only):
    roster = json.loads(ROSTER.read_text())
    reviewers = roster['reviewers']
    if only:
        unknown = [name for name in only if name not in reviewers]
        if unknown:
            raise PanelError(f"unknown reviewer {', '.join(unknown)}; choose from {', '.join(reviewers)}")
        reviewers = {name: reviewers[name] for name in only}
    has_codex = shutil.which('codex') is not None
    for spec in reviewers.values():
        spec['planned'] = dict(spec['agent'])
        if spec['agent']['harness'] == 'codex' and (claude_only or not has_codex):
            spec['agent'] = dict(roster['codex_fallback'])
            spec['note'] = 'ran on Claude: ' + ('--claude-only' if claude_only else 'codex is not installed')
    if not shutil.which('claude'):
        raise PanelError('the panel needs Claude Code (`claude`) on PATH')
    return roster, reviewers


def reviewer_prompt(name, spec, context, files):
    base = (SKILL / 'prompts' / 'reviewer.md').read_text()
    focus = (SKILL / spec['focus']).read_text()
    return (base.replace('{{REVIEWER}}', name).replace('{{CONTEXT_FILE}}', files['context'])
            + '\n\n---\n\n# Your focus\n\n' + focus + '\n\n---\n\n' + context)


def synthesis_prompt(context, reviews, failures):
    base = (SKILL / 'prompts' / 'synthesize.md').read_text()
    ran = ', '.join([*reviews, *failures])
    parts = [base, '\n---\n', context, f'\n# Reviewer reports\n\nThis run asked these reviewers only: {ran}.\n']
    for name, review in reviews.items():
        parts += [f'\n## {name}\n', '```json', json.dumps(review, indent=2, ensure_ascii=False), '```']
    if failures:
        parts += ['\n# Reviewers that did not report\n'] + [f'- {name}: {reason}' for name, reason in failures.items()]
    return '\n'.join(parts) + '\n'


def report_markdown(state):
    synthesis = state['synthesis'].get('result')
    if synthesis is None:
        return unsynthesized_markdown(state)
    lines = [f"# Review panel: {state['target']['label']}", '', f"Verdict: **{synthesis['verdict']}**", '']
    lines += [f'- {line}' for line in synthesis.get('conclusions', [])] + ['', synthesis['summary'], '']
    for finding in synthesis['findings']:
        where = finding.get('file') or ''
        if finding.get('line'):
            where += f":{finding['line']}"
        lines += [f"## {finding['id']} [{finding['severity']}] {finding['title']}",
                  f"{where} (merges {', '.join(finding.get('merges', []))})", '', finding['body'], '']
        if finding.get('fix'):
            lines += ['Fix: ' + finding['fix'], '']
    if synthesis.get('questions'):
        lines += ['## Questions for you', ''] + [f"- {'[blocking] ' if q.get('blocking') else ''}{q['question']}"
                                                 for q in synthesis['questions']] + ['']
    dropped = []
    for item in synthesis.get('dropped', []):
        result = state['reviewers'].get(item['reviewer'], {}).get('result') or {}
        original = next((f for f in result.get('findings', []) if f.get('id') == item['finding']), {})
        dropped.append((original.get('severity') != 'blocking', item, original))
    if dropped:
        lines += ['## Dropped by the synthesis', '']
        for _, item, original in sorted(dropped, key=lambda d: d[0]):
            lines.append(f"- {item['reviewer']}:{item['finding']} [{original.get('severity', '?')}] "
                         f"{original.get('title', '')}: {item['reason']}")
        lines.append('')
    for name, reviewer in state['reviewers'].items():
        if reviewer['status'] != 'done':
            lines.append(f"- {name} did not report: {reviewer.get('error') or reviewer['status']}")
    return '\n'.join(lines) + '\n'


def unsynthesized_markdown(state):
    """The report when synthesis didn't finish: say why, then each reviewer's own findings, unverified."""
    synthesis = state['synthesis']
    lines = [f"# Review panel: {state['target']['label']}", '',
             f"Synthesis {synthesis['status']}: {synthesis.get('error') or 'no reason recorded'}. "
             'The findings below are each reviewer\'s own, not checked or merged.', '']
    for name, reviewer in state['reviewers'].items():
        result = reviewer.get('result')
        if not result:
            lines.append(f"- {name} did not report: {reviewer.get('error') or reviewer['status']}")
            continue
        lines += [f"## {name}: {result['verdict']}", '', result['summary'], '']
        for finding in result['findings']:
            where = (finding.get('file') or '') + (f":{finding['line']}" if finding.get('line') else '')
            lines.append(f"- {finding['id']} [{finding['severity']}] {finding['title']} {where}".rstrip())
        lines.append('')
    return '\n'.join(lines) + '\n'


def standalone_html(state_json):
    page = PAGE.read_text()
    # Escaped this way, nothing in the state (a PR description, a finding) can end the script element early.
    inline = state_json.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return page.replace('<script id="inline-state" type="application/json"></script>',
                        f'<script id="inline-state" type="application/json">{inline}</script>')


def serve(state, run_dir, port, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split('?')[0]
            if path == f'/{token}/':
                body, kind = PAGE.read_bytes(), 'text/html; charset=utf-8'
            elif path == f'/{token}/state.json':
                body, kind = state.serve_snapshot().encode(), 'application/json'
            elif path.startswith(f'/{token}/log/'):
                name = path.rsplit('/', 1)[-1]
                if not re.fullmatch(r'[a-z0-9-]+', name):
                    self.send_error(404)
                    return
                # After a Codex-to-Claude fallback, the session that produced the result logged under fallback/.
                log = run_dir / 'reviewers' / name / 'fallback' / 'events.jsonl'
                if not log.exists():
                    log = run_dir / 'reviewers' / name / 'events.jsonl'
                if not log.exists():
                    self.send_error(404)
                    return
                body, kind = log.read_bytes()[-200_000:], 'text/plain; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def open_page(url):
    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
    if shutil.which(opener):
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def write_base_files(repo, target, run_dir):
    """Copy each changed file's version at the merge base into the run directory, for reviewers without Git."""
    base_dir = run_dir / 'base'
    for name in changed_files(repo, target):
        result = subprocess.run(['git', 'show', f"{target['merge_base']}:{name}"], cwd=repo, capture_output=True)
        if result.returncode == 0 and len(result.stdout) <= 1_000_000:
            path = base_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(result.stdout)
    return base_dir


def initial_state(repo, run_dir, target, stat, roster, reviewers):
    def entry(agent, **extra):
        return {'agent': agent, 'status': 'queued', 'started_at': None, 'ended_at': None, 'activity': None,
                'usage': {}, 'result': None, 'error': None, **extra}
    return {
        'status': 'running', 'started_at': now(), 'updated_at': now(), 'ended_at': None,
        'repo': str(repo), 'run_dir': str(run_dir), 'target': target, 'diff_stat': stat,
        'reviewers': {name: entry(spec['agent'], focus=spec['summary'], planned=spec['planned'], note=spec.get('note'))
                      for name, spec in reviewers.items()},
        'synthesis': entry(roster['synthesize']['agent'], status='waiting'),
    }


def wait_for_page(state, server, limit=20):
    """Give an open live page up to `limit` seconds to fetch the final state, then stop serving."""
    final = state.version
    deadline = time.monotonic() + limit
    while state.served_version is not None and state.served_version < final and time.monotonic() < deadline:
        time.sleep(0.5)
    server.shutdown()


def run(args):
    repo = Path(git(['rev-parse', '--show-toplevel'], Path.cwd()))
    common = Path(git(['rev-parse', '--git-common-dir'], repo))
    common = common if common.is_absolute() else repo / common
    roster, reviewers = load_roster(args.only, args.claude_only)
    try:
        extra = Path(args.context).read_text() if args.context else ''
    except OSError as error:
        raise PanelError(f'cannot read --context: {error}') from error
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_dir = common / 'review-panel' / f"{stamp}-{f'pr{args.pr}' if args.pr else 'local'}"
    (run_dir / 'reviewers').mkdir(parents=True)
    try:
        target, code_dir, diff = prepare_target(args, repo, run_dir)
        if not diff.strip():
            raise PanelError(f"there is nothing to review: no changes between {target['base']} and the working tree")
        return review(args, repo, run_dir, target, code_dir, diff, extra, roster, reviewers)
    finally:
        if (run_dir / 'worktree').exists():
            git(['worktree', 'remove', '--force', str(run_dir / 'worktree')], repo, check=False)
        if not (run_dir / 'state.json').exists():  # Nothing ran; leave no empty run behind.
            shutil.rmtree(run_dir, ignore_errors=True)


def review(args, repo, run_dir, target, code_dir, diff, extra, roster, reviewers):
    (run_dir / 'diff.patch').write_text(diff)
    files = {'diff': str(run_dir / 'diff.patch'), 'context': str(run_dir / 'context.md'),
             'base': str(write_base_files(repo, target, run_dir))}
    stat = git([*DIFF, '--stat', target['merge_base'], target['head']], repo)
    context = context_markdown(target, files, stat, extra, args.note)
    Path(files['context']).write_text(context)

    state = State(run_dir / 'state.json', initial_state(repo, run_dir, target, stat, roster, reviewers))
    server = None
    if not args.no_serve:
        token = secrets.token_urlsafe(12)
        try:
            server = serve(state, run_dir, args.port, token)
        except OSError as error:
            state.path.unlink()  # Nothing ran, so the run directory is removed.
            raise PanelError(f'cannot serve the live view on port {args.port}: {error}') from error
        url = f'http://127.0.0.1:{server.server_address[1]}/{token}/'
        print(f'Live view: {url}', flush=True)
        if not args.no_open:
            open_page(url)
    print(f'Run directory: {run_dir}', flush=True)
    try:
        return run_panel(args, run_dir, code_dir, state, server, context, files, roster, reviewers)
    except BaseException as error:
        message = f'{type(error).__name__}: {error}'
        state.update(lambda data: data.update(status='failed', ended_at=now(), error=message))
        if server:
            server.shutdown()
        raise


def run_panel(args, run_dir, code_dir, state, server, context, files, roster, reviewers):
    panel = Panel(run_dir, code_dir, state, args.timeout, args.retries)
    signal.signal(signal.SIGINT, lambda signum, frame: panel.cancel())
    signal.signal(signal.SIGTERM, lambda signum, frame: panel.cancel())

    def reviewer(name, spec):
        entry = lambda data: data['reviewers'][name]  # noqa: E731
        prompt = reviewer_prompt(name, spec, context, files)
        folder = run_dir / 'reviewers' / name
        result = panel.run_stage(entry, spec['agent'], prompt, validate_review, folder)
        if result is None and spec['agent']['harness'] == 'codex' and not panel.cancelled.is_set():
            # Codex is installed but its session failed (signed out, out of quota): keep the panel's coverage.
            error = state.data['reviewers'][name]['error']
            fallback = dict(roster['codex_fallback'])
            state.update(lambda data: entry(data).update(agent=fallback, error=None, note=f'ran on Claude: codex failed ({error})'[:300]))
            result = panel.run_stage(entry, fallback, prompt, validate_review, folder / 'fallback')
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = dict(zip(reviewers, pool.map(lambda item: reviewer(*item), reviewers.items())))
    reviews = {name: result for name, result in results.items() if result is not None}
    failures = {name: state.data['reviewers'][name]['error'] for name, result in results.items() if result is None}

    if reviews and not panel.cancelled.is_set():
        panel.run_stage(lambda data: data['synthesis'], roster['synthesize']['agent'],
                        synthesis_prompt(context, reviews, failures),
                        lambda value: validate_synthesis(normalize_synthesis(value), reviews), run_dir / 'synthesis')
    else:
        reason = 'cancelled' if panel.cancelled.is_set() else 'no reviewer reported'
        state.update(lambda data: data['synthesis'].update(status='skipped', error=reason))

    if panel.cancelled.is_set():
        final_status = 'cancelled'
    else:
        final_status = 'done' if state.data['synthesis']['status'] == 'done' else 'failed'
    state.update(lambda data: data.update(status=final_status, ended_at=now()))
    final_json = state.snapshot()
    (run_dir / 'report.html').write_text(standalone_html(final_json))
    (run_dir / 'report.md').write_text(report_markdown(json.loads(final_json)))
    if server:
        wait_for_page(state, server, limit=0 if panel.cancelled.is_set() else 20)
    print(f"Report: {run_dir / 'report.md'}")
    print(f"Standalone page: {run_dir / 'report.html'}")
    print(f'Status: {final_status}')
    return 0 if final_status == 'done' else 1



def reopen(args):
    run_dir = Path(args.run_dir).resolve()
    page = run_dir / 'report.html'
    if not page.exists():
        raise PanelError(f'{page} does not exist; the run may still be going or was interrupted')
    open_page(page.as_uri())
    print(page)
    return 0


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be 1 or more')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('run', help='review the current branch (or a pull request) with the panel')
    start.add_argument('--pr', type=int, help='review this GitHub pull request in a temporary worktree')
    start.add_argument('--base', help='base for a local review (default: origin/HEAD, else the first of origin/main, origin/master, main, master)')
    start.add_argument('--only', type=lambda v: [s.strip() for s in v.split(',') if s.strip()], help='comma-separated reviewers to run')
    start.add_argument('--context', help='a file with the spec, acceptance criteria, or decisions to judge against')
    start.add_argument('--note', help='a short note every reviewer reads, such as what to focus on')
    start.add_argument('--claude-only', action='store_true', help='run every reviewer on Claude Code')
    start.add_argument('--concurrency', type=positive, default=8, help='reviewers running at once (default 8)')
    start.add_argument('--timeout', type=positive, default=20 * 60, metavar='SECONDS', help='limit per session (default 1200)')
    start.add_argument('--retries', type=int, choices=range(0, 6), default=2, metavar='N',
                       help='retries for a reply that breaks the output contract (0-5, default 2)')
    start.add_argument('--port', type=int, default=0, help='port for the live view (default: any free port)')
    start.add_argument('--no-open', action='store_true', help='print the live view URL without opening a browser')
    start.add_argument('--no-serve', action='store_true', help='skip the live view; write the report only')
    again = commands.add_parser('open', help="open a finished run's standalone report page")
    again.add_argument('run_dir')
    args = parser.parse_args(argv)
    try:
        return run(args) if args.command == 'run' else reopen(args)
    except PanelError as error:
        print(f'review-panel: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
