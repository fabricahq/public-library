#!/usr/bin/env python3
"""Local canvas and durable reply inbox for the agent running grill-me-ui."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import selectors
import shlex
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ASSET = Path(__file__).resolve().parent.parent / 'assets' / 'canvas.html'
LIMIT = 2_000_000
LEASE = 75


def read(path):
    return json.loads(Path(path).read_text())


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.grill-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def validate_shape(value, schema, path='design tree'):
    """Check the bundled schema's closed subset without a runtime dependency.

    The schema is also usable by standard JSON Schema editors and validators.
    Graph consistency rules live in validate(), below.
    """
    unsupported = set(schema) - {'$schema', '$id', 'title', 'description', 'type', 'const', 'enum',
                                'required', 'properties', 'additionalProperties', 'items',
                                'minItems', 'maxItems', 'minLength', 'maxLength', 'pattern', 'minimum'}
    if unsupported:
        raise ValueError(f'{path}: schema uses unsupported checks: {sorted(unsupported)}.')
    types = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: type(v) is int,
             'boolean': lambda v: type(v) is bool, 'null': lambda v: v is None}
    expected = schema.get('type', [])
    if isinstance(expected, str):
        expected = [expected]
    if expected and not any(types[kind](value) for kind in expected):
        raise ValueError(f'{path}: expected {" or ".join(expected)}.')
    if 'const' in schema and value != schema['const']:
        raise ValueError(f'{path}: unsupported version; expected {schema["const"]}.')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: expected one of {schema["enum"]}.')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                raise ValueError(f'{path}.{key}: required.')
        properties = schema.get('properties', {})
        for key, item in value.items():
            if key not in properties:
                if schema.get('additionalProperties') is False:
                    raise ValueError(f'{path}.{key}: unknown field.')
            else:
                validate_shape(item, properties[key], f'{path}.{key}')
    elif isinstance(value, list):
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', float('inf')):
            raise ValueError(f'{path}: provide {schema.get("minItems", 0)}-{schema["maxItems"]} items.')
        for index, item in enumerate(value):
            validate_shape(item, schema['items'], f'{path}[{index}]')
    elif isinstance(value, str):
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', float('inf')):
            raise ValueError(f'{path}: text length is outside the allowed range.')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(f'{path}: text does not match the required format.')
    elif type(value) is int and value < schema.get('minimum', value):
        raise ValueError(f'{path}: must be at least {schema["minimum"]}.')


def validate(data):
    validate_shape(data, read(ASSET.parent.parent / 'schemas' / 'design-tree.schema.json'))
    nodes = data['nodes']
    for node in nodes:
        if node.get('help') and node['help']['basedOnRevision'] > data['revision']:
            raise ValueError('Question help cannot be based on a future revision.')
    by_id = {n['id']: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError('Node IDs must be unique.')
    if not any(n['parentId'] is None for n in nodes):
        raise ValueError('The design must have at least one top-level element.')
    visiting, done = set(), set()

    def visit(ident):
        if ident in visiting:
            raise ValueError('Parent/prerequisite cycles are not allowed.')
        if ident in done:
            return
        if ident not in by_id:
            raise ValueError(f'Missing prerequisite: {ident}')
        visiting.add(ident)
        n = by_id[ident]
        for dep in ([n['parentId']] if n['parentId'] else []) + n.get('dependsOn', []):
            visit(dep)
        visiting.remove(ident)
        done.add(ident)

    for ident in by_id:
        visit(ident)
    constraints = data.get('constraints', [])
    constraint_ids = {item['id'] for item in constraints}
    if len(constraint_ids) != len(constraints):
        raise ValueError('Constraint IDs must be unique.')
    for node in nodes:
        for key in ('assumptions', 'alternatives'):
            items = node.get(key, [])
            if len({item['id'] for item in items}) != len(items):
                raise ValueError(f'{node["id"]}: {key} IDs must be unique.')
        if any(ident not in constraint_ids for ident in node.get('constraintIds', [])):
            raise ValueError(f'{node["id"]}: unknown constraint reference.')
    return dict(data, schemaVersion=1)


def artifact_file(path):
    """Read only the exact registered text file, with bounded memory usage."""
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.suffix.lower() not in ('.md', '.txt'):
        raise ValueError('The registered Markdown/text file has moved or changed target.')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Artifact must be a regular file.')
        content = stream.read(262145)
        if len(content) > 262144:
            raise ValueError('Artifact exceeds the 256 KB viewer limit.')
    return {'content': content.decode('utf-8'), 'updatedAt': info.st_mtime,
            'version': hashlib.sha256(content).hexdigest()}


def artifacts(directory):
    manifest = directory / 'artifacts.json'
    result = []
    for item in read(manifest) if manifest.exists() else []:
        entry = dict(item)
        try:
            entry.update(artifact_file(item['path']))
        except (OSError, ValueError) as exc:
            entry['error'] = 'File unavailable. ' + str(exc)
        result.append(entry)
    return result


def register_artifact(args):
    path = args.file.resolve(strict=True)
    artifact_file(path)
    item = {'id': hashlib.sha256(str(path).encode()).hexdigest()[:16],
            'path': str(path), 'title': args.title or path.name}
    with lock(args.session_dir):
        manifest = args.session_dir / 'artifacts.json'
        entries = read(manifest) if manifest.exists() else []
        entries = [entry for entry in entries if entry['id'] != item['id']]
        if len(entries) >= 20:
            raise ValueError('At most 20 artifacts can be registered.')
        atomic(manifest, entries + [item])
    return {'status': 'registered', **item}


def html(snapshot, bridge=None, app=None):
    def safe(value):
        return json.dumps(value, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    values = {'__GRILL_SESSION__': safe(snapshot), '__GRILL_BRIDGE__': safe(bridge), '__GRILL_APP_STATE__': safe(app or {'answerState': update_answer_state({}, snapshot)})}
    values['__GRILL_CONFIDENCE_CSS__'] = (ASSET.parent / 'confidence.css').read_text()
    values['__GRILL_CONFIDENCE_JS__'] = (ASSET.parent / 'confidence.js').read_text()
    values['__GRILL_HELP_CSS__'] = (ASSET.parent / 'question-help.css').read_text()
    values['__GRILL_HELP_JS__'] = (ASSET.parent / 'question-help.js').read_text()
    return re.sub('|'.join(values), lambda match: values[match[0]], ASSET.read_text())


def dependencies(node):
    return sorted(set(filter(None, [node.get('parentId'), *node.get('dependsOn', [])])))


def update_answer_state(previous, snapshot, confirmed=()):
    """Persist revision facts; the canvas derives review status from these facts."""
    old_session = previous.get('session', {})
    old_nodes = {node['id']: node for node in old_session.get('nodes', [])}
    def decision_context(node, design):
        constraints = {item['id']: item['statement'] for item in design.get('constraints', [])}
        return (node['question'], dependencies(node),
                sorted((ident, constraints.get(ident)) for ident in node.get('constraintIds', [])))
    records = previous.get('answerState', {})
    revision = snapshot['revision']
    result = {}
    for node in snapshot['nodes']:
        old = old_nodes.get(node['id'])
        record = records.get(node['id'], {'changedAt': previous.get('session', {}).get('revision', revision),
                                         'confirmedAt': previous.get('session', {}).get('revision', revision) if old and old.get('answer') else 0})
        answer_changed = old is None or old['answer'] != node['answer']
        context_changed = old is None or decision_context(old, old_session) != decision_context(node, snapshot)
        result[node['id']] = {
            'changedAt': revision if answer_changed or context_changed else record['changedAt'],
            'confirmedAt': (revision if node['answer'] else 0) if answer_changed or node['id'] in confirmed else record['confirmedAt'],
        }
    return result


def require_question_help(snapshot, records):
    """Match the canvas freshness rules before a new interview revision is shown."""
    nodes = {node['id']: node for node in snapshot['nodes']}
    latest = {}
    def context_revision(ident):
        if ident not in latest:
            latest[ident] = max([records[ident]['changedAt'], *(context_revision(dep) for dep in dependencies(nodes[ident]))])
        return latest[ident]
    missing = []
    for node in snapshot['nodes']:
        help_data = node.get('help')
        recommendation = '\n\n'.join(filter(None, [node.get('agentRecommendationSummary'), node.get('agentRecommendation')]))
        if (not help_data or help_data['sourceQuestion'] != node['question']
                or help_data['sourceRecommendation'] != recommendation
                or help_data['basedOnRevision'] < context_revision(node['id'])):
            missing.append(node['id'])
    if missing:
        raise ValueError('Prepare or refresh ELI-15, ELI-18, and a walkthrough before publishing: '
                         + ', '.join(missing) + '. See references/question-help.md.')


def current_answer(state, ident):
    nodes = {node['id']: node for node in state['session']['nodes']}
    records = state.get('answerState') or update_answer_state({}, state['session'])
    evaluated, visiting = {}, set()
    def evaluate(key):
        if key in evaluated:
            return evaluated[key]
        if key not in nodes or key in visiting:
            return False, float('inf')
        visiting.add(key)
        node = nodes[key]
        parents = [evaluate(dep) for dep in dependencies(node)]
        latest_change = max([records[key]['changedAt'], *(changed for _, changed in parents)])
        current = bool(node['answer']) and all(current for current, _ in parents) and latest_change <= records[key]['confirmedAt']
        visiting.remove(key)
        evaluated[key] = current, latest_change
        return evaluated[key]
    return evaluate(ident)[0]


def read_artifact(value):
    """An export wraps the authored design with application-owned restore data."""
    exported = isinstance(value, dict) and 'session' in value
    snapshot = validate(value['session'] if exported else value)
    app = {'answerState': update_answer_state({}, snapshot), 'drafts': {}, 'draftContexts': {}, 'pending': []}
    if not exported:
        return snapshot, app, False
    records = value.get('answerState')
    if not isinstance(records, dict) or set(records) != {node['id'] for node in snapshot['nodes']}:
        raise ValueError('Export must include revision history for every question.')
    for record in records.values():
        if not isinstance(record, dict) or set(record) != {'changedAt', 'confirmedAt'} or any(type(v) is not int or not 0 <= v <= snapshot['revision'] for v in record.values()):
            raise ValueError('Invalid answer revision history.')
    app['answerState'] = records
    for field in ('drafts', 'draftContexts'):
        item = value.get(field, {})
        if not isinstance(item, dict):
            raise ValueError(f'Invalid exported {field}.')
        app[field] = item
    if any(not isinstance(text, str) for text in app['drafts'].values()):
        raise ValueError('Exported drafts must be text.')
    for context in app['draftContexts'].values():
        if not isinstance(context, dict) or type(context.get('baseRevision')) is not int or not 1 <= context['baseRevision'] <= snapshot['revision'] or not isinstance(context.get('previousAnswer'), (str, type(None))):
            raise ValueError('Invalid exported draft context.')
    receipts = value.get('pending', [])
    if not isinstance(receipts, list):
        raise ValueError('Invalid exported pending replies.')
    ids, answered = set(), set()
    nodes = {node['id']: node for node in snapshot['nodes']}
    for receipt in receipts:
        if not isinstance(receipt, dict) or not re.fullmatch(r'[a-f0-9-]{36}', str(receipt.get('id', ''))) or receipt['id'] in ids:
            raise ValueError('Invalid exported receipt ID.')
        if receipt.get('kind') not in ('answer', 'clear', 'pause', 'help') or receipt.get('sessionId') != snapshot['id'] or type(receipt.get('baseRevision')) is not int or not 1 <= receipt['baseRevision'] <= snapshot['revision']:
            raise ValueError('Invalid exported receipt context.')
        if not isinstance(receipt.get('createdAt'), (int, float)):
            raise ValueError('Invalid exported receipt time.')
        if receipt['kind'] != 'pause' and (receipt.get('nodeId') not in nodes or not isinstance(receipt.get('text'), str)):
            raise ValueError('Exported receipt must reference a current question.')
        if receipt['kind'] == 'help' and not isinstance(receipt.get('question'), str):
            raise ValueError('Exported help requests must include the original question.')
        if receipt['kind'] == 'answer':
            if receipt['nodeId'] in answered or receipt['text'] != nodes[receipt['nodeId']]['answer']:
                raise ValueError('Exported pending answer must match the current answer.')
            answered.add(receipt['nodeId'])
        ids.add(receipt['id'])
    app['pending'] = receipts
    completed = value.get('completedRevision')
    if completed is not None:
        if type(completed) is not int or completed != snapshot['revision'] or any(e['kind'] != 'help' for e in receipts) or not snapshot['nodes'] or not all(current_answer({'session': snapshot, **app}, n['id']) for n in snapshot['nodes']):
            raise ValueError('Completion must reference a fully reviewed revision with no pending answer or pause receipts.')
        app['completedRevision'] = completed
    return snapshot, app, True


def pending(state):
    acknowledged = set(state.get('acknowledged', []))
    all_events = state.get('events', [])
    superseded = {event.get('replaces') for event in all_events}
    return sorted((event for event in all_events if event['id'] not in acknowledged | superseded), key=lambda event: event['createdAt'])


def assert_event(state, ident):
    if not any(event['id'] == ident for event in state.get('events', [])):
        raise ValueError('Cannot acknowledge an unknown event.')


def receive(directory, ident):
    with lock(directory):
        state = read(directory / 'state.json')
        event = next((e for e in pending(state) if e['id'] == ident), None)
        if event is None:
            raise ValueError('This receipt was processed or replaced. Read the latest pending answer.')
        if 'receivedAt' not in event:
            event['receivedAt'] = time.time()
            atomic(directory / 'state.json', state)
        return event


def timing_report(directory):
    state = read(directory / 'state.json')
    rows = []
    for event in state.get('events', []):
        receipt = directory / 'deliveries' / (event['id'] + '.json')
        delivery = read(receipt) if receipt.exists() else {}
        times = {key: event[key] for key in ('createdAt', 'receivedAt', 'publishedAt', 'acknowledgedAt') if key in event}
        times.update({key: delivery[key] for key in ('queuedAt', 'sendingAt', 'sentAt') if key in delivery})
        rows.append({'id': event['id'], 'nodeId': event.get('nodeId'), 'times': times,
                     'secondsFromSave': {key: round(value - event['createdAt'], 3) for key, value in times.items() if key != 'createdAt'}})
    return {'events': rows}


def publish(args):
    snapshot, restored, exported = read_artifact(read(args.snapshot))
    directory = args.session_dir
    with lock(directory):
        path = directory / 'state.json'
        old = read(path) if path.exists() else None
        revision = old['session']['revision'] if old else 0
        if revision != args.expected_revision:
            raise ValueError(f'Revision conflict: expected {args.expected_revision}, current {revision}.')
        if not (exported and old is None) and snapshot['revision'] != revision + 1:
            raise ValueError('New revision must equal current revision plus one.')
        if old and snapshot['id'] != old['session']['id']:
            raise ValueError('Session ID cannot change; use a new session directory.')
        acknowledged = old.get('acknowledged', []) if old else []
        if args.ack:
            assert_event(old or {}, args.ack)
            if any(event.get('replaces') == args.ack for event in old.get('events', [])):
                raise ValueError('This answer was replaced. Read the latest pending answer before publishing.')
            acknowledged = list(dict.fromkeys(acknowledged + [args.ack]))
        help_only = bool(args.ack and next(e for e in old['events'] if e['id'] == args.ack)['kind'] == 'help')
        if help_only:
            def decisions(design):
                return {**design, 'revision': 0, 'nodes': [{key: value for key, value in node.items() if key != 'help'} for node in design['nodes']]}
            if decisions(snapshot) != decisions(old['session']):
                raise ValueError('A help publication must preserve the interview and all answers; change only help content.')
            event = next(e for e in old['events'] if e['id'] == args.ack)
            node = next((n for n in snapshot['nodes'] if n['id'] == event['nodeId']), None)
            help_data = node.get('help', {}) if node else {}
            recommendation = '\n\n'.join(filter(None, [node.get('agentRecommendationSummary'), node.get('agentRecommendation')])) if node else ''
            if not help_data or help_data['sourceQuestion'] != node['question'] or help_data['sourceRecommendation'] != recommendation or help_data['basedOnRevision'] != snapshot['revision']:
                raise ValueError('Publish current question help before acknowledging its request.')
        if old:
            next_nodes = {node['id']: node for node in snapshot['nodes']}
            old_nodes = {node['id']: node for node in old['session']['nodes']}
            for event in pending(old):
                if event['kind'] in ('answer', 'clear') and event['id'] != args.ack:
                    ident = event['nodeId']
                    if ident not in next_nodes or next_nodes[ident]['answer'] != old_nodes[ident]['answer']:
                        raise ValueError('Preserve current answers until their latest receipt is processed.')
            app = {'answerState': update_answer_state(old, snapshot)}
        else:
            app = {'answerState': restored['answerState'], 'drafts': restored['drafts'],
                   'draftContexts': restored['draftContexts'], 'events': restored['pending']}
        if getattr(args, 'require_help', False):
            require_question_help(snapshot, app['answerState'])
        if args.ack:
            next(e for e in old['events'] if e['id'] == args.ack)['publishedAt'] = time.time()
        updated = {**(old or {}), **app, 'session': snapshot, 'acknowledged': acknowledged}
        updated.pop('completedRevision', None)
        if getattr(args, 'complete', False) or (old is None and restored.get('completedRevision') == snapshot['revision']) or (help_only and old.get('completedRevision') == revision):
            if any(e['kind'] != 'help' for e in pending(updated)) or not snapshot['nodes'] or not all(current_answer(updated, n['id']) for n in snapshot['nodes']):
                raise ValueError('Complete the interview only after all answers are reviewed and pending answer or pause receipts are acknowledged.')
            updated['completedRevision'] = snapshot['revision']
        atomic(path, updated)
    return {'status': 'published', 'revision': snapshot['revision']}


class RevisionConflict(ValueError):
    pass


def clear_answer(directory, data):
    """Caller holds the lock. Answer, revision facts, and receipt commit together."""
    path = directory / 'state.json'
    state = read(path)
    for event in state.get('events', []):
        if event['id'] == data['id']:
            if event['kind'] != 'clear' or event['nodeId'] != data.get('nodeId'):
                raise ValueError('Submission ID is already in use.')
            return event, False
    session = state['session']
    if type(data.get('baseRevision')) is not int or data['baseRevision'] != session['revision']:
        raise RevisionConflict('The design changed. Review the latest answer, then clear it again.')
    node = next((node for node in session['nodes'] if node['id'] == data.get('nodeId')), None)
    if not node:
        raise ValueError('Question no longer exists.')
    if not node['answer']:
        raise ValueError('This question has no answer to clear.')
    cleared = [event for event in pending(state) if event['kind'] == 'answer' and event['nodeId'] == node['id']]
    affected = {node['id']}
    while True:
        downstream = {item['id'] for item in session['nodes'] if affected.intersection(dependencies(item))}
        if downstream <= affected:
            break
        affected |= downstream
    review = [item['id'] for item in session['nodes'] if item['id'] != node['id'] and item['id'] in affected and item['answer']]
    event = {'id': data['id'], 'kind': 'clear', 'nodeId': node['id'], 'title': node['title'],
             'question': node['question'], 'baseRevision': session['revision'], 'createdAt': time.time(),
             'sessionId': session['id'], 'previousAnswer': node['answer'], 'clearedReplies': cleared,
             'affectedNodeIds': review,
             'text': f"The user cleared the answer to {node['id']}: {node['question']}. Keep it unanswered until a new answer is provided. Review dependent answers: {', '.join(review) or 'none'}."}
    previous = json.loads(json.dumps(state))
    node['answer'] = None
    session['revision'] += 1
    state.pop('completedRevision', None)
    state['answerState'] = update_answer_state(previous, session)
    state['acknowledged'] = list(dict.fromkeys(state.get('acknowledged', []) + [reply['id'] for reply in cleared]))
    if connection(directory)['transport'] == 'codex-queue':
        event['deliveryRequested'] = {key: connection(directory).get(key) for key in ('provider', 'sessionId', 'transport')}
    state.setdefault('events', []).append(event)
    atomic(path, state)
    return event, True


def connection(directory):
    path = directory / 'connection.json'
    return read(path) if path.exists() else {'transport': 'inbox'}


def verify_codex_thread(executable, ident):
    process = subprocess.Popen([executable, 'app-server', 'proxy'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    try:
        buffered = b''
        def request(message):
            nonlocal buffered
            process.stdin.write((json.dumps(message) + '\n').encode()); process.stdin.flush()
            deadline = time.monotonic() + 5
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if b'\n' not in buffered:
                        if not selector.select(max(0, deadline - time.monotonic())):
                            break
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        buffered += chunk
                        if len(buffered) > LIMIT:
                            raise ValueError('The Codex host returned an oversized response.')
                        continue
                    line, buffered = buffered.split(b'\n', 1)
                    response = json.loads(line)
                    if response.get('id') == message['id']:
                        if 'error' in response:
                            raise ValueError('The running Codex host could not verify this chat.')
                        return response['result']
            raise ValueError('The running Codex host did not confirm this chat.')
        request({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'grill_ui', 'version': '1'}}})
        process.stdin.write(b'{"method":"initialized"}\n'); process.stdin.flush()
        result = request({'id': 2, 'method': 'thread/read', 'params': {'threadId': ident}})
        thread = result.get('thread', {})
        if thread.get('id') != ident or thread.get('status', {}).get('type') not in ('idle', 'active'):
            raise ValueError('This chat is not loaded in the shared Codex host. Use the live inbox listener.')
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()


def bind(args):
    if not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', args.agent_session):
        raise ValueError('Use the exact agent session UUID, not a name or the most recent session.')
    if args.transport == 'codex-queue' and args.provider != 'codex':
        raise ValueError('codex-queue requires a Codex session.')
    config = {'provider': args.provider, 'sessionId': args.agent_session,
              'transport': args.transport, 'cwd': str(args.cwd.resolve())}
    if args.transport in ('auto', 'codex-queue'):
        executable = shutil.which('codex')
        try:
            if args.provider != 'codex' or not executable:
                raise ValueError('Direct delivery is unavailable; use the live inbox listener.')
            probe = subprocess.run([executable, 'app-server', 'daemon', 'version'], capture_output=True, text=True, timeout=5)
            if probe.returncode:
                raise ValueError('The shared Codex host is unavailable; use the live inbox listener.')
            verify_codex_thread(executable, args.agent_session)
            config.update(transport='codex-queue', executable=executable)
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            if args.transport != 'auto':
                raise
            config.update(transport='inbox', reason=str(error))
    with lock(args.session_dir):
        atomic(args.session_dir / 'connection.json', config)
    return {'status': 'bound', 'connection': config}


def delivery_prompt(directory, event):
    intro = (f'Continue the grill-me-ui interview in this existing session. '
             f'Read {Path(__file__).resolve().parent.parent / "SKILL.md"}. '
             f'The canvas session directory is {directory.resolve()}. '
             f'First run python3 {shlex.quote(str(Path(__file__).resolve()))} receive --session-dir {shlex.quote(str(directory.resolve()))} --event {event["id"]} to confirm receipt, then read state.json. ')
    if event.get('kind') == 'help':
        return (intro + 'This is a help event. Read references/question-help.md. Prepare ELI-15 (really simple), ELI-18, and a concrete scenario walkthrough for the current question. '
                'Publish only help content with --ack for this receipt, preserving every question, recommendation, and answer. Help is a request for understanding, never an answer or implementation approval. '
                'On a revision conflict, reread current state. If this receipt is acknowledged or replaced, stop processing it. Then resume the interview loop if active.')
    return (intro + 'If it is a pause event, acknowledge it and pause the interview. For a clear event, the canvas already reopened the question and marked dependent answers for review; do not restore the cleared answer or apply the clear again after a newer answer. Otherwise treat its text as the user answer. Reconcile against the current revision, preserve unrelated answers, '
            'Publish the next useful question with prepared ELI-15, ELI-18, and scenario help, using --require-help and --ack for this event before optional research or glossary/ADR maintenance. If research is essential, publish the known next question without inventing a recommendation. Then do the supporting work. Do not batch answers. '
            'Do not implement the proposed design. If this receipt is already acknowledged or replaced, do not process it. Read the latest pending answer instead.')


def deliver(directory, event):
    config = connection(directory)
    if config['transport'] != 'codex-queue':
        receipt = directory / 'deliveries' / (event['id'] + '.json')
        if receipt.exists() and read(receipt).get('status') == 'queued':
            result = {'status': 'failed', 'detail': 'The destination changed before delivery. Your answer is saved.'}
            with lock(directory):
                atomic(receipt, result)
            return result
        return {'status': 'inbox'}
    receipt = directory / 'deliveries' / (event['id'] + '.json')
    with lock(directory):
        if not any(item['id'] == event['id'] for item in pending(read(directory / 'state.json'))):
            return {'status': 'superseded'}
        previous = read(receipt) if receipt.exists() else {}
        if previous and previous['status'] != 'queued':
            return previous
        route = {key: config.get(key) for key in ('provider', 'sessionId', 'transport')}
        if previous.get('route', route) != route:
            result = {**previous, 'status': 'failed', 'detail': 'The destination changed before delivery. Your answer is saved.'}
            atomic(receipt, result)
            return result
        result = {**previous, 'status': 'sending', 'sendingAt': time.time()}
        atomic(receipt, result)
    try:
        executable = config['executable']
        probe = subprocess.run([executable, 'app-server', 'daemon', 'version'],
                               capture_output=True, text=True, timeout=10)
        if probe.returncode:
            result = {'status': 'failed', 'detail': 'Codex is unavailable. Your reply is saved; use Copy instead.'}
        else:
            sent = subprocess.run([executable, 'queue', '--thread', config['sessionId'],
                                   '--message', delivery_prompt(directory, event)],
                                  cwd=config['cwd'], capture_output=True, text=True, timeout=20)
            result = ({'status': 'sent'} if sent.returncode == 0 else
                      {'status': 'unknown', 'detail': 'Codex did not confirm delivery. Check the chat before copying to avoid a duplicate.'})
    except (OSError, subprocess.TimeoutExpired):
        result = {'status': 'unknown', 'detail': 'Delivery could not be confirmed. Your reply is saved. Check the chat before copying.'}
    with lock(directory):
        result = {**(read(receipt) if receipt.exists() else {}), **result}
        if result['status'] == 'sent':
            result['sentAt'] = time.time()
        atomic(receipt, result)
    return result


class DeliveryWorker:
    """One bounded worker per server; durable queued receipts survive a restart."""
    def __init__(self, directory):
        self.directory = directory
        self.wake = threading.Event()
        self.stopped = threading.Event()
        with lock(directory):
            for path in (directory / 'deliveries').glob('*.json'):
                receipt = read(path)
                if receipt.get('status') == 'sending':
                    atomic(path, {**receipt, 'status': 'unknown', 'detail': 'Delivery was interrupted. Check the chat before copying.'})
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def schedule(self, event):
        if not event.get('deliveryRequested'):
            return {'status': 'inbox'}
        with lock(self.directory):
            config = connection(self.directory)
            path = self.directory / 'deliveries' / (event['id'] + '.json')
            route = {key: config.get(key) for key in ('provider', 'sessionId', 'transport')}
            if event.get('deliveryRequested', route) != route:
                result = {'status': 'failed', 'detail': 'The destination changed before delivery. Your answer is saved.'}
                atomic(path, result)
                return result
            if config['transport'] != 'codex-queue':
                return {'status': 'inbox'}
            if not path.exists():
                atomic(path, {'status': 'queued', 'queuedAt': time.time(),
                              'route': {key: config.get(key) for key in ('provider', 'sessionId', 'transport')}})
            result = read(path)
        self.wake.set()
        return result

    def run(self):
        while not self.stopped.is_set():
            self.wake.clear()
            with lock(self.directory):
                events = pending(read(self.directory / 'state.json'))
            for event in events:
                if self.stopped.is_set():
                    return
                path = self.directory / 'deliveries' / (event['id'] + '.json')
                if event.get('deliveryRequested') and not path.exists():
                    self.schedule(event)
                if path.exists() and read(path).get('status') == 'queued':
                    try:
                        deliver(self.directory, event)
                    except Exception:
                        with lock(self.directory):
                            atomic(path, {**read(path), 'status': 'unknown', 'detail': 'Delivery could not be confirmed. Check the chat.'})
            self.wake.wait(1)

    def close(self):
        self.stopped.set(); self.wake.set(); self.thread.join(timeout=1)


def update_signature(directory):
    # Small stat checks observe CLI publications and canonical-file edits across processes.
    paths = [directory / name for name in ('state.json', 'connection.json', 'deliveries', 'artifacts.json')]
    manifest = directory / 'artifacts.json'
    if manifest.exists():
        paths.extend(Path(item['path']) for item in read(manifest))
    stamps = []
    for path in paths:
        try:
            info = path.stat(); stamps.append((str(path), info.st_mtime_ns, info.st_size))
        except OSError:
            stamps.append((str(path), None))
    presence = directory / 'presence.json'
    listening = presence.exists() and time.time() - read(presence).get('at', 0) < LEASE
    return (stamps, listening)


def serve(args):
    args.session_dir.mkdir(parents=True, exist_ok=True)
    with (args.session_dir / '.server.lock').open('a') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('This session already has a running server.')
        serve_session(args)


def serve_session(args):
    directory = args.session_dir
    with lock(directory):
        state = read(directory / 'state.json')
        validate(state['session'])
        if 'answerState' not in state:
            state['answerState'] = update_answer_state({}, state['session'])
            atomic(directory / 'state.json', state)
        token_path = directory / '.server-token.json'
        if not token_path.exists():
            atomic(token_path, {'token': secrets.token_urlsafe(24)})
        token = read(token_path)['token']
        if not re.fullmatch(r'[A-Za-z0-9_-]{24,80}', token):
            raise ValueError('Invalid server token.')
    prefix = '/s/' + token + '/'
    stream_slots = threading.BoundedSemaphore(8)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, data, content_type='application/json'):
            payload = data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src data:; font-src data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host() or self.path not in (prefix, prefix + 'state', prefix + 'updates'):
                return self.respond(404, {'error': 'Not found'})
            if self.path == prefix + 'updates':
                return self.stream_updates()
            with lock(directory):
                state = read(directory / 'state.json')
                if self.path == prefix:
                    return self.respond(200, html(state['session'], {'base': prefix, 'connection': connection(directory), 'sessionDir': str(directory.resolve())}, {'answerState': state.get('answerState') or update_answer_state({}, state['session']), 'drafts': state.get('drafts', {}), 'draftContexts': state.get('draftContexts', {}), 'pending': pending(state), 'completedRevision': state.get('completedRevision')}), 'text/html')
                presence = read(directory / 'presence.json') if (directory / 'presence.json').exists() else {}
                state['listening'] = time.time() - presence.get('at', 0) < LEASE
                state['connection'] = connection(directory)
                state['pending'] = pending(state)
                for event in state['pending']:
                    receipt = directory / 'deliveries' / (event['id'] + '.json')
                    event['delivery'] = read(receipt) if receipt.exists() else {'status': 'inbox'}
            state['artifacts'] = artifacts(directory)
            self.respond(200, state)

        def stream_updates(self):
            if not stream_slots.acquire(blocking=False):
                return self.respond(503, {'error': 'Too many update streams'})
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(b'retry: 1000\n\n'); self.wfile.flush()
                previous, deadline, heartbeat = None, time.monotonic() + 30, time.monotonic()
                while time.monotonic() < deadline:
                    signature = update_signature(directory)
                    if signature != previous:
                        self.wfile.write(b'data: changed\n\n'); self.wfile.flush()
                        previous = signature
                    elif time.monotonic() - heartbeat > 10:
                        self.wfile.write(b': heartbeat\n\n'); self.wfile.flush()
                        heartbeat = time.monotonic()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                stream_slots.release()

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.path not in (prefix + 'reply', prefix + 'clear') or self.headers.get('Origin') != origin:
                return self.respond(403, {'error': 'Only the local canvas may submit replies.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= LIMIT:
                    return self.respond(413, {'error': 'Reply must be smaller than 2 MB.'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.respond(415, {'error': 'Use JSON.'})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or not isinstance(data.get('id'), str) or not re.fullmatch(r'[a-f0-9-]{36}', data['id']):
                    raise ValueError('Invalid submission ID.')
                if self.path == prefix + 'clear':
                    with lock(directory):
                        event, changed = clear_answer(directory, data)
                    result = worker.schedule(event) if changed else None
                    return self.respond(201 if changed else 200, {'status': 'cleared', 'id': event['id'], 'affectedNodeIds': event['affectedNodeIds'], 'delivery': result})
                with lock(directory):
                    state = read(directory / 'state.json')
                    for receipt in state.get('events', []):
                        if receipt['id'] == data['id']:
                            if receipt['kind'] != data.get('kind', 'answer') or receipt.get('nodeId') != data.get('nodeId'):
                                raise ValueError('Submission ID is already in use.')
                            return self.respond(200, {'status': 'saved', 'id': data['id']})
                    kind = data.get('kind', 'answer')
                    if kind not in ('answer', 'pause', 'help'):
                        raise ValueError('Unknown event kind.')
                    if type(data.get('baseRevision')) is not int or not 1 <= data['baseRevision'] <= state['session']['revision']:
                        raise ValueError('Invalid base revision.')
                    event = {'id': data['id'], 'kind': kind, 'baseRevision': data['baseRevision'], 'createdAt': time.time(), 'sessionId': state['session']['id']}
                    if kind == 'answer':
                        n = next((n for n in state['session']['nodes'] if n['id'] == data.get('nodeId')), None)
                        if not n:
                            raise ValueError('Question no longer exists. Reload the session and copy your draft if needed.')
                        if not isinstance(data.get('text'), str) or not data['text'].strip():
                            raise ValueError('Answer cannot be empty.')
                        saved = next((e for e in pending(state) if e['kind'] == 'answer' and e.get('nodeId') == n['id']), None)
                        if data.get('replaces') != (saved['id'] if saved else None):
                            raise RevisionConflict('This answer changed since you opened it. Review the latest saved answer, then try again. Your draft is retained.')
                        if saved:
                            event['replaces'] = saved['id']
                        if data.get('previousAnswer') != n['answer']:
                            raise RevisionConflict('This answer changed. Review the current answer before replacing it. Your draft is retained.')
                        records = state.get('answerState') or update_answer_state({}, state['session'])
                        by_id = {node['id']: node for node in state['session']['nodes']}
                        relevant = {n['id']}
                        queue = [n['id']]
                        while queue:
                            for dep in dependencies(by_id[queue.pop()]):
                                if dep not in relevant:
                                    relevant.add(dep); queue.append(dep)
                        if any(records[ident]['changedAt'] > data['baseRevision'] for ident in relevant):
                            raise RevisionConflict('This question or a prerequisite changed. Review it before submitting. Your draft is retained.')
                        confirmation = data.get('confirmation', False)
                        if type(confirmation) is not bool:
                            raise ValueError('Invalid confirmation.')
                        if confirmation and (data['baseRevision'] != state['session']['revision'] or not n['answer'] or data['text'].strip() != n['answer'] or not all(current_answer(state, dep) for dep in dependencies(n))):
                            raise RevisionConflict('Review the current prerequisite answers before keeping this answer.')
                        event.update(nodeId=n['id'], title=n['title'], question=n['question'], text=data['text'].strip(), previousAnswer=n['answer'], confirmation=confirmation)
                        previous = json.loads(json.dumps(state))
                        n['answer'] = event['text']
                        state['session']['revision'] += 1
                        state.pop('completedRevision', None)
                        state['answerState'] = update_answer_state(previous, state['session'], [n['id']])
                        event['savedRevision'] = state['session']['revision']
                    if kind == 'help':
                        n = next((n for n in state['session']['nodes'] if n['id'] == data.get('nodeId')), None)
                        if not n or data.get('question') != n['question']:
                            raise RevisionConflict('This question changed. Reopen help for the current question.')
                        previous = next((e for e in pending(state) if e['kind'] == 'help' and e.get('nodeId') == n['id']), None)
                        if previous and previous['question'] == n['question'] and previous['baseRevision'] == state['session']['revision']:
                            return self.respond(200, {'status': 'saved', 'id': previous['id']})
                        if previous:
                            event['replaces'] = previous['id']
                        event.update(nodeId=n['id'], title=n['title'], question=n['question'],
                                     baseRevision=state['session']['revision'],
                                     text='Explain this question at ELI-15 (really simple) and ELI-18, and walk me through a concrete scenario. Preserve my answer.')
                    if connection(directory)['transport'] == 'codex-queue':
                        event['deliveryRequested'] = {key: connection(directory).get(key) for key in ('provider', 'sessionId', 'transport')}
                    state.setdefault('events', []).append(event)
                    atomic(directory / 'state.json', state)
                result = worker.schedule(event)
                self.respond(201, {'status': 'saved', 'id': data['id'], 'delivery': result})
            except RevisionConflict as exc:
                self.respond(409, {'error': str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                self.respond(400, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    worker = DeliveryWorker(directory)
    print(json.dumps({'status': 'serving', 'url': f'http://127.0.0.1:{server.server_port}{prefix}', 'sessionDir': str(directory)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()
        server.server_close()


def wait(args):
    deadline = time.monotonic() + args.timeout
    next_presence = 0
    while True:
        with lock(args.session_dir):
            if time.monotonic() >= next_presence:
                atomic(args.session_dir / 'presence.json', {'at': time.time()})
                next_presence = time.monotonic() + 1
            state = read(args.session_dir / 'state.json')
            inbox = pending(state)
        if inbox:
            event = next((e for e in inbox if e['kind'] == 'pause'), inbox[0])
            try:
                event = receive(args.session_dir, event['id'])
            except ValueError:
                continue
            return {'status': 'paused' if event['kind'] == 'pause' else 'event', 'event': event}
        if time.monotonic() >= deadline:
            return {'status': 'timeout'}
        time.sleep(min(0.1, max(0, deadline - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('publish', 'serve', 'wait', 'offline', 'ack', 'receive', 'timings'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--session-dir', required=True, type=Path)
        if name == 'publish':
            cmd.add_argument('--snapshot', required=True, type=Path)
            cmd.add_argument('--expected-revision', required=True, type=int)
            cmd.add_argument('--ack')
            cmd.add_argument('--require-help', action='store_true', help='Require current prepared explanations and a walkthrough for every question.')
            cmd.add_argument('--complete', action='store_true', help='Confirm the interview is complete after reviewing every answer.')
        elif name == 'serve':
            cmd.add_argument('--port', type=int, default=0)
        elif name == 'wait':
            cmd.add_argument('--timeout', type=int, default=50, choices=range(1, 61), metavar='1-60')
        elif name in ('ack', 'receive'):
            cmd.add_argument('--event', required=True)
    cmd = commands.add_parser('bind')
    cmd.add_argument('--session-dir', required=True, type=Path)
    cmd.add_argument('--provider', required=True, choices=['codex', 'claude'])
    cmd.add_argument('--agent-session', required=True)
    cmd.add_argument('--transport', choices=['auto', 'inbox', 'codex-queue'], default='auto')
    cmd.add_argument('--cwd', type=Path, default=Path.cwd())
    cmd = commands.add_parser('render')
    cmd.add_argument('--snapshot', required=True, type=Path)
    cmd.add_argument('--output', required=True, type=Path)
    cmd.add_argument('--require-help', action='store_true')
    cmd = commands.add_parser('validate', help='Validate a reusable design-tree artifact without publishing.')
    cmd.add_argument('--snapshot', required=True, type=Path)
    cmd.add_argument('--require-help', action='store_true')
    cmd = commands.add_parser('artifact', help='Show an official Markdown/text file live in the canvas.')
    cmd.add_argument('--session-dir', required=True, type=Path)
    cmd.add_argument('--file', required=True, type=Path)
    cmd.add_argument('--title')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            snapshot, app, exported = read_artifact(read(args.snapshot))
            if args.require_help:
                # Raw snapshots lack history; publication checks against the live session.
                records = app['answerState'] if exported else {n['id']: {'changedAt': 0} for n in snapshot['nodes']}
                require_question_help(snapshot, records)
            result = {'status': 'valid', 'schemaVersion': snapshot['schemaVersion'], 'nodes': len(snapshot['nodes'])}
        elif args.command == 'artifact':
            result = register_artifact(args)
        elif args.command == 'bind':
            result = bind(args)
        elif args.command == 'publish':
            result = publish(args)
        elif args.command == 'serve':
            serve(args)
            return
        elif args.command == 'wait':
            result = wait(args)
        elif args.command == 'receive':
            result = {'status': 'received', 'event': receive(args.session_dir, args.event)}
        elif args.command == 'timings':
            result = timing_report(args.session_dir)
        elif args.command == 'offline':
            with lock(args.session_dir):
                atomic(args.session_dir / 'presence.json', {'at': 0})
            result = {'status': 'offline'}
        elif args.command == 'ack':
            with lock(args.session_dir):
                state = read(args.session_dir / 'state.json')
                assert_event(state, args.event)
                next(e for e in state['events'] if e['id'] == args.event)['acknowledgedAt'] = time.time()
                state['acknowledged'] = list(dict.fromkeys(state.get('acknowledged', []) + [args.event]))
                atomic(args.session_dir / 'state.json', state)
            result = {'status': 'acknowledged', 'id': args.event}
        else:
            snapshot, app, _ = read_artifact(read(args.snapshot))
            if args.require_help:
                require_question_help(snapshot, app['answerState'])
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(html(snapshot, app=app))
            result = {'status': 'rendered', 'path': str(args.output.resolve())}
        print(json.dumps(result), flush=True)
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
