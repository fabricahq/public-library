"""Confidence is optional evidence, not user confirmation or review history."""
import copy
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('grill', root / 'scripts/grill_ui.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
base = json.loads((root / 'examples/design-context.json').read_text())
assert g.validate(base)
assessed = copy.deepcopy(base)
node = assessed['nodes'][0]
node['contextConfidence'] = {'level': 'high', 'reason': 'Explicit in the specification.', 'evidence': 'Section 2: offline by default.'}
node['recommendationConfidence'] = {'level': 'low', 'reason': 'Storage limits need research.'}
assert g.validate(assessed)['nodes'][0]['contextConfidence'] == node['contextConfidence']
for invalid in ({'level':'certain','reason':'Known'}, {'level':'low'}, {'level':'high','reason':' '}, {'level':'low','reason':'Unknown','probability':.9}, None):
    candidate = copy.deepcopy(assessed)
    candidate['nodes'][0]['contextConfidence'] = invalid
    try: g.validate(candidate)
    except ValueError: pass
    else: raise AssertionError(f'Accepted invalid assessment: {invalid}')
prior = {'session':base, 'answerState':g.update_answer_state({},base)}
assessed['revision'] += 1
assert g.update_answer_state(prior,assessed) == prior['answerState'], 'Assessment changes must not alter answer review history'
restored, _, _ = g.read_artifact({'session':assessed, 'answerState':prior['answerState']})
assert restored['nodes'][0]['contextConfidence'] == node['contextConfidence']
rendered = g.html(assessed)
assert '__GRILL_CONFIDENCE_' not in rendered
assert 'function confidenceMatches' in rendered
assert '<script src=' not in rendered, 'Standalone rendering must embed feature assets'
print('PASS optional assessments, validation, restore, review independence, standalone embedding')
