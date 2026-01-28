import os

# --- 配置部分 ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")

# 为了避开Twitter昂贵的API，建议使用 Nitter 实例的 RSS，或者 RSSHub 生成的源
# 例如: https://nitter.net/OpenAI/rss
TWITTER_RSS_URLS = os.getenv("TWITTER_RSS_URLS", "").split(",") 