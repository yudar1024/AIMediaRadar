from abc import ABC, abstractmethod
import logging
import requests
import feedparser
import arxiv
from datetime import datetime, timedelta
from internal.config import TWITTER_RSS_URLS

logger = logging.getLogger("collectors")

# --- 2. 数据采集器 (增加 Twitter & Arxiv) ---
class BaseCollector(ABC):
    @abstractmethod
    def fetch(self): pass

class GitHubCollector(BaseCollector):
    def fetch(self):
        logger.info("📥 开始抓取 GitHub...")
        two_days_ago = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
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
