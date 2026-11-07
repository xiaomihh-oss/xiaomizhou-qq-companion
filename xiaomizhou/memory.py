"""显式确认的记忆建议、时效与轻量中文检索。"""
import json
import time
import re

OUTPUT_RULES = '''只返回JSON对象，不使用代码围栏：{"reply":"自然语言回复", "memory":null}。
如果当前用户消息明确表达本人稳定偏好、称呼、目标或临时安排，可把memory改为
{"slot":"简短名称","value":"内容","quote":"当前用户消息的逐字连续引用","temporary":false}。
每轮最多一个建议；临时计划temporary为true，最多保留7天。不要记录健康、政治、身份号码、住址、密钥等敏感信息；不要从问题、假设、第三方经历或角色扮演提取事实。不要重复提出已存在且相同的记忆。reply不要声称已经保存，也不要自行询问保存，程序会处理确认。'''

class Memory:
    def __init__(self, db):
        self.db=db
        db.executescript('''CREATE TABLE IF NOT EXISTS memory_meta(user TEXT,slot TEXT,expires REAL,PRIMARY KEY(user,slot));
        CREATE TABLE IF NOT EXISTS pending_memory(user TEXT PRIMARY KEY,payload TEXT,created REAL);''')

    def expire(self,user):
        slots=self.db.execute('SELECT slot FROM memory_meta WHERE user=? AND expires IS NOT NULL AND expires<=?',(user,time.time())).fetchall()
        for (slot,) in slots:
            self.db.execute('DELETE FROM memories WHERE user=? AND slot=?',(user,slot))
            self.db.execute('DELETE FROM memory_meta WHERE user=? AND slot=?',(user,slot))
        if slots:
            self.db.execute('DELETE FROM history WHERE user=?',(user,))
        self.db.execute('DELETE FROM pending_memory WHERE created<?',(time.time()-1800,))
        self.db.commit()

    def clear_pending(self,user):
        self.db.execute('DELETE FROM pending_memory WHERE user=?',(user,))
        self.db.commit()

    def suggest(self,user,item,source):
        if not isinstance(item,dict):
            return ''
        slot,value,quote=(item.get(k) for k in ('slot','value','quote'))
        if not all(isinstance(x,str) and x.strip() for x in (slot,value,quote)):
            return ''
        if len(slot)>40 or len(value)>300 or len(quote)<4 or quote not in source or type(item.get('temporary')) is not bool:
            return ''
        if re.search(r'密钥|密码|身份证|住址|投票|政党|病|膝盖|药|受伤|api.?key|sk-',slot+value+quote,re.I):
            return ''
        old=self.db.execute('SELECT value FROM memories WHERE user=? AND slot=?',(user,slot)).fetchone()
        if old and old[0]==value:
            return ''
        item={k:item[k] for k in ('slot','value','quote','temporary')}
        self.db.execute('INSERT OR REPLACE INTO pending_memory VALUES(?,?,?)',(user,json.dumps(item,ensure_ascii=False),time.time()))
        self.db.commit()
        duration='临时记忆，确认后7天到期' if item['temporary'] else '长期记忆'
        change=f'（将替换：{old[0]}）' if old else ''
        return f'\n\n要记住「{slot}：{value}」吗？{change}\n{duration}；依据：“{quote}”\n发送 /确认记忆 或 /取消记忆。'

    def confirm(self,user):
        self.expire(user)
        row=self.db.execute('SELECT payload FROM pending_memory WHERE user=?',(user,)).fetchone()
        if not row:
            return '目前没有待确认的记忆，建议会在30分钟后失效。'
        item=json.loads(row[0])
        self.db.execute('INSERT OR REPLACE INTO memories VALUES(?,?,?,?)',(user,item['slot'],item['value'],item['quote']))
        self.db.execute('INSERT OR REPLACE INTO memory_meta VALUES(?,?,?)',(user,item['slot'],time.time()+7*86400 if item['temporary'] else None))
        self.db.execute('DELETE FROM pending_memory WHERE user=?',(user,))
        self.db.execute('DELETE FROM history WHERE user=?',(user,))
        self.db.commit()
        return '已保存：'+item['slot']+' = '+item['value']+'。可用 /记忆 查看，或 /忘记 '+item['slot']+' 删除。'

    def retrieve(self,user,query):
        self.expire(user)
        rows=self.db.execute('SELECT slot,value,source FROM memories WHERE user=?',(user,)).fetchall()
        def grams(text):
            text=re.sub(r'\s+','',text.lower())
            return {text[i:i+2] for i in range(len(text)-1)}
        q=grams(query)
        broad=any(x in query for x in ('你记得','我的爱好','我喜欢什么','介绍我','周末','建议','安排'))
        scored=[]
        for row in rows:
            score=len(q & grams(row[0]+row[1]))
            if score or broad or row[0] in ('称呼','名字'):
                scored.append((score,row))
        return [row for _,row in sorted(scored,key=lambda x:(-x[0],x[1][0]))[:8]]
