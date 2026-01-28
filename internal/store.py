import chromadb

# --- 向量数据库 (ChromaDB) ---
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