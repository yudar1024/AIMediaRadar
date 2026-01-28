# main.py
import logging
from openai import OpenAI
from internal.collectors import GitHubCollector, ArxivCollector, TwitterRSSCollector
from internal.config import DEEPSEEK_API_KEY, FEISHU_WEBHOOK, DINGTALK_WEBHOOK, TWITTER_RSS_URLS
from internal.store import MemoryStore
from internal.notifiers import Notifier

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('AIMediaRadar')




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