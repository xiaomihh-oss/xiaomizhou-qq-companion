import io
import json
import os
import unittest
from unittest.mock import patch
from companion import Companion,parse_reply

class ReplyTests(unittest.TestCase):
    def test_plain_and_json(self):
        self.assertEqual(parse_reply('你好，我是小米粥。'),('你好，我是小米粥。',None))
        self.assertEqual(parse_reply('```json\n{"reply":"你好","memory":null}\n```'),('你好',None))
    def test_broken_structure_not_shown(self):
        for text in ('{"reply":"你', '', '{"memory":null}', '[]'):
            with self.assertRaises(ValueError):
                parse_reply(text)
    def test_full_plain_response(self):
        bot=Companion(':memory:')
        payload={'choices':[{'message':{'content':'你好，我是小米粥。'},'finish_reason':'stop'}]}
        with patch.dict(os.environ,{'MODEL_ENDPOINT':'https://example.com/chat/completions','MODEL_API_KEY':'test','MODEL_NAME':'test'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())):
            self.assertEqual(bot.reply('qq:test','你好'),'你好，我是小米粥。')
        self.assertEqual(bot.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],2)
        self.assertEqual(bot.memories('qq:test'),[])
