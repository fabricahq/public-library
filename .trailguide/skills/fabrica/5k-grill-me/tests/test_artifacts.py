import importlib.util,tempfile,types,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('grill',Path(__file__).resolve().parents[1] / 'scripts' / 'grill_ui.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class Artifacts(unittest.TestCase):
 def test_live_file_is_source_and_missing_does_not_return_stale_copy(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve(); session=root/'session'; doc=root/'CONTEXT.md'; doc.write_text('# First\n')
   args=types.SimpleNamespace(file=doc,title='Glossary',session_dir=session)
   g.register_artifact(args);g.register_artifact(args)
   self.assertEqual(len(g.read(session/'artifacts.json')),1)
   self.assertNotIn('content',g.read(session/'artifacts.json')[0])
   first=g.artifacts(session)[0];self.assertEqual(first['content'],'# First\n')
   doc.write_text('# Changed\n');second=g.artifacts(session)[0]
   self.assertEqual(second['content'],'# Changed\n');self.assertNotEqual(first['version'],second['version'])
   doc.unlink();missing=g.artifacts(session)[0];self.assertIn('error',missing);self.assertNotIn('content',missing)
 def test_replacement_symlink_and_oversize_are_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();doc=root/'CONTEXT.md';other=root/'other.md';doc.write_text('safe');other.write_text('not registered')
   g.register_artifact(types.SimpleNamespace(file=doc,title=None,session_dir=root/'session'))
   doc.unlink();doc.symlink_to(other)
   self.assertIn('error',g.artifacts(root/'session')[0])
   doc.unlink();doc.write_bytes(b'a'*262145)
   self.assertIn('error',g.artifacts(root/'session')[0])
 def test_html_remains_literal_source(self):
  with tempfile.TemporaryDirectory() as d:
   doc=Path(d).resolve()/'CONTEXT.md';doc.write_text('<script>alert(1)</script>')
   self.assertEqual(g.artifact_file(doc)['content'],'<script>alert(1)</script>')
unittest.main()
