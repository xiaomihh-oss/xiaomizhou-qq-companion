"""交互式配置，仅保存在当前进程内，兼容 Windows PowerShell。"""
import getpass
import os
import runpy
from pathlib import Path
from urllib.parse import urlparse

def main():
    print('小米粥配置向导：密钥输入时不会显示，不保存到文件。')
    mode = input('启动方式：1 本地聊天 / 2 QQ机器人 [1]：').strip() or '1'
    if mode not in ('1', '2'):
        raise SystemExit('请输入 1 或 2。')
    endpoint = input('模型完整API地址（回车跳过模型配置）：').strip()
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme != 'https' or not parsed.hostname or '你的' in endpoint:
            raise SystemExit('请填写服务商提供的真实 HTTPS 地址，不要使用示例占位符。')
        model = input('真实模型ID：').strip()
        key = getpass.getpass('模型API Key（隐藏输入）：').strip()
        if not model or '你的' in model or not key:
            raise SystemExit('模型ID和密钥不能为空，模型ID不能是占位符。')
        os.environ.update(MODEL_ENDPOINT=endpoint, MODEL_NAME=model, MODEL_API_KEY=key)
    else:
        for name in ('MODEL_ENDPOINT', 'MODEL_NAME', 'MODEL_API_KEY'):
            os.environ.pop(name, None)
        print('本次仅体验记忆和成长指令，普通聊天不可用。')
    if mode == '2':
        app_id = input('QQ机器人AppID：').strip()
        secret = getpass.getpass('QQ机器人AppSecret（隐藏输入）：').strip()
        if not app_id or not secret:
            raise SystemExit('QQ机器人凭据不能为空。')
        os.environ.update(QQ_APP_ID=app_id, QQ_APP_SECRET=secret)
    runpy.run_path(str(Path(__file__).with_name('qq_bot.py' if mode == '2' else 'companion.py')), run_name='__main__')

if __name__ == '__main__':
    main()
