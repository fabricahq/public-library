"""The reusable artifact retains evidence and rejects misleading or oversized context."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('grill', root / 'scripts/grill_ui.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
base = json.loads((root / 'examples/design-context.json').read_text())
assert g.validate(base) == base
direct = copy.deepcopy(base)
direct['nodes'][0]['answer'] = 'Yes.'
assert g.validate(direct)['nodes'][0]['answer'] == 'Yes.'
direct['nodes'][0]['answer'] = 'Yes, because I need offline access.'
assert g.validate(direct)['nodes'][0]['answer'] == direct['nodes'][0]['answer']
legacy = json.loads((root / 'examples/design.json').read_text())
assert g.validate(legacy)['schemaVersion'] == 1

def rejects(mutate):
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        g.validate(candidate)
    except ValueError:
        return
    raise AssertionError('Accepted invalid artifact: ' + repr(candidate))

rejects(lambda s: s.update(schemaVersion=2))
rejects(lambda s: s['nodes'][0].update(needsReview=True))
rejects(lambda s: s.update(answerState={}))
rejects(lambda s: s['nodes'][0].update(id='Q1\n'))
rejects(lambda s: s['nodes'][0].update(title='\u00a0'))
rejects(lambda s: s.update(schemaVersion=True))
rejects(lambda s: s.update(constraints=[dict(s['constraints'][0], id=f'C{i}') for i in range(8)]))
rejects(lambda s: s['constraints'][0].update(statement='x' * 161))
rejects(lambda s: s['constraints'][0].update(kind='requirement'))
rejects(lambda s: s['constraints'].append(s['constraints'][0]))
rejects(lambda s: s['nodes'][0].update(constraintIds=['missing']))
rejects(lambda s: s['nodes'][0]['assumptions'][0].update(status='probably'))
rejects(lambda s: s['nodes'][0]['alternatives'].append(s['nodes'][0]['alternatives'][0]))
rejects(lambda s: s['nodes'][0]['precedents'][0].update(url='javascript:alert(1)'))
rejects(lambda s: s['nodes'][0].update(research={'status':'needed','questions':['Which examples?']}))
rejects(lambda s: s['nodes'][0].update(assumptons=[]))
rejects(lambda s: s['nodes'][0].update(recommendation='Old field'))
rejects(lambda s: s['nodes'][0].update(recommendationSummary='Old field'))
without_url = copy.deepcopy(base)
without_url['nodes'][0]['precedents'][0].pop('url')
assert g.validate(without_url) == without_url
rejects(lambda s: s['nodes'][0]['precedents'][0].pop('insight'))
rejects(lambda s: s['nodes'][0]['precedents'][0].update(insight=' '))
rejects(lambda s: s['nodes'][0]['assumptions'].append(s['nodes'][0]['assumptions'][0]))
optional = copy.deepcopy(base)
for node in optional['nodes']:
    for field in ('assumptions', 'alternatives', 'precedents'):
        node.pop(field, None)
assert g.validate(optional) == optional
for field in ('assumptions', 'alternatives', 'precedents'):
    optional['nodes'][0][field] = []
assert g.validate(optional) == optional
seven = copy.deepcopy(base)
seven['constraints'] = [dict(base['constraints'][0], id=f'C{i}') for i in range(7)]
assert len(g.validate(seven)['constraints']) == 7
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    snapshot = directory / 'design-tree.json'
    snapshot.write_text(json.dumps(base))
    result = subprocess.run([sys.executable, str(root / 'scripts/grill_ui.py'), 'publish', '--session-dir', tmp, '--snapshot', str(snapshot), '--expected-revision', '0'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert g.read(directory / 'state.json')['session'] == base
    output = directory / 'canvas.html'
    result = subprocess.run([sys.executable, str(root / 'scripts/grill_ui.py'), 'render', '--snapshot', str(snapshot), '--output', str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    embedded, _ = json.JSONDecoder().raw_decode(output.read_text().split('let session = ', 1)[1])
    assert embedded == base
print('PASS structured context roundtrip, version, seven-constraint ceiling, references and evidence validation')

# Only changes to requirements linked to a question invalidate its confirmation.
previous = {'session': copy.deepcopy(base), 'answerState': g.update_answer_state({}, base)}
changed = copy.deepcopy(base); changed['revision'] += 1
changed['constraints'][0]['statement'] = 'Changed requirement'
records = g.update_answer_state(previous, changed)
linked = [n for n in changed['nodes'] if changed['constraints'][0]['id'] in n.get('constraintIds', [])]
assert linked and all(records[n['id']]['changedAt'] == changed['revision'] for n in linked)
for n in changed['nodes']:
    if n not in linked: assert records[n['id']] == previous['answerState'][n['id']]
reordered = copy.deepcopy(base); reordered['revision'] += 1; reordered['constraints'].reverse()
assert g.update_answer_state(previous, reordered) == previous['answerState']
print('PASS linked requirement changes invalidate only affected decision context')

shared = dict(id='shared-paths', title='Shared prerequisite paths', revision=1, nodes=[])
for i in range(70):
    shared['nodes'].append(dict(id=f'Q{i}', title=f'Q{i}', question='Keep this?', parentId=None, answer='Yes', dependsOn=[f'Q{j}' for j in range(max(0,i-2),i)]))
state = {'session':shared, 'answerState':g.update_answer_state({},shared)}
assert g.current_answer(state,'Q69')
state['answerState']['Q0']['changedAt']=2
assert not g.current_answer(state,'Q69')
print('PASS bounded traversal of overlapping prerequisite paths')
