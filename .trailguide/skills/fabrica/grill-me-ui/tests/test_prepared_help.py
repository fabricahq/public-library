"""The standard publishing workflow refuses missing/stale help atomically."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/grill_ui.py'
base = json.loads((ROOT / 'examples/question-help.json').read_text())
with tempfile.TemporaryDirectory(prefix='grill-prepared-help-') as tmp:
    directory = Path(tmp)
    source = directory / 'input.json'
    state_file = directory / 'state.json'
    def run(design, command='publish', strict=True):
        source.write_text(json.dumps(design))
        args = [sys.executable, str(SCRIPT), command, '--snapshot', str(source)]
        if strict: args += ['--require-help']
        if command == 'publish': args += ['--session-dir', tmp, '--expected-revision', str(design['revision'] - 1)]
        if command == 'render': args += ['--output', str(directory / 'out.html')]
        return subprocess.run(args, capture_output=True, text=True)
    assert run(base).returncode == 0
    base['revision'] = 2
    assert run(base, 'validate').returncode == 0, 'Raw validation accepts unchanged prepared help; publication checks history'
    assert run(base).returncode == 0, 'Unrelated publication keeps prior help'
    before = state_file.read_bytes()
    for change in ('missing', 'recommendation', 'question', 'new-node', 'prerequisite'):
        design = copy.deepcopy(base); design['revision'] = 3
        if change == 'missing': del design['nodes'][1]['help']
        if change == 'recommendation': design['nodes'][1]['agentRecommendation'] = 'Use a generic message.'
        if change == 'question': design['nodes'][1]['question'] = 'Should errors stay generic?'
        if change == 'new-node': design['nodes'].append({'id':'Q3','parentId':None,'title':'Another decision','question':'Should we retry?','answer':None})
        if change == 'prerequisite': design['nodes'][1]['parentId'] = 'Q1'
        result = run(design)
        assert result.returncode != 0, change
        assert ('Q3' if change == 'new-node' else 'Q2') in result.stderr
        assert state_file.read_bytes() == before, 'Refusal must not modify state'
    design = copy.deepcopy(base); design['revision'] = 3
    design['nodes'][1]['parentId'] = 'Q1'; design['nodes'][1]['help']['basedOnRevision'] = 3
    assert run(design).returncode == 0
    design['revision'] = 4; design['nodes'][0]['answer'] = 'Use the saved repository.'
    result = run(design)
    assert result.returncode != 0 and 'Q1, Q2' in result.stderr, 'Refresh help across the changed prerequisite path'
    for n in design['nodes']: n['help']['basedOnRevision'] = 4
    assert run(design).returncode == 0
    legacy = copy.deepcopy(base)
    del legacy['nodes'][1]['help']
    assert run(legacy, 'validate', strict=False).returncode == 0
    assert run(legacy, 'render', strict=False).returncode == 0
    assert run(legacy, 'validate').returncode != 0
    assert run(legacy, 'render').returncode != 0
print('PASS prepared-help publication, missing/stale refusals, affected prerequisites, atomic failure and legacy recovery')
