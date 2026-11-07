"""官方 QQ SDK 接入。依赖安装与凭据见 README。"""
import asyncio
import os
from companion import Companion

async def run_connection(api, ws, wait=None):
    import httpx
    # SDK不会创建异步HTTP客户端，必须显式setup，并维持到WS停止。
    async with httpx.AsyncClient(timeout=45) as http:
        api.setup(http)
        try:
            await api.ensure_token()
            gateway=await api.get_gateway_url()
            ws.start(gateway,asyncio.get_running_loop())
            print('小米粥已启动，正在连接QQ；请等待“QQ连接已建立”。')
            await (wait if wait is not None else asyncio.Event().wait())
        finally:
            ws.stop()

def make_callbacks(api, on_message, report=print):
    """SDK要求宿主提供会话状态；只在进程内保留，不落盘凭据。"""
    from qqbot_agent_sdk import WSCallbacks
    import threading
    state={'session':(None,None),'heartbeat':None}
    guard=threading.Lock()
    def get_session():
        with guard:
            return state['session']
    def set_session(session_id,seq):
        with guard:
            state['session']=(session_id,seq)
    def set_heartbeat(interval):
        with guard:
            state['heartbeat']=interval
    def fatal(code,message):
        # 不输出平台原始消息，防止其中夹带敏感配置。
        report('QQ连接遇到不可恢复错误，请检查机器人权限、凭据和平台设置。')
    return WSCallbacks(
        on_message_event=on_message,
        on_connected=lambda: report('QQ连接已建立，可以发送单聊消息了。'),
        on_disconnected=lambda: report('QQ连接已断开，SDK将按策略尝试重连。'),
        on_fatal_error=fatal,
        get_token=api.ensure_token_sync,
        get_session=get_session,
        set_session=set_session,
        set_heartbeat_interval=set_heartbeat,
        clear_token=api.clear_token,
        # 本程序没有待处理响应future，故只报告状态。
        fail_pending=lambda reason: report('QQ连接状态变化，未发送消息不会自动补发。'),
        get_gateway_url=api.get_gateway_url_sync,
    )

async def main():
    from qqbot_agent_sdk import QQApiClient, QQWebSocket, WSCallbacks, EventParser
    app_id=os.environ['QQ_APP_ID']
    secret=os.environ['QQ_APP_SECRET']
    api=QQApiClient(app_id=app_id,client_secret=secret)
    bot=Companion()
    lock=asyncio.Lock()
    seen=set()

    async def on_message(event_type,raw):
        # 第一版只处理单聊，避免群里共享个人记忆。
        if event_type != 'C2C_MESSAGE_CREATE':
            return
        event=EventParser().parse(event_type,raw)
        if not event or not event.content:
            return
        async with lock:
            if event.message_id in seen:
                return
            if len(seen)>5000:
                seen.clear()
            seen.add(event.message_id)
            reply=await asyncio.to_thread(bot.reply,'qq:'+str(event.chat_id),event.content)
            try:
                await api.send_text(event.chat_scope,event.chat_id,reply[:1800],reply_to=event.message_id)
            except Exception:
                print('QQ回复发送失败，请检查平台权限或连接；不输出消息或凭据。')

    ws=QQWebSocket(callbacks=make_callbacks(api,on_message))
    await run_connection(api,ws)

if __name__=='__main__':
    asyncio.run(main())
