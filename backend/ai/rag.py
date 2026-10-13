"""
ai/rag.py  (patched)

Changes vs. the original:
  * Paths are resolved from this file's location (backend/), so it no longer
    matters which folder uvicorn is started from.
  * Stale vectors are removed when a knowledge-base file is deleted/renamed.
  * Optional relevance cutoff: set RAG_MAX_DISTANCE in .env (see below).
  * Distances are printed (titles only, never the user's question) so you can tune the cutoff.

Chroma's default metric is squared L2. all-MiniLM-L6-v2 vectors are normalised, so
distance = 2 - 2*cosine. Lower = closer. Start with RAG_MAX_DISTANCE=1.2, watch the
printed distances for good and bad questions, then adjust. Leave it unset to keep the
old "always return top_k" behaviour.
"""

import os
import glob
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend


class RAGEngine:
    def __init__(self, data_dir=None, db_dir=None):
        self.data_dir = str(data_dir or BASE_DIR / "knowledge_base")
        self.db_dir = str(db_dir or BASE_DIR / "vector_db")

        print("Initializing Sentence Transformer...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        print(f"Initializing ChromaDB at {self.db_dir}...")
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.chroma_client.get_or_create_collection(name="egov_knowledge")

        self.load_documents()

    def load_documents(self):
        files = sorted(glob.glob(os.path.join(self.data_dir, "*.txt")))
        if not files:
            print(f"No documents found in knowledge base ({self.data_dir}).")
            return

        documents, metadatas, ids = [], [], []

        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            service_title = "Unknown Service"
            source_type = "Government Knowledge Base"
            portal = None

            for line in content.split("\n"):
                if line.startswith("SERVICE:"):
                    service_title = line.replace("SERVICE:", "").strip()
                elif line.startswith("OFFICIAL PORTAL:"):
                    portal = line.replace("OFFICIAL PORTAL:", "").strip()
                elif line.startswith("SOURCE / SOURCE TYPE:"):
                    source_type = line.replace("SOURCE / SOURCE TYPE:", "").strip()

            doc_id = f"doc_{os.path.splitext(os.path.basename(file_path))[0]}"
            documents.append(content)
            metadatas.append({
                "title": service_title,
                "source_type": source_type,
                "portal": portal or "",
                "file": os.path.basename(file_path),
            })
            ids.append(doc_id)

        print(f"Syncing and indexing {len(documents)} knowledge base documents into ChromaDB...")
        embeddings = self.embedding_model.encode(documents).tolist()
        self.collection.upsert(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)

        # Remove vectors whose source file no longer exists
        try:
            existing_ids = self.collection.get()["ids"]
            stale = [i for i in existing_ids if i not in set(ids)]
            if stale:
                self.collection.delete(ids=stale)
                print(f"Removed {len(stale)} stale document(s) from ChromaDB.")
        except Exception as e:
            print(f"Stale-document cleanup skipped: {e}")

        print(f"Successfully synced {len(documents)} documents in ChromaDB.")

    def search(self, query: str, top_k: int = 3):
        total = self.collection.count()
        if total == 0:
            return [], []

        query_embedding = self.embedding_model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )

        docs_list = results.get("documents") or []
        if not docs_list or not docs_list[0]:
            return [], []

        docs = docs_list[0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        print("[RAG] " + " | ".join(f"{m.get('title', '?')}: {d:.3f}" for m, d in zip(metas, dists)))

        max_d = os.getenv("RAG_MAX_DISTANCE", "").strip()
        if max_d:
            try:
                limit = float(max_d)
                kept = [(d, m) for d, m, dist in zip(docs, metas, dists) if dist <= limit]
                if not kept:
                    return [], []
                docs, metas = [k[0] for k in kept], [k[1] for k in kept]
            except ValueError:
                print(f"[RAG] Ignoring invalid RAG_MAX_DISTANCE={max_d!r}")

        return docs, metas


# Singleton instance
rag_engine = RAGEngine()
