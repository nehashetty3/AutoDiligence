import os
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from dotenv import load_dotenv
from sklearn.feature_extraction.text import HashingVectorizer

from backend.database.schema import SessionLocal, Filing, NewsArticle

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_EMBED_MODEL = None
_PINECONE_INDEX = None
_IN_MEMORY_STORE: Dict[int, List[Dict[str, Any]]] = {}
_HASH_VECTORIZER = HashingVectorizer(
    n_features=384,
    alternate_sign=False,
    norm="l2",
    ngram_range=(1, 2),
)


def _to_float_list(vector) -> List[float]:
    arr = np.asarray(vector, dtype=np.float32)
    return arr.tolist()


def _cosine_similarity(a, b) -> float:
    a_vec = np.asarray(a, dtype=np.float32)
    b_vec = np.asarray(b, dtype=np.float32)
    a_norm = np.linalg.norm(a_vec)
    b_norm = np.linalg.norm(b_vec)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a_vec, b_vec) / (a_norm * b_norm))


def get_embedding_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer

            model_name = os.getenv("RAG_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            _EMBED_MODEL = SentenceTransformer(model_name)
            print(f"[RAG] Loaded local embedding model: {model_name}")
        except Exception as e:
            print(f"[RAG] SentenceTransformer unavailable, using hashing fallback: {e}")
            _EMBED_MODEL = False
    return _EMBED_MODEL


def get_embedding(text: str) -> List[float] | None:
    if not text or not text.strip():
        return None
    try:
        model = get_embedding_model()
        if model is not False:
            embedding = model.encode(text[:4000], normalize_embeddings=True)
            return _to_float_list(embedding)

        hashed = _HASH_VECTORIZER.transform([text[:4000]])
        return _to_float_list(hashed.toarray()[0])
    except Exception as e:
        print(f"[RAG] Embedding error: {e}")
        return None


def get_pinecone_index():
    global _PINECONE_INDEX
    if _PINECONE_INDEX is not None:
        return _PINECONE_INDEX

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        return None

    try:
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=api_key)
        index_name = os.getenv("PINECONE_INDEX_NAME", "autodiligence")
        existing = [i.name for i in pc.list_indexes()]
        if index_name not in existing:
            pc.create_index(
                name=index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=os.getenv("PINECONE_REGION", "us-east-1"))
            )
            print(f"[RAG] Created Pinecone index: {index_name}")
        _PINECONE_INDEX = pc.Index(index_name)
        print("[RAG] Pinecone connected successfully")
    except Exception as e:
        print(f"[RAG] Pinecone unavailable: {e}")
        return None
    return _PINECONE_INDEX


def disable_pinecone(reason: str):
    global _PINECONE_INDEX
    print(f"[RAG] Disabling Pinecone fallback: {reason}")
    _PINECONE_INDEX = False


def _collect_company_documents(company_id: int) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        docs: List[Dict[str, Any]] = []

        filings = db.query(Filing).filter(Filing.company_id == company_id).order_by(Filing.filing_date.desc()).limit(8).all()
        for filing in filings:
            parts = []
            if filing.revenue is not None:
                parts.append(f"Revenue: {float(filing.revenue):,.0f}")
            if filing.net_income is not None:
                parts.append(f"Net income: {float(filing.net_income):,.0f}")
            if filing.total_debt is not None:
                parts.append(f"Total debt: {float(filing.total_debt):,.0f}")
            if filing.cash is not None:
                parts.append(f"Cash: {float(filing.cash):,.0f}")
            if filing.raw_text:
                parts.append(filing.raw_text[:1200])

            text = ". ".join(p for p in parts if p)
            if text:
                docs.append({
                    "id": f"filing_{filing.id}",
                    "type": "filing",
                    "text": text,
                    "date": str(filing.filing_date) if filing.filing_date else None,
                })

        articles = db.query(NewsArticle).filter(NewsArticle.company_id == company_id).order_by(NewsArticle.published_date.desc()).limit(30).all()
        for article in articles:
            text_parts = [article.headline or "", article.full_text or ""]
            text = ". ".join(part.strip() for part in text_parts if part and part.strip())
            if text:
                docs.append({
                    "id": f"news_{article.id}",
                    "type": "news",
                    "text": text[:1500],
                    "date": str(article.published_date) if article.published_date else None,
                    "source": article.source,
                })

        return docs
    finally:
        db.close()


def index_company_documents(company_id: int, company_name: str):
    docs = _collect_company_documents(company_id)
    if not docs:
        print(f"[RAG] No documents found to index for {company_name}")
        _IN_MEMORY_STORE[company_id] = []
        return {"indexed": 0, "backend": "none"}

    vectors = []
    memory_entries = []
    for doc in docs:
        embedding = get_embedding(doc["text"])
        if not embedding:
            continue

        metadata = {
            "company_id": company_id,
            "company_name": company_name,
            "type": doc["type"],
            "text": doc["text"][:500],
            "date": doc.get("date"),
            "source": doc.get("source"),
        }
        vectors.append({"id": doc["id"], "values": embedding, "metadata": metadata})
        memory_entries.append({"id": doc["id"], "embedding": embedding, "metadata": metadata})

    _IN_MEMORY_STORE[company_id] = memory_entries

    index = get_pinecone_index()
    if index and vectors:
        try:
            namespace = f"company-{company_id}"
            for i in range(0, len(vectors), 100):
                index.upsert(vectors=vectors[i:i + 100], namespace=namespace)
            print(f"[RAG] Indexed {len(vectors)} documents in Pinecone for {company_name}")
            return {"indexed": len(vectors), "backend": "pinecone"}
        except Exception as e:
            if "dimension" in str(e).lower():
                disable_pinecone(str(e))
            else:
                print(f"[RAG] Pinecone upsert failed, keeping in-memory fallback: {e}")

    print(f"[RAG] Indexed {len(memory_entries)} documents in memory for {company_name}")
    return {"indexed": len(memory_entries), "backend": "memory"}


def retrieve_relevant_context(company_id: int, query: str, top_k: int = 3) -> str:
    query_embedding = get_embedding(query)
    if not query_embedding:
        return ""

    index = get_pinecone_index()
    if index:
        try:
            namespace = f"company-{company_id}"
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )
            matches = results.get("matches", []) if isinstance(results, dict) else getattr(results, "matches", [])
            contexts = [m["metadata"].get("text", "") for m in matches if m.get("metadata")]
            if any(contexts):
                return "\n\n".join(c for c in contexts if c)
        except Exception as e:
            if "dimension" in str(e).lower():
                disable_pinecone(str(e))
            else:
                print(f"[RAG] Retrieval error from Pinecone: {e}")

    if company_id not in _IN_MEMORY_STORE:
        # Lazy-build the fallback store if indexing did not run earlier.
        index_company_documents(company_id, f"company-{company_id}")

    entries = _IN_MEMORY_STORE.get(company_id, [])
    if not entries:
        return ""

    ranked = sorted(
        entries,
        key=lambda item: _cosine_similarity(query_embedding, item["embedding"]),
        reverse=True,
    )[:top_k]
    return "\n\n".join(item["metadata"].get("text", "") for item in ranked if item["metadata"].get("text"))
