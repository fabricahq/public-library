import base64
import importlib.util
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('grill', Path(__file__).resolve().parents[1] / 'scripts' / 'grill_ui.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

COMMIT = 'a' * 40


class FakeGitHub:
    """Stands in for `gh api`: serves the organization repository's files, or fails like an offline login."""

    def __init__(self, files=None, error=None):
        self.files, self.error, self.calls = files or {}, error, []

    def __call__(self, path):
        self.calls.append(path)
        if self.error:
            return None, self.error
        if path == 'repos/acme/.fabrica/commits/HEAD':
            return {'sha': COMMIT}, None
        for name, text in self.files.items():
            if path == f'repos/acme/.fabrica/contents/5k-grill-me/{name}?ref={COMMIT}':
                return {'content': base64.b64encode(text.encode()).decode()}, None
        return None, 'missing'


class Settings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name).resolve()
        self.repo = base / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', 'git@github.com:acme/widgets.git'], cwd=self.repo, check=True)
        self.original = g.gh_api, g.ORG_CACHE
        g.ORG_CACHE = base / 'cache'

    def tearDown(self):
        g.gh_api, g.ORG_CACHE = self.original
        self.temp.cleanup()

    def resolve(self, org_repo=None):
        return g.resolve_settings(types.SimpleNamespace(repo=self.repo / 'sub' if (self.repo / 'sub').exists() else self.repo, org_repo=org_repo))

    def write_repo(self, name, text):
        folder = self.repo / '.fabrica' / '5k-grill-me'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)

    def test_repository_settings_override_the_organization_and_both_guidance_files_apply(self):
        g.gh_api = FakeGitHub({'settings.yaml': 'sessions: org-sessions\n', 'guidance.md': 'Org guidance.\n'})
        self.write_repo('settings.yaml', '# Where interviews are kept\nsessions: "tmp/grill"\n')
        self.write_repo('guidance.md', 'Repo guidance.\n')
        (self.repo / 'sub').mkdir()
        result = self.resolve()
        self.assertEqual(result['repository'], str(self.repo))
        self.assertEqual(result['organization']['status'], 'found')
        self.assertEqual(result['organization']['repo'], 'acme/.fabrica')
        self.assertEqual(result['settings']['sessions'], {'value': 'tmp/grill', 'source': 'repository', 'path': str(self.repo / 'tmp' / 'grill')})
        self.assertEqual([(item['source'], item['text']) for item in result['guidance']],
                         [('organization', 'Org guidance.'), ('repository', 'Repo guidance.')])

    def test_organization_settings_apply_when_the_repository_has_none(self):
        g.gh_api = FakeGitHub({'settings.yaml': 'sessions: org-sessions\n'})
        result = self.resolve()
        self.assertEqual(result['settings']['sessions']['source'], 'organization')
        self.assertEqual(result['guidance'], [])

    def test_offline_uses_the_cached_copy_and_then_says_there_is_none(self):
        g.gh_api = FakeGitHub({'guidance.md': 'Cached guidance.'})
        self.resolve()
        g.gh_api = FakeGitHub(error='connection refused')
        cached = self.resolve()
        self.assertEqual(cached['organization']['status'], 'cached')
        self.assertEqual(cached['guidance'][0]['text'], 'Cached guidance.')
        g.ORG_CACHE = Path(self.temp.name) / 'empty-cache'
        unreachable = self.resolve()
        self.assertEqual(unreachable['organization']['status'], 'unreachable')
        self.assertEqual(unreachable['guidance'], [])

    def test_a_missing_organization_folder_is_not_an_error(self):
        g.gh_api = FakeGitHub()
        self.assertEqual(self.resolve()['organization']['status'], 'missing')

    def test_org_repo_flag_picks_another_repository_or_skips_it(self):
        fake = FakeGitHub()
        g.gh_api = fake
        self.assertEqual(self.resolve(org_repo='')['organization']['status'], 'off')
        self.assertEqual(fake.calls, [])
        self.resolve(org_repo='other/settings')
        self.assertEqual(fake.calls[0], 'repos/other/settings/commits/HEAD')
        with self.assertRaisesRegex(ValueError, 'owner/name'):
            self.resolve(org_repo='not a repo')

    def test_bad_settings_name_the_problem(self):
        g.gh_api = FakeGitHub()
        self.write_repo('settings.yaml', 'theme: dark\n')
        with self.assertRaisesRegex(ValueError, r'settings.yaml:1: unknown setting theme'):
            self.resolve()
        self.write_repo('settings.yaml', 'sessions: ../outside\n')
        with self.assertRaisesRegex(ValueError, 'inside the repository'):
            self.resolve()
        self.write_repo('settings.yaml', 'sessions\n')
        with self.assertRaisesRegex(ValueError, r'settings.yaml:1: expected "key: value"'):
            self.resolve()


unittest.main()
