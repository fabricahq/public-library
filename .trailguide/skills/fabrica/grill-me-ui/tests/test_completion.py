"""Completion is an explicit reviewed revision, never inferred from answer count."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/grill_ui.py'

with tempfile.TemporaryDirectory(prefix='grill-completion-') as tmp:
    directory = Path(tmp)
    source = directory / 'input.json'
    session = json.loads((ROOT / 'examples/design-context.json').read_text())
    session['nodes'][1]['answer'] = 'Use examples.'
    def publish(expected, complete=False, success=True):
        source.write_text(json.dumps(session))
        result = subprocess.run([sys.executable, str(SCRIPT), 'publish', '--session-dir', tmp,
            '--snapshot', str(source), '--expected-revision', str(expected), *(['--complete'] if complete else [])], capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return json.loads((directory / 'state.json').read_text())
    state = publish(0)
    assert 'completedRevision' not in state, 'An answered tree alone is not completion'
    session['revision'] = 2
    state = publish(1, complete=True)
    assert state['completedRevision'] == 2
    session['revision'] = 3
    session['nodes'][0]['answer'] = 'Always show evidence.'
    unchanged = (directory / 'state.json').read_bytes()
    publish(2, complete=True, success=False)
    assert (directory / 'state.json').read_bytes() == unchanged, 'Failed completion is atomic'
    state = publish(2)
    assert 'completedRevision' not in state, 'A new publication invalidates completion'
    session['revision'] = 4
    session['nodes'][1]['answer'] = None
    publish(3, complete=True, success=False)
    session['nodes'] = []
    publish(3, complete=True, success=False)
    exported = {**state, 'pending': [], 'completedRevision': state['session']['revision']}
    source.write_text(json.dumps(exported))
    result = subprocess.run([sys.executable, str(SCRIPT), 'render', '--snapshot', str(source),
        '--output', str(directory / 'invalid.html')], capture_output=True, text=True)
    assert result.returncode != 0, 'An export cannot mark stale dependent answers complete'
print('PASS explicit completion, revision invalidation, stale/unanswered/empty rejection, atomic failure and restore validation')
