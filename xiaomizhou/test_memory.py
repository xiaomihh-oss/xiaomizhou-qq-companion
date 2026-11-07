import time
import unittest
from companion import Companion

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.bot=Companion(':memory:')
        self.item={'slot':'运动偏好','value':'喜欢篮球','quote':'我平时喜欢篮球','temporary':False}
    def propose(self,user='a',item=None):
        return self.bot.memory.suggest(user,item or self.item,'我平时喜欢篮球')
    def test_consent_and_isolation(self):
        self.assertIn('/确认记忆',self.propose())
        self.assertEqual(self.bot.memories('a'),[])
        self.assertIn('没有待确认',self.bot.reply('b','/确认记忆'))
        self.bot.reply('a','/确认记忆')
        self.assertEqual(self.bot.memories('a')[0][1],'喜欢篮球')
        self.assertEqual(self.bot.memories('b'),[])
    def test_cancel_and_forget_pending(self):
        self.propose()
        self.bot.reply('a','/取消记忆')
        self.assertIn('没有待确认',self.bot.reply('a','/确认记忆'))
        self.propose()
        self.bot.reply('a','/忘记 运动偏好')
        self.assertIn('没有待确认',self.bot.reply('a','/确认记忆'))
    def test_evidence_and_sensitive_filter(self):
        self.assertEqual(self.propose(item={**self.item,'quote':'不存在的原话'}),'')
        self.assertEqual(self.propose(item={**self.item,'value':'身份证号码'}),'')
    def test_expiry_removes_context(self):
        self.propose(item={**self.item,'temporary':True})
        self.bot.reply('a','/确认记忆')
        self.bot.db.execute('UPDATE memory_meta SET expires=?',(time.time()-1,))
        self.bot.db.execute("INSERT INTO history(user,role,content) VALUES('a','user','旧状态')")
        self.assertEqual(self.bot.memories('a'),[])
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
    def test_retrieval(self):
        self.bot.reply('a','/记住 运动偏好=喜欢篮球')
        self.bot.reply('a','/记住 饮料偏好=喜欢热水')
        self.assertEqual(self.bot.memory.retrieve('a','篮球怎么练')[0][0],'运动偏好')
        self.assertEqual(self.bot.memory.retrieve('b','篮球怎么练'),[])

if __name__=='__main__':
    unittest.main()
