"""Public entry-point checks; no game files or account access required."""
import json,os,re,unittest
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(os.environ.get('DEMENTIUM_PUBLICATION_ROOT',Path(__file__).resolve().parents[1]))
CURRENT=['README.md','BUILDING.md','TECHNICAL.md','TRANSLATING.md','LICENSING.md','docs/README.md','docs/STATUS.md','docs/KNOWN_ISSUES.md','docs/PLAYER_README.md','docs/INSTALLATION_GUIDE.md','docs/BUILD_AND_RELEASE.md','docs/FILEMAP.md','docs/FILE_FORMATS.md','docs/PROGRESS.md']
class PublicationTests(unittest.TestCase):
 def read(self,name):
  path=ROOT/name;self.assertTrue(path.is_file(),name+' missing');return path.read_text('utf-8-sig')
 def test_readme_is_player_facing_and_links_published_installer(self):
  s=self.read('README.md')
  self.assertIn('releases)',s);self.assertIn('Dementium-II-CN-v1.1.exe',s);self.assertIn('26123896',s);self.assertIn('不承诺通用所有版本',s)
  self.assertIn('完整通关',s);self.assertIn('2013',s);self.assertIn('BUILDING.md',s)
  self.assertNotIn('不创建未经授权的正式 Release',s)
 def test_current_status_distinguishes_playthrough_from_automation(self):
  s=self.read('docs/STATUS.md')
  for token in ['2026-10-22','完整通关','322','76','13','6986bf2e92f58917379dfd5fa3bdb84c2ba6e5633d96859065c171f95048e971']:self.assertIn(token,s)
 def test_current_markdown_links_resolve(self):
  for name in CURRENT:
   s=re.sub(r'```.*?```','',self.read(name),flags=re.S)
   for target in re.findall(r'\]\(([^)]+)\)',s):
    target=target.split()[0].strip('<>')
    if not target or target.startswith('#') or urlsplit(target).scheme:continue
    path=(ROOT/name).parent/unquote(target.split('#')[0])
    self.assertTrue(path.exists(),name+' -> '+target)
 def test_generic_unfilled_templates_are_not_public_guides(self):
  for name in ['BUILDING.md','TECHNICAL.md','TRANSLATING.md','LICENSING.md','docs/FILE_FORMATS.md','docs/KNOWN_ISSUES.md','docs/PITFALLS.md']:
   s=self.read(name)
   for token in ['Replace this section','Issue Entry Template','Document the exact supported game build here','This document defines the default']:
    self.assertNotIn(token,s,name)
 def test_release_identity_matches_supported_build_and_policy(self):
  r=json.loads(self.read('assets/releases/v1.0.json'));b=json.loads(self.read('assets/supported-builds/26099941.json'));p={'installer_version':'1.0.0'}
  self.assertEqual(r['supported_appid'],b['appid']);self.assertEqual(r['reference_build'],b['buildid']);self.assertEqual(r['installer_version'],p['installer_version'])
  self.assertRegex(r['sha256'],r'^[0-9a-f]{64}$');self.assertEqual(r['size'],78500889);self.assertEqual(r['player_acceptance']['status'],'full_playthrough_completed')
 def test_player_instructions_use_gui_not_python_install(self):
  s=self.read('docs/PLAYER_README.md');self.assertIn('Dementium-II-CN-v1.1.exe',s);self.assertIn('cn-backup',s);self.assertNotIn('install_patch.py install',s)
 def test_v11_identity_matches_current_policy_and_manual_release(self):
  r=json.loads(self.read('assets/releases/v1.1.json'));b=json.loads(self.read('assets/supported-build.json'));p=json.loads(self.read('assets/release-policy.json'))
  self.assertEqual(r['reference_build'],b['buildid']);self.assertEqual(r['installer_version'],p['installer_version'])
  self.assertEqual(r['supported_builds'],['26099941','26123896'])
  self.assertEqual(r['status'],'prepared_for_manual_release')
  self.assertEqual(r['player_acceptance']['game_launch'],'NEVER')
 def test_history_retains_findings_and_explains_old_paths(self):
  s=self.read('docs/history/FIXED_ISSUES.md');self.assertIn('历史',s);self.assertIn('现场明信片',s)
  s=self.read('docs/history/BUILD_REGRESSIONS.md');self.assertIn('历史',s);self.assertIn('verify_ui_regressions.py',s)
 def test_current_entrypoints_have_no_local_machine_paths(self):
  for name in CURRENT:
   s=self.read(name);self.assertNotRegex(s,r'(?i)[cC]:[\\/]Users[\\/]noway')
 def assert_objective_wording(self,text,name):
  self.assertNotRegex(text,r'维护者|用户|玩家|开发者|我们|本人|(?i:\bmaintainers?\b|\busers?\b)',name)
 def test_project_documentation_uses_objective_wording(self):
  paths=list(ROOT.glob('*.md'))+list((ROOT/'docs').rglob('*.md'))+list((ROOT/'docs').glob('*.txt'))
  self.assertGreater(len(paths),40)
  for path in paths:
   self.assert_objective_wording(path.read_text('utf-8-sig'),str(path.relative_to(ROOT)))
 def test_review_metadata_uses_objective_wording(self):
  def visit(value,path):
   if isinstance(value,dict):
    for key,item in value.items():visit(item,path+'/'+key)
   elif isinstance(value,list):
    for index,item in enumerate(value):visit(item,path+'/'+str(index))
   elif isinstance(value,str):self.assert_objective_wording(value,path)
  visit(json.loads(self.read('assets/releases/v1.0.json')),'v1.0')
  visit(json.loads(self.read('assets/releases/v1.1.json')),'v1.1')
  def reviews(value,path):
   if isinstance(value,dict):
    for key,item in value.items():
     if key in ('review','reason','workflow','prompt'):visit(item,path+'/'+key)
     elif isinstance(item,(dict,list)):reviews(item,path+'/'+key)
   elif isinstance(value,list):
    for index,item in enumerate(value):reviews(item,path+'/'+str(index))
  reviews(json.loads(self.read('locales/zh-CN/image-text.json')),'image-text')
 def test_readme_limits_playthrough_claim_to_historical_version(self):
  s=self.read('README.md')
  self.assertIn('v1.0已有完整通关记录',s)
  self.assertIn('尚无新版完整通关记录',s)
if __name__=='__main__':unittest.main()
