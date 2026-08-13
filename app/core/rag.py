"""
知识库 RAG 检索
================
支持两种检索模式，自动选择：

    1. 向量语义检索（默认，需 API Key）
       用嵌入模型（text-embedding-v3）把 FAQ 和用户查询都转向量，
       做余弦相似度检索。语义匹配，"钱什么时候退给我"也能命中"退款到账"。
    2. TF-IDF 关键词检索（兜底，无 Key 时自动降级）
       字符二元组 TF-IDF + 关键词命中，零依赖。

两种模式下都会把「关键词命中数」作为辅助信号叠加到分数上，
让精确词匹配的条目更靠前。启动时批量计算所有 FAQ 向量并缓存，
查询时只算一次查询向量。
"""
import json
import math
import os
from collections import Counter

from app.core import llm

_FAQ_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faq.json")


def _char_bigrams(text: str) -> list[str]:
    """中文友好的字符二元组（也保留单字）。"""
    text = text.replace(" ", "").replace("？", "?").replace("，", ",")
    if len(text) < 2:
        return [text] if text else []
    return [text[i : i + 2] for i in range(len(text) - 1)] + [text[-1]]


def _cosine(vec_a: list[float], vec_b: list[float], norm_b: float) -> float:
    """余弦相似度（vec_b 的范数已预计算）。"""
    norm_a = math.sqrt(sum(x * x for x in vec_a)) or 1.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    return dot / (norm_a * norm_b)


class KnowledgeBase:
    """FAQ 知识库：加载文档、构建索引、检索相关条目。"""

    def __init__(self):
        self.docs: list[dict] = []
        # TF-IDF 索引（兜底用）
        self.idf: dict[str, float] = {}
        self.doc_vectors: list[dict[str, float]] = []
        # 向量索引
        self.use_vectors: bool = False
        self.doc_embeddings: list[list[float]] = []
        self.doc_norms: list[float] = []

        self._load()
        self._build_tfidf_index()
        self._build_vector_index()

    # ---------- 加载 ----------
    def _load(self) -> None:
        with open(_FAQ_PATH, "r", encoding="utf-8") as f:
            self.docs = json.load(f)

    # ---------- TF-IDF 索引 ----------
    def _build_tfidf_index(self) -> None:
        N = len(self.docs)
        df: Counter = Counter()
        tokenized: list[list[str]] = []
        for doc in self.docs:
            tokens = _char_bigrams(doc["question"] + doc["answer"])
            tokenized.append(tokens)
            for t in set(tokens):
                df[t] += 1
        self.idf = {t: math.log((N + 1) / (cnt + 1)) + 1 for t, cnt in df.items()}
        self.doc_vectors = []
        for tokens in tokenized:
            tf = Counter(tokens)
            total = len(tokens) or 1
            self.doc_vectors.append({t: (c / total) * self.idf.get(t, 1.0) for t, c in tf.items()})

    def _tfidf_query_vec(self, text: str) -> dict[str, float]:
        tokens = _char_bigrams(text)
        tf = Counter(tokens)
        total = len(tokens) or 1
        return {t: (c / total) * self.idf.get(t, 1.0) for t, c in tf.items()}

    # ---------- 向量索引 ----------
    def _build_vector_index(self) -> None:
        """启动时批量把所有 FAQ 转向量并缓存。失败则降级为 TF-IDF。"""
        texts = [f"{d['question']} {d['answer']} {' '.join(d.get('keywords', []))}" for d in self.docs]
        embs = llm.embed_texts(texts)
        if embs and len(embs) == len(self.docs):
            self.doc_embeddings = embs
            self.doc_norms = [math.sqrt(sum(x * x for x in e)) or 1.0 for e in embs]
            self.use_vectors = True
            print(f"[RAG] 向量检索已启用（{len(embs)} 条 FAQ 已向量化）", flush=True)
        else:
            self.use_vectors = False
            print("[RAG] 嵌入调用失败或无 Key，降级为 TF-IDF 关键词检索", flush=True)

    def _embed_query(self, text: str) -> list[float] | None:
        embs = llm.embed_texts([text])
        if embs and len(embs) == 1:
            return embs[0]
        return None

    # ---------- 检索 ----------
    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """检索与 query 最相关的 top_k 条 FAQ。"""
        kw_scores = [sum(1 for kw in d.get("keywords", []) if kw in query) for d in self.docs]
        # 向量模式下尝试查询向量；拿不到则本轮降级 TF-IDF
        qv = self._embed_query(query) if self.use_vectors else None
        use_vec = self.use_vectors and qv is not None

        scores: list[tuple[float, int]] = []
        for i, _doc in enumerate(self.docs):
            kw = kw_scores[i]
            if use_vec:
                sim = _cosine(qv, self.doc_embeddings[i], self.doc_norms[i])
                final = sim + kw * 0.1  # 向量为主，关键词小幅加权
            else:
                tfv = self._tfidf_query_vec(query)
                dv = self.doc_vectors[i]
                tfidf = sum(w * dv.get(k, 0.0) for k, w in tfv.items())
                final = kw + tfidf  # 关键词为主，TF-IDF 辅助
            scores.append((final, i))

        scores.sort(reverse=True)
        results = []
        for score, i in scores[:top_k]:
            if score <= 0:
                break
            doc = self.docs[i]
            results.append(
                {
                    "score": round(score, 4),
                    "question": doc["question"],
                    "answer": doc["answer"],
                }
            )
        return results

    @property
    def mode(self) -> str:
        return "vector" if self.use_vectors else "tfidf"


# 模块级单例：首次导入时构建索引（向量模式下会调用一次嵌入 API）
kb = KnowledgeBase()


def build_rag_context(query: str, top_k: int = 3) -> tuple[str, list[dict]]:
    """检索知识库并拼成给大模型的背景上下文。

    返回 (context文本, hits详情)。
    """
    hits = kb.retrieve(query, top_k=top_k)
    if not hits:
        return "", hits
    context = "以下是知识库中可能相关的政策与解答，回答用户时请优先参考这些内容：\n\n"
    for i, h in enumerate(hits, 1):
        context += f"{i}. 问：{h['question']}\n   答：{h['answer']}\n\n"
    return context, hits
