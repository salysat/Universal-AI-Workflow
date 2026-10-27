import unittest,sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ai_discovery,auto_plan,v5_auto
class V5Tests(unittest.TestCase):
 def test_draft(self):
  d=auto_plan.draft('project5','إنشاء تطبيق لإدارة مكاتب المحاماة');self.assertEqual(len(d['tasks']),4)
  self.assertEqual(d['tasks'][3]['depends_on'],['03_tester'])
 def test_description_invalid(self):
  with self.assertRaises(ValueError):auto_plan.draft('x','short')
 def test_cycle(self):
  with self.assertRaises(ValueError):v5_auto.schedule([{'id':'a','depends_on':['b']},{'id':'b','depends_on':['a']}])
 def test_parallel(self):
  waves=v5_auto.schedule([{'id':'a'},{'id':'b'},{'id':'c','depends_on':['a','b']}],2)
  self.assertEqual(waves,[['a','b'],['c']])
 def test_role_reuse(self):
  conf={'agents':{'one':{}},'roles':{'reviewer':'one','developer':'one'}}
  self.assertEqual(v5_auto.config_for_role(conf,'reviewer','one'),'one')
 def test_detection(self):
  self.assertIsInstance(ai_discovery.discover(),dict)
if __name__=='__main__':unittest.main()
