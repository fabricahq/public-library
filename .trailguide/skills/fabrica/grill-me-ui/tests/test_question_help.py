"""Help is a durable non-answer event, with atomic, current-content publication."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/grill_ui.py'
spec = importlib.util.spec_from_file_location('grill', SCRIPT)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
base = json.loads((ROOT / 'examples/question-help.json').read_text())
g.validate(base)
for mutate in ('future', 'missing-level', 'executable-visual', 'one-step'):
    invalid = copy.deepcopy(base)
    h = invalid['nodes'][0]['help']
    if mutate == 'future': h['basedOnRevision'] = 2
    if mutate == 'missing-level': del h['eli15']
    if mutate == 'executable-visual': h['walkthrough']['steps'][0]['visual']['html'] = '<script>alert(1)</script>'
    if mutate == 'one-step': h['walkthrough']['steps'] = h['walkthrough']['steps'][:1]
    try:
        g.validate(invalid)
        raise AssertionError('Accepted ' + mutate)
    except ValueError:
        pass

with tempfile.TemporaryDirectory(prefix='grill-help-') as tmp:
    directory = Path(tmp)
    source = directory / 'snapshot.json'
    def cli(*args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    def state(): return json.loads((directory / 'state.json').read_text())
    def publish(design, ack=None, success=True, complete=False):
        source.write_text(json.dumps(design))
        result = cli('publish', '--session-dir', tmp, '--snapshot', str(source), '--expected-revision', str(design['revision'] - 1), *(['--ack', ack] if ack else []), *(['--complete'] if complete else []))
        assert (result.returncode == 0) == success, result.stdout + result.stderr
    # Help on an already completed interview must not reopen its decisions.
    for node in base['nodes']: node['answer'] = 'Yes.'
    publish(base, complete=True)
    server = subprocess.Popen([sys.executable, str(SCRIPT), 'serve', '--session-dir', tmp], stdout=subprocess.PIPE, text=True)
    try:
        url = json.loads(server.stdout.readline())['url']
        def req(body):
            request = urllib.request.Request(url + 'reply', data=json.dumps(body).encode(), headers={'Content-Type':'application/json', 'Origin':url.split('/s/')[0]})
            try:
                with urllib.request.urlopen(request) as response: return response.status, json.loads(response.read())
            except urllib.error.HTTPError as error: return error.code, json.loads(error.read())
        before = state()
        event = {'id':str(uuid.uuid4()), 'kind':'help', 'nodeId':'Q1', 'question':base['nodes'][0]['question'], 'baseRevision':1}
        assert req({**event, 'nodeId':'missing'})[0] == 409
        assert req({**event, 'question':'old question'})[0] == 409
        assert req(event)[0] == 201
        assert req(event)[0] == 200
        assert req({**event, 'id':str(uuid.uuid4())}) == (200, {'status':'saved', 'id':event['id']})
        after = state()
        for field in ('session', 'answerState', 'completedRevision'): assert after[field] == before[field]
        assert len(g.pending(after)) == 1
        received = json.loads(cli('wait', '--session-dir', tmp, '--timeout','1').stdout)['event']
        assert received['kind'] == 'help' and received['receivedAt']
        prompt = g.delivery_prompt(directory, received)
        assert 'never an answer' in prompt and 'references/question-help.md' in prompt
        exported = {'session':after['session'], 'answerState':after['answerState'], 'pending':g.pending(after)}
        assert g.read_artifact(exported)[1]['pending'][0]['kind'] == 'help'
        other = {**event, 'id':str(uuid.uuid4()), 'nodeId':'Q2', 'question':base['nodes'][1]['question']}
        assert req(other)[0] == 201
        update = copy.deepcopy(base); update['revision'] = 2
        # An old explanation cannot be passed off as a newly prepared one.
        unchanged = (directory / 'state.json').read_bytes()
        publish(update, event['id'], success=False)
        assert unchanged == (directory / 'state.json').read_bytes()
        update['nodes'][0]['help']['basedOnRevision'] = 2
        invalid = copy.deepcopy(update); invalid['nodes'][0]['answer'] = 'Changed by agent'
        publish(invalid, event['id'], success=False)
        invalid = copy.deepcopy(update); invalid['nodes'][0]['help']['sourceQuestion'] = 'Wrong question'
        publish(invalid, event['id'], success=False)
        publish(update, event['id'])
        assert state()['completedRevision'] == 2
        assert state()['answerState'] == before['answerState']
        assert [e['id'] for e in g.pending(state())] == [other['id']]
        exported = {**state(), 'pending':g.pending(state())}
        assert g.read_artifact(exported)[1]['completedRevision'] == 2
        update = copy.deepcopy(state()['session']); update['revision'] = 3
        n = update['nodes'][1]; n['help'] = copy.deepcopy(base['nodes'][0]['help'])
        n['help'].update(basedOnRevision=3, sourceQuestion=n['question'], sourceRecommendation=n['agentRecommendationSummary']+'\n\n'+n['agentRecommendation'])
        publish(update, other['id'])
        assert state()['completedRevision'] == 3
        assert not g.pending(state())
        # A help ack preserves a separate, concurrently submitted answer receipt.
        answer = {'id':str(uuid.uuid4()), 'kind':'answer', 'nodeId':'Q2', 'baseRevision':3, 'previousAnswer':'Yes.', 'text':'Keep the failure message short.'}
        assert req(answer)[0] == 201
        event = {**event, 'id':str(uuid.uuid4()), 'baseRevision':4}
        assert req(event)[0] == 201
        update = copy.deepcopy(state()['session']); update['revision'] = 5; update['nodes'][0]['help']['basedOnRevision'] = 5
        publish(update, event['id'])
        assert [e['id'] for e in g.pending(state())] == [answer['id']]
        assert state()['session']['nodes'][1]['answer'] == answer['text']
        assert 'completedRevision' not in state()
        print('PASS help schema, durable delivery, deduplication, unchanged answers, atomic freshness checks, completion preservation and concurrent answer receipt')
    finally:
        server.terminate(); server.wait(timeout=5)
