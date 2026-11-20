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
import shlex
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
# A repository customizes its panel here: panel.yaml picks and orders the reviewers, and reviewers/<name>.md
# replaces, extends, or adds a reviewer's focus prompt. Read from the checkout the command runs in, never from
# a pull request under review, so a change can't rewrite the panel that judges it.
CONFIG_DIR = Path('.fabrica') / 'review-panel'
HARNESSES = ('claude-code', 'codex')
NEW_REVIEWER_AGENT = {'harness': 'claude-code', 'model': 'opus', 'effort': 'high'}
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


CONCLUSION_KINDS = ('fix', 'decide', 'check', 'note')


def _check_conclusion(item, where, ids, problems):
    if not isinstance(item, dict):
        _require(False, f'{where} must be an object with kind, headline, detail, and findings', problems)
        return
    _require(set(item) <= {'kind', 'headline', 'detail', 'findings'}, f"{where} has unknown keys; use kind, headline, detail, and findings", problems)
    _require(item.get('kind') in CONCLUSION_KINDS, f"{where}.kind must be one of {', '.join(CONCLUSION_KINDS)}", problems)
    headline = item.get('headline')
    _require(isinstance(headline, str) and headline.strip() and len(headline) <= 60, f'{where}.headline must be a few words under 60 characters', problems)
    detail = item.get('detail')
    _require(detail is None or (isinstance(detail, str) and len(detail) <= 200), f'{where}.detail must be one sentence under 200 characters, or null', problems)
    refs = item.get('findings', [])
    _require(isinstance(refs, list) and all(isinstance(r, str) for r in refs), f'{where}.findings must list finding IDs such as "S1"', problems)
    for ref in refs if isinstance(refs, list) else []:
        _require(ref in ids, f'{where}.findings names {ref!r}, which is not one of your findings', problems)


def conclusion_line(item):
    """One conclusion as a Markdown list item; earlier runs wrote plain strings."""
    if isinstance(item, str):
        return f'- {item}'
    refs = f" ({', '.join(item.get('findings') or [])})" if item.get('findings') else ''
    detail = f" {item['detail']}" if item.get('detail') else ''
    return f"- **{item['kind'].capitalize()}:** {item['headline']}.{detail}{refs}"


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
    _require(isinstance(conclusions, list) and 1 <= len(conclusions) <= 5, 'conclusions must list one to five conclusions', problems)
    ids = {f.get('id') for f in findings if isinstance(f, dict)} if isinstance(findings, list) else set()
    for index, item in enumerate(conclusions if isinstance(conclusions, list) else []):
        _check_conclusion(item, f'conclusions[{index}]', ids, problems)
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


def github_repo(repo):
    """owner/name when origin is a GitHub repository, else None."""
    url = git(['remote', 'get-url', 'origin'], repo, check=False) or ''
    match = re.search(r'github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$', url)
    return match.group(1) if match else None


