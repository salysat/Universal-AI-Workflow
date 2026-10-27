import unittest,tempfile,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import uw_internal_team as team
import uw_file_edit as files
class TestTeam(unittest.TestCase):
 def test_lifecycle(self):
  with tempfile.TemporaryDirectory() as d:
   team.create(d,'T1','Build feature',[])
   self.assertEqual(team.prompt(d,'T1')['role'],'architect')
   for role in team.ROLES:
    team.record(d,'T1',role,'reported','proof',approved=role=='reviewer')
   self.assertEqual(team.load(d)['tasks']['T1']['status'],'completed')
 def test_reject_and_resume(self):
  with tempfile.TemporaryDirectory() as d:
   team.create(d,'T1','Build',[])
   for role in team.ROLES:team.record(d,'T1',role,'report','proof')
   self.assertEqual(team.prompt(d,'T1')['role'],'developer')
 def test_order(self):
  with tempfile.TemporaryDirectory() as d:
   team.create(d,'T1','Build',[])
   with self.assertRaises(ValueError):team.record(d,'T1','tester','test','evidence')
 def test_escape(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):team.create(d,'T1','x',['../../etc/passwd'])
 def test_file_replace_preview(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.txt';p.write_text('hello world')
   target,h,result=files.edit(d,'x.txt','replace',old='world',new='earth')
   self.assertEqual(result,'hello earth');self.assertEqual(p.read_text(),'hello world')
   with self.assertRaises(ValueError):files.edit(d,'x.txt','replace',old='oops',new='earth')
 def test_json(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_text('{"a":1}')
   _,_,result=files.edit(d,'x.json','json-set',key='a',value='2')
   self.assertEqual(json.loads(result)['a'],2)
 def test_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.txt';p.write_text('abc')
   with self.assertRaises(ValueError):files.edit(d,'x.txt','replace',old='abc',new='xyz',expected_hash='0'*64)
if __name__=='__main__':unittest.main()
