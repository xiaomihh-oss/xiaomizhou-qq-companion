import unittest
import os
import urllib.error
from unittest.mock import patch
from companion import Companion

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.bot=Companion(':memory:')
    def test_update_and_isolation(self):
        self.bot.reply('a','/记住 饮料=咖啡')
        self.bot.reply('a','/记住 饮料=热水')
        self.assertEqual(len(self.bot.memories('a')),1)
        self.assertEqual(self.bot.memories('a')[0][1],'热水')
        self.assertEqual(self.bot.memories('b'),[])
    def test_forget_clears_history(self):
        self.bot.reply('a','/记住 称呼=小林')
        self.bot.db.execute("INSERT INTO history(user,role,content) VALUES('a','user','小林')")
        self.bot.reply('a','/忘记 称呼')
        self.assertEqual(self.bot.memories('a'),[])
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
    def test_growth_is_idempotent(self):
        for _ in range(3):
            self.bot.reply('a','/完成 读书')
        self.assertIn('1 件',self.bot.growth('a'))
        for name in ('散步','练字'):
            self.bot.reply('a','/完成 '+name)
        self.assertIn('探头的新芽',self.bot.growth('a'))

    def test_new_chat_preserves_memory_and_growth(self):
        self.bot.reply('a','/记住 运动=篮球')
        self.bot.reply('a','/完成 打篮球')
        self.bot.db.execute("INSERT INTO history(user,role,content) VALUES('a','user','你好')")
        self.bot.reply('a','/新对话')
        self.assertEqual(len(self.bot.memories('a')),1)
        self.assertIn('1 件',self.bot.growth('a'))
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
    def test_clear_isolated(self):
        for user in ('a','b'):
            self.bot.reply(user,'/记住 称呼=朋友')
        self.bot.reply('a','/清空')
        self.assertEqual(self.bot.memories('a'),[])
        self.assertEqual(len(self.bot.memories('b')),1)

    def test_http_error_is_actionable_without_secrets(self):
        with patch.dict(os.environ, {'MODEL_ENDPOINT':'https://example.com/chat/completions','MODEL_NAME':'test','MODEL_API_KEY':'private-test-key'}):
            for code in (400,401,402,404,429):
                error=urllib.error.HTTPError('https://example.com',code,'private-test-key',{},None)
                with patch('urllib.request.urlopen',side_effect=error):
                    result=self.bot.reply('a','你好')
                self.assertIn(str(code),result)
                self.assertNotIn('private-test-key',result)
        self.assertEqual(self.bot.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)

if __name__=='__main__':
    unittest.main()

class DeleteNameTests(unittest.TestCase):
    def test_missing_name_is_not_success(self):
        bot=Companion(':memory:')
        bot.reply('a','/记住 最喜欢运动=游泳')
        self.assertIn('没有找到',bot.reply('a','/忘记 喜欢的运动'))
        self.assertEqual(len(bot.memories('a')),1)
        self.assertIn('已删除',bot.reply('a','/忘记 最喜欢运动'))
        self.assertEqual(bot.memories('a'),[])