def open_pull_request(repo):
    """The open pull request for the current branch, if gh can find one quickly; None otherwise."""
    if not shutil.which('gh'):
        return None
    try:
        result = subprocess.run(['gh', 'pr', 'view', '--json', 'number,title,url,state'], cwd=repo,
                                capture_output=True, text=True, timeout=10)
        pr = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    return pr if pr and pr.get('state') == 'OPEN' else None


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
                  'description': pr.get('body') or '', 'number': pr['number'], 'title': pr['title']}
    else:
        base = args.base or default_base(repo)
        branch = git(['branch', '--show-current'], repo, check=False) or git(['rev-parse', '--short', 'HEAD'], repo)
        # Reviewers read a snapshot, so the person can keep working while the panel runs.
        head = snapshot_commit(repo)
        target = {'kind': 'local', 'label': f'{branch} against {base}', 'url': None, 'description': '', 'branch': branch}
        # A local review of a branch that has a pull request links to it, but still reviews the local snapshot.
        pr = open_pull_request(repo)
        if pr:
            target.update(url=pr['url'], number=pr['number'], title=pr['title'])
    merge_base = git(['merge-base', base, head], repo)
    worktree = run_dir / 'worktree'
    git(['worktree', 'add', '--quiet', '--detach', str(worktree), head], repo)
    log = git(['log', '--no-color', '--format=%h %s%n%n%b', f'{merge_base}..{head}'], repo)
    github = github_repo(repo)
    target.update(repo_name=github or repo.name, github=github, base=base, merge_base=merge_base, head=head, commits=log[:20_000],
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

def _scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        return text[1:-1]
    return {'true': True, 'false': False}.get(text, text)


def _strip_comment(line):
    quote = None
    for index, char in enumerate(line):
        if quote:
            quote = None if char == quote else quote
        elif char in '"\'':
            quote = char
        elif char == '#' and (index == 0 or line[index - 1] in ' \t'):
            return line[:index]
    return line


def parse_yaml(text, where):
    """Parse the small YAML subset panel files use: `key: value`, and a key holding a list or a flat map.

    The skill runs on the Python standard library alone, so it reads this subset rather than full YAML,
    and names the line it can't read instead of guessing.
    """
    data, current = {}, None
    for number, raw in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indented = line[0] in ' \t'
        stripped = line.strip()
        if not indented:
            key, sep, value = stripped.partition(':')
            if not sep or not re.fullmatch(r'[A-Za-z0-9_-]+', key.strip()):
                raise PanelError(f'{where}:{number}: expected "key: value"')
            key = key.strip()
            if value.strip():
                data[key], current = _scalar(value), None
            else:
                data[key], current = None, key
            continue
        if current is None:
            raise PanelError(f'{where}:{number}: indented line with no key above it')
        if stripped.startswith('- '):
            if data[current] is None:
                data[current] = []
            if not isinstance(data[current], list):
                raise PanelError(f'{where}:{number}: {current} mixes a list and a map')
            data[current].append(_scalar(stripped[2:]))
        else:
            key, sep, value = stripped.partition(':')
            if not sep or not value.strip():
                raise PanelError(f'{where}:{number}: expected "- item" or "key: value" under {current}')
            if data[current] is None:
                data[current] = {}
            if not isinstance(data[current], dict):
                raise PanelError(f'{where}:{number}: {current} mixes a list and a map')
            data[current][key.strip()] = _scalar(value)
    return data


def read_prompt_file(path):
    """Split a reviewer file into its front matter (settings) and its Markdown body (the focus prompt)."""
    text = path.read_text()
    match = re.match(r'---\n(.*?)\n---\n?(.*)', text, re.S)
    if not match:
        return {}, text.strip()
    return parse_yaml(match.group(1), str(path)), match.group(2).strip()


def _agent_with(agent, settings, where):
    agent = dict(agent)
    for key in ('harness', 'model', 'effort'):
        if settings.get(key) is not None:
            agent[key] = str(settings[key])
    if agent['harness'] not in HARNESSES:
        raise PanelError(f"{where}: harness must be one of {', '.join(HARNESSES)}")
    return agent


def apply_repo_config(roster, folder, label):
    """Merge a repository's .fabrica/review-panel folder over the built-in roster, in place."""
    reviewers = roster['reviewers']
    config_path = folder / 'panel.yaml'
    config = parse_yaml(config_path.read_text(), str(config_path)) if config_path.exists() else {}
    unknown = sorted(set(config) - {'reviewers', 'synthesis', 'codex_fallback'})
    if unknown:
        raise PanelError(f"{config_path}: unknown setting {', '.join(unknown)}; use reviewers, synthesis, or codex_fallback")
    for key, target in (('synthesis', roster['synthesize']), ('codex_fallback', None)):
        settings = config.get(key)
        if settings is None:
            continue
        if not isinstance(settings, dict):
            raise PanelError(f'{config_path}: {key} must be a map of harness, model, and effort')
        if target is None:
            roster['codex_fallback'] = _agent_with(roster['codex_fallback'], settings, f'{config_path} {key}')
        else:
            target['agent'] = _agent_with(target['agent'], settings, f'{config_path} {key}')
    added = []
    for path in sorted((folder / 'reviewers').glob('*.md')):
        name = path.stem
        if not re.fullmatch(r'[a-z0-9-]+', name):
            raise PanelError(f'{path}: reviewer file names use lowercase letters, digits, and hyphens')
        settings, body = read_prompt_file(path)
        extra = sorted(set(settings) - {'summary', 'harness', 'model', 'effort', 'mode'})
        if extra:
            raise PanelError(f"{path}: unknown setting {', '.join(extra)}")
        mode = settings.get('mode', 'replace')
        if mode not in ('replace', 'append'):
            raise PanelError(f'{path}: mode must be replace or append')
        relative = f'{label}/reviewers/{path.name}'
        if name in reviewers:
            reviewers[name].update(file=relative, file_body=body, mode=mode)
            spec = reviewers[name]
            if not body:  # Front matter only: change the summary or agent and keep the built-in prompt.
                spec['source'] = f'built-in prompt, settings from {relative}'
            elif mode == 'append':
                spec['focus_text'] += '\n\n## Added by this repository\n\n' + body
                spec['source'] = f'built-in, extended by {relative}'
            else:
                spec['focus_text'] = body
                spec['source'] = f'replaced by {relative}'
        else:
            if mode == 'append':
                raise PanelError(f'{path}: mode append needs a built-in reviewer named {name}; this one is new')
            if not settings.get('summary'):
                raise PanelError(f'{path}: a new reviewer needs a summary in its front matter')
            spec = reviewers[name] = {'agent': dict(NEW_REVIEWER_AGENT), 'focus_text': body, 'source': f'added by {relative}',
                                      'file': relative, 'file_body': body, 'mode': mode}
            added.append(name)
        if not body and name in added:
            raise PanelError(f'{path}: a new reviewer needs a prompt below the front matter')
        if settings.get('summary'):
            spec['summary'] = str(settings['summary'])
        spec['agent'] = _agent_with(spec['agent'], settings, str(path))
    chosen = config.get('reviewers')
    if chosen is not None:
        if not isinstance(chosen, list) or not chosen or not all(isinstance(n, str) for n in chosen):
            raise PanelError(f'{config_path}: reviewers must be a list of reviewer names')
        missing = [n for n in chosen if n not in reviewers]
        if missing:
            raise PanelError(f"{config_path}: no reviewer named {', '.join(missing)}; add reviewers/{missing[0]}.md "
                             f"or choose from {', '.join(reviewers)}")
        roster['reviewers'] = {n: reviewers[n] for n in chosen}
    roster.setdefault('config', {})['panel'] = config


def roster_summary(roster):
    """Every reviewer the panel would run, and where each setting comes from, for the settings window."""
    chosen = roster['config'].get('panel', {}).get('reviewers')
    every = {**roster.get('built_in', {}), **roster['reviewers']}
    if chosen:
        every = {**{n: every[n] for n in chosen if n in every}, **every}
    return {
        'reviewers': {name: {'summary': spec.get('summary', ''), 'agent': dict(spec['agent']), 'source': spec['source'],
                             'builtin': 'builtin_text' in spec, 'builtin_text': spec.get('builtin_text', ''),
                             'builtin_agent': spec.get('builtin_agent'), 'builtin_summary': spec.get('builtin_summary'),
                             'file': spec.get('file'), 'file_body': spec.get('file_body', ''), 'mode': spec.get('mode', 'replace'),
                             'included': chosen is None or name in chosen}
                      for name, spec in every.items()},
        'synthesis': dict(roster['synthesize']['agent']),
        'builtin_synthesis': roster.get('builtin_synthesis'),
        'codex_fallback': dict(roster['codex_fallback']),
        'panel_codex_fallback': roster['config'].get('panel', {}).get('codex_fallback'),
    }


def load_roster(only, claude_only, repo=None, panel=None, settings_only=False):
    roster = json.loads(ROSTER.read_text())
    for spec in roster['reviewers'].values():
        spec['focus_text'] = spec['builtin_text'] = (SKILL / spec.pop('focus')).read_text().strip()
        spec['builtin_agent'], spec['builtin_summary'] = dict(spec['agent']), spec['summary']
        spec['source'] = 'built-in'
    folder = Path(panel) if panel else (repo / CONFIG_DIR if repo else None)
    if panel and not folder.is_dir():
        raise PanelError(f'--panel {panel} is not a folder')
    roster['built_in'] = roster['reviewers']
    roster['builtin_synthesis'] = dict(roster['synthesize']['agent'])
    script = Path(__file__).resolve()
    roster['config'] = {'dir': str(CONFIG_DIR) if not panel else str(folder), 'found': bool(folder and folder.is_dir()),
                        'command': shlex.join(['python3', str(script), 'settings', *(['--panel', str(panel)] if panel else [])])}
    if roster['config']['found']:
        apply_repo_config(roster, folder, roster['config']['dir'])
    roster['all'] = roster_summary(roster)
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
    if not shutil.which('claude') and not settings_only:
        raise PanelError('the panel needs Claude Code (`claude`) on PATH')
    return roster, reviewers


def reviewer_prompt(name, spec, context, files):
    base = (SKILL / 'prompts' / 'reviewer.md').read_text()
    focus = spec['focus_text']
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
    lines += [conclusion_line(item) for item in synthesis.get('conclusions', [])] + ['', synthesis['summary'], '']
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


SETTINGS_FILE = re.compile(r'(panel\.yaml|reviewers/[a-z0-9-]+\.md)')


def save_settings(repo, panel, files, remove):
    """Write the settings window's files into the repository's config folder, after checking the result loads.

    `files` maps a path inside the folder (panel.yaml or reviewers/<name>.md) to its text; `remove` lists paths to
    delete. Nothing is written unless the folder, with these changes, is one the next run would accept."""
    folder = Path(panel) if panel else repo / CONFIG_DIR
    paths = [*files, *remove]
    bad = [p for p in paths if not isinstance(p, str) or not SETTINGS_FILE.fullmatch(p)]
    if bad:
        raise PanelError(f'can only write panel.yaml and reviewers/<name>.md, not {bad[0]}')
    if not all(isinstance(text, str) for text in files.values()):
        raise PanelError('each file needs its text')
    with tempfile.TemporaryDirectory() as scratch:
        trial = Path(scratch) / 'review-panel'
        if folder.is_dir():
            shutil.copytree(folder, trial)
        (trial / 'reviewers').mkdir(parents=True, exist_ok=True)
        for path in remove:
            (trial / path).unlink(missing_ok=True)
        for path, text in files.items():
            (trial / path).write_text(text)
        load_roster(None, False, panel=trial, settings_only=True)  # Raises PanelError, which the page shows.
    (folder / 'reviewers').mkdir(parents=True, exist_ok=True)
    for path in remove:
        (folder / path).unlink(missing_ok=True)
    for path, text in files.items():
        (folder / path).write_text(text)
    roster, _ = load_roster(None, False, repo, panel, settings_only=True)
    return roster


def refresh_settings(data, roster):
    data.update(roster=roster['all'], models=roster.get('models', []),
                config={k: v for k, v in roster['config'].items() if k != 'panel'})


def serve(state, run_dir, port, token, repo=None, panel=None):
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

        def do_POST(self):
            # Only the page this server handed out can save: the path holds the secret token, and a JSON body
            # from another site needs a CORS preflight, which this server never answers.
            if self.path != f'/{token}/settings' or repo is None:
                self.send_error(404)
                return
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                self.send_error(415)
                return
            origin = self.headers.get('Origin')
            if origin and origin != f'http://{self.headers.get("Host")}':
                self.send_error(403)
                return
            try:
                request = json.loads(self.rfile.read(min(int(self.headers.get('Content-Length', 0)), 2_000_000)))
                roster = save_settings(repo, panel, dict(request.get('files') or {}), list(request.get('remove') or []))
                state.update(lambda data: refresh_settings(data, roster))
                status, reply = 200, {'ok': True, 'roster': state.data['roster'], 'config': state.data['config']}
            except (ValueError, AttributeError, TypeError) as error:
                status, reply = 400, {'ok': False, 'error': f'bad request: {error}'}
            except (PanelError, OSError) as error:
                status, reply = 400, {'ok': False, 'error': str(error)}
            body = json.dumps(reply).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
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


SNIPPET_CONTEXT = 2       # lines shown around each cited range
SNIPPET_MAX_LINES = 60    # longest single range shown
SNIPPET_MAX_RANGES = 4    # ranges shown per finding


def line_ranges(line):
    """Parse a finding's `line` ("42", "40-55", "472-484, 528") into (start, end) pairs; [] if it has none."""
    ranges = []
    for start, end in re.findall(r'(\d+)(?:\s*[-\u2013]\s*(\d+))?', str(line or '')):
        start, end = int(start), int(end or start)
        if start > 0 and end >= start:
            ranges.append((start, min(end, start + SNIPPET_MAX_LINES - 1)))
    return ranges[:SNIPPET_MAX_RANGES]


def code_snippets(code_dir, findings):
    """Excerpts of the code each finding cites, read from the reviewed snapshot, keyed "file:line".

    The page shows them in the finding window, and the standalone report keeps them after the worktree is gone.
    """
    root = Path(code_dir).resolve()
    snippets = {}
    for finding in findings:
        file, line = finding.get('file'), finding.get('line')
        key = f'{file}:{line}'
        if not file or key in snippets:
            continue
        path = (root / file).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            continue
        try:
            lines = path.read_text(errors='replace').splitlines()
        except OSError:
            continue
        excerpts = []
        for start, end in line_ranges(line):
            if start > len(lines):
                continue
            first, last = max(1, start - SNIPPET_CONTEXT), min(len(lines), end + SNIPPET_CONTEXT)
            excerpts.append({'start': first, 'focus': [start, min(end, len(lines))],
                             'lines': [text[:400] for text in lines[first - 1:last]]})
        snippets[key] = excerpts
    return snippets


def initial_state(repo, run_dir, target, stat, roster, reviewers):
    def entry(agent, **extra):
        return {'agent': agent, 'status': 'queued', 'started_at': None, 'ended_at': None, 'activity': None,
                'usage': {}, 'result': None, 'error': None, **extra}
    return {
        'status': 'running', 'started_at': now(), 'updated_at': now(), 'ended_at': None,
        'repo': str(repo), 'run_dir': str(run_dir), 'target': target, 'diff_stat': stat,
        'reviewers': {name: entry(spec['agent'], focus=spec['summary'], planned=spec['planned'], note=spec.get('note'),
                                  focus_text=spec['focus_text'], source=spec['source'])
                      for name, spec in reviewers.items()},
        'config': {k: v for k, v in roster.get('config', {}).items() if k != 'panel'}, 'snippets': {},
        'models': roster.get('models', []), 'roster': roster.get('all'),
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
    roster, reviewers = load_roster(args.only, args.claude_only, repo, args.panel)
    try:
        extra = Path(args.context).read_text() if args.context else ''
    except OSError as error:
        raise PanelError(f'cannot read --context: {error}') from error
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_dir = common / 'review-panel' / f"{stamp}-{f'pr{args.pr}' if args.pr else 'local'}"
    (run_dir / 'reviewers').mkdir(parents=True)
    try:
        target, code_dir, diff = prepare_target(args, repo, run_dir)
        # The page's Rerun button copies this, so a person can review the change again after fixing it.
        target['rerun'] = shlex.join(['python3', str(Path(__file__).resolve()), *sys.argv[1:]])
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
            server = serve(state, run_dir, args.port, token, repo, args.panel)
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
        if result:
            add_snippets(result['findings'])
        return result

    def add_snippets(findings):
        found = code_snippets(code_dir, findings)
        state.update(lambda data: data.setdefault('snippets', {}).update(found))

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = dict(zip(reviewers, pool.map(lambda item: reviewer(*item), reviewers.items())))
    reviews = {name: result for name, result in results.items() if result is not None}
    failures = {name: state.data['reviewers'][name]['error'] for name, result in results.items() if result is None}

    if reviews and not panel.cancelled.is_set():
        panel.run_stage(lambda data: data['synthesis'], roster['synthesize']['agent'],
                        synthesis_prompt(context, reviews, failures),
                        lambda value: validate_synthesis(normalize_synthesis(value), reviews), run_dir / 'synthesis')
        if state.data['synthesis'].get('result'):
            add_snippets(state.data['synthesis']['result']['findings'])
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


def settings_command(args):
    """Serve the latest run's page with its settings window open, so saved settings land in the repository."""
    repo = Path(git(['rev-parse', '--show-toplevel'], Path.cwd()))
    common = Path(git(['rev-parse', '--git-common-dir'], repo))
    common = common if common.is_absolute() else repo / common
    runs = sorted((common / 'review-panel').glob('*/state.json'))
    if not runs:
        raise PanelError('no review has run in this repository yet; run `review_panel.py run` once first')
    data = json.loads(runs[-1].read_text())
    roster, _ = load_roster(None, False, repo, args.panel, settings_only=True)
    refresh_settings(data, roster)
    with tempfile.TemporaryDirectory() as scratch:
        state = State(Path(scratch) / 'state.json', data)
        token = secrets.token_urlsafe(12)
        try:
            server = serve(state, runs[-1].parent, args.port, token, repo, args.panel)
        except OSError as error:
            raise PanelError(f'cannot serve the settings page on port {args.port}: {error}') from error
        url = f'http://127.0.0.1:{server.server_address[1]}/{token}/#settings'
        print(f'Settings: {url}', flush=True)
        print('Saved settings go to ' + str(Path(args.panel) if args.panel else repo / CONFIG_DIR) + '. Press Ctrl-C to stop.', flush=True)
        if not args.no_open:
            open_page(url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            server.shutdown()
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
    start.add_argument('--panel', metavar='DIR', help=f'read panel settings from DIR instead of {CONFIG_DIR} in the repository')
    start.add_argument('--concurrency', type=positive, default=8, help='reviewers running at once (default 8)')
    start.add_argument('--timeout', type=positive, default=20 * 60, metavar='SECONDS', help='limit per session (default 1200)')
    start.add_argument('--retries', type=int, choices=range(0, 6), default=2, metavar='N',
                       help='retries for a reply that breaks the output contract (0-5, default 2)')
    start.add_argument('--port', type=int, default=0, help='port for the live view (default: any free port)')
    start.add_argument('--no-open', action='store_true', help='print the live view URL without opening a browser')
    start.add_argument('--no-serve', action='store_true', help='skip the live view; write the report only')
    again = commands.add_parser('open', help="open a finished run's standalone report page")
    again.add_argument('run_dir')
    config = commands.add_parser('settings', help="edit this repository's panel settings in the page, saving them to its config folder")
    config.add_argument('--panel', metavar='DIR', help=f'save to DIR instead of {CONFIG_DIR} in the repository')
    config.add_argument('--port', type=int, default=0, help='port for the page (default: any free port)')
    config.add_argument('--no-open', action='store_true', help='print the URL without opening a browser')
    args = parser.parse_args(argv)
    try:
        return {'run': run, 'open': reopen, 'settings': settings_command}[args.command](args)
    except PanelError as error:
        print(f'review-panel: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
