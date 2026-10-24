"""Terminology and patch-version regression checks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class TerminologyTests(unittest.TestCase):
 def test_item_names_match_in_narrative_menu_and_glossary(self):
  narrative=json.loads((ROOT/'locales/zh-CN/narrative.map.json').read_text('utf8'))
  labels=json.loads((ROOT/'locales/zh-CN/debug-menu.json').read_text('utf8'))['labels']
  text=''.join(row['target'] for row in narrative.values())
  glossary=(ROOT/'GLOSSARY.md').read_text('utf8')
  for source,target in [('Skeleton Key','骷髅钥匙'),('Fumigator','驱虫烟雾器')]:
   self.assertEqual(labels[source],target)
   self.assertIn(target,text)
   self.assertIn(f'| {source} | {target} |',glossary)
  for stale in ['万能钥匙','熏蒸器']:self.assertNotIn(stale,text+''.join(labels.values()))
 def test_version_is_112_in_metadata_and_visible_ui(self):
  policy=json.loads((ROOT/'assets/release-policy.json').read_text('utf8'))
  self.assertEqual(policy['installer_version'],'1.1.2')
  release=json.loads((ROOT/'assets/releases/v1.1.2.json').read_text('utf8'))
  self.assertEqual(release['installer_version'],policy['installer_version'])
  self.assertIn('26152271',release['supported_builds'])
  for name in ['installer/MaterialWindow.xaml','installer/MaterialWindow.xaml.cs']:
   self.assertIn('v1.1.2',(ROOT/name).read_text('utf8'))
 def test_compatibility_rebuild_rejects_unknown_source_without_output(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'source.exe';source.write_bytes(b'MZ INVALID FIXTURE')
   output=Path(temp)/'out/resource-patches.gz'
   done=subprocess.run([sys.executable,str(ROOT/'tools/build_compatibility.py'),'--executable',str(source),'--build-id','26099941','--output',str(output)],capture_output=True,text=True)
   self.assertNotEqual(done.returncode,0)
   self.assertIn('identity mismatch',done.stderr)
   self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
