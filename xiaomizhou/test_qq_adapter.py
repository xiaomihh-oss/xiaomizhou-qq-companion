import unittest
from unittest.mock import Mock
from qq_bot import make_callbacks
from qq_bot import run_connection
from unittest.mock import AsyncMock

class CallbackTests(unittest.TestCase):
    def test_sdk_contract_and_session(self):
        api=Mock()
        async def receive(event,raw):
            pass
        cb=make_callbacks(api,receive,report=Mock())
        self.assertEqual(cb.get_session(),(None,None))
        cb.set_session('session',42)
        self.assertEqual(cb.get_session(),('session',42))
        cb.set_heartbeat_interval(30)
        cb.clear_token()
        api.clear_token.assert_called_once()
        cb.on_connected()
        cb.on_disconnected()
        cb.on_fatal_error('error','secret')
        cb.fail_pending('disconnect')
        from qqbot_agent_sdk import QQWebSocket
        ws=QQWebSocket(callbacks=cb)
        self.assertIsNotNone(ws)

class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_http_initialized_before_gateway(self):
        from qqbot_agent_sdk import QQApiClient
        import httpx
        api=QQApiClient(app_id='test',client_secret='test')
        api.ensure_token=AsyncMock(return_value='test-token')
        original_request=api.request
        async def gateway():
            # 走真实SDK.request，只有HTTP传输使用mock，检查setup缺失回归。
            async def transport(request):
                return httpx.Response(200,json={'url':'wss://example.com'})
            self.assertIsNotNone(api._http_client)
            api._http_client._transport=httpx.MockTransport(transport)
            # 避免环境代理改变测试路由。
            api._http_client._mounts={}
            return (await original_request('GET','/gateway'))['url']
        api.get_gateway_url=gateway
        ws=Mock()
        async def finish():
            pass
        await run_connection(api,ws,finish())
        ws.start.assert_called_once()
        self.assertEqual(ws.start.call_args.args[0],'wss://example.com')
        ws.stop.assert_called_once()
        self.assertTrue(api._http_client.is_closed)

if __name__=='__main__':
    unittest.main()
