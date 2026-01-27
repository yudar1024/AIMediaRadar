# main.py
import os
import json
import datetime
import logging
import requests
import feedparser # 用于解析 RSS (Twitter/Nitter)
import arxiv      # 用于 Arxiv 论文
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from abc import ABC, abstractmethod

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('AIMediaRadar')

# --- 配置部分 ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")
# 为了避开Twitter昂贵的API，建议使用 Nitter 实例的 RSS，或者 RSSHub 生成的源
# 例如: https://nitter.net/OpenAI/rss
TWITTER_RSS_URLS = os.getenv("TWITTER_RSS_URLS", "").split(",") 

# --- 1. LLM 服务 (接入 DeepSeek) ---
class DeepSeekAnalyst:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise ValueError("缺少 DEEPSEEK_API_KEY")
        # DeepSeek 兼容 OpenAI SDK
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    def analyze(self, raw_data_text):
        print("🤖 DeepSeek 正在思考...")
        prompt = f"""
        你是一个敏锐的科技商业情报专家。请分析以下今日采集的AI领域原始数据（包含GitHub项目、ArXiv论文、Twitter动态）。
        
        任务：
        1. 过滤掉无意义的噪音。
        2. 总结出 3-5 个最重要的技术或商业趋势。
        3. 每一个趋势请按格式输出：【标题】+ 简短评价 + 商业价值评分(1-5星)。
        
        原始数据：
        {raw_data_text[:15000]} 
        """
        # 注意：DeepSeek V3 上下文很长，但为了节省 tokens，我们做适当截断
        response = self.client.chat.completions.create(
            model="deepseek-chat", # 或者 deepseek-reasoner
            messages=[{"role": "user", "content": prompt}],
            temperature=1.3 
        )
        return response.choices[0].message.content

# --- 2. 数据采集器 (增加 Twitter & Arxiv) ---
class BaseCollector(ABC):
    @abstractmethod
    def fetch(self): pass

class GitHubCollector(BaseCollector):
    def fetch(self):
        logger.info("📥 开始抓取 GitHub...")
        two_days_ago = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{two_days_ago}+language:python&sort=stars&order=desc"
        try:
            res = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"}).json()
            items = res.get('items', [])[:20]
            results = [f"[GitHub] {item['name']}: {item['description']} (Stars: {item['stargazers_count']})" for item in items]
            logger.info(f"✅ GitHub 采集完成，共获取 {len(results)} 条数据")
            for i, item in enumerate(items[:5], 1):
                logger.debug(f"  [{i}] {item['name']} - Stars: {item['stargazers_count']}")
            return results
        except Exception as e:
            logger.error(f"❌ GitHub 采集失败: {e}")
            return []

class ArxivCollector(BaseCollector):
    def fetch(self):
        logger.info("📥 开始抓取 ArXiv (CS.CL/CS.AI)...")
        # 搜索最近提交的 AI/CL 论文
        client = arxiv.Client()
        search = arxiv.Search(
            query = "cat:cs.CL OR cat:cs.AI",
            max_results = 10,
            sort_by = arxiv.SortCriterion.SubmittedDate
        )
        results = []
        for r in client.results(search):
            results.append(f"[ArXiv] {r.title} - {r.summary[:100]}...")
            logger.debug(f"  论文: {r.title}")
        logger.info(f"✅ ArXiv 采集完成，共获取 {len(results)} 篇论文")
        return results

class TwitterRSSCollector(BaseCollector):
    def fetch(self):
        logger.info("📥 开始抓取 Twitter/RSS...")
        results = []
        for url in TWITTER_RSS_URLS:
            if not url: continue
            try:
                logger.debug(f"  正在解析 RSS: {url}")
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]: # 每个源取前3条
                    results.append(f"[Twitter] {entry.title}: {entry.link}")
                    logger.debug(f"  推文: {entry.title}")
            except Exception as e:
                logger.error(f"❌ RSS 解析失败 {url}: {e}")
        logger.info(f"✅ Twitter/RSS 采集完成，共获取 {len(results)} 条动态")
        return results

# --- 3. 向量数据库 (ChromaDB) ---
class MemoryStore:
    def __init__(self):
        # 持久化到本地 ./chroma_db 目录
        self.client = chromadb.PersistentClient(path="./chroma_db")
        # 使用开源免费的 embedding 模型，不需要调用 OpenAI
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self.collection = self.client.get_or_create_collection(name="ai_intelligence", embedding_function=self.ef)

    def save(self, documents, metadatas):
        ids = [f"id_{datetime.datetime.now().timestamp()}_{i}" for i in range(len(documents))]
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"💾 已存入 {len(documents)} 条数据到向量库")

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

# --- 主流程 ---
def main():
    logger.info("=" * 50)
    logger.info("🚀 AI 情报雷达开始运行")
    logger.info("=" * 50)
    
    # 1. 采集
    collectors = [GitHubCollector(), ArxivCollector(), TwitterRSSCollector()]
    # collectors = [GitHubCollector(), ArxivCollector()]
    raw_data = []
    for c in collectors:
        raw_data.extend(c.fetch())
    
    logger.info(f"📊 采集汇总: 共获取 {len(raw_data)} 条原始数据")
    
    if not raw_data:
        logger.warning("❌ 未采集到任何数据，程序退出")
        return

    full_text = "\n".join(raw_data)

    # 2. 存储到 ChromaDB (用于未来 RAG 检索)
    # 将每条原始数据单独存入，方便未来精确检索
    try:
        logger.info("💾 正在存储数据到向量数据库...")
        db = MemoryStore()
        metadatas = [{"source": "monitor", "date": str(datetime.date.today())} for _ in raw_data]
        db.save(documents=raw_data, metadatas=metadatas)
        logger.info("✅ 向量数据库存储完成")
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB 存储警告: {e}")

    # 3. DeepSeek 分析
    logger.info("🤖 开始 DeepSeek 分析...")
    analyst = DeepSeekAnalyst()
    report = analyst.analyze(full_text)
    logger.info("✅ DeepSeek 分析完成")
    logger.info(f"📝 分析报告:\n{report}")
    
    # 4. 推送
    # notifier = Notifier()
    # notifier.send(report)
    
    logger.info("=" * 50)
    logger.info("🎉 AI 情报雷达运行结束")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()