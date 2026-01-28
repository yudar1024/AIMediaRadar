import requests
import logging
from internal.config import FEISHU_WEBHOOK, DINGTALK_WEBHOOK

logger = logging.getLogger("notifier")

# --- 4. 通知模块 (Feishu & DingTalk) ---
class Notifier:
    def send(self, content):
        title = f"🚀 AI 情报日报 ({datetime.date.today()})"
        logger.info(f"📤 开始发送通知，标题: {title}")
        logger.debug(f"通知内容预览: {content[:200]}..." if len(content) > 200 else f"通知内容: {content}")
        
        # 飞书推送
        if FEISHU_WEBHOOK:
            data = {"msg_type": "text", "content": {"text": f"{title}\n\n{content}"}}
            logger.info(f"📨 正在发送飞书通知到: {FEISHU_WEBHOOK[:50]}...")
            try:
                response = requests.post(FEISHU_WEBHOOK, json=data)
                logger.info(f"✅ 飞书推送成功，状态码: {response.status_code}")
                logger.debug(f"飞书响应: {response.text}")
            except Exception as e:
                logger.error(f"❌ 飞书推送失败: {e}")
            
        # 钉钉推送
        if DINGTALK_WEBHOOK:
            data = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"# {title}\n\n{content}"}
            }
            logger.info(f"📨 正在发送钉钉通知到: {DINGTALK_WEBHOOK[:50]}...")
            try:
                response = requests.post(DINGTALK_WEBHOOK, json=data)
                logger.info(f"✅ 钉钉推送成功，状态码: {response.status_code}")
                logger.debug(f"钉钉响应: {response.text}")
            except Exception as e:
                logger.error(f"❌ 钉钉推送失败: {e}")
        
        if not FEISHU_WEBHOOK and not DINGTALK_WEBHOOK:
            logger.warning("⚠️ 未配置任何通知 Webhook，跳过推送")