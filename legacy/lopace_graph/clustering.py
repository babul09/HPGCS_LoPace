"""
Vector Similarity Clustering Module - HPGCS Component 4

Groups semantically similar prompts using embedding vectors.
Uses sentence-transformers when available; falls back to TF-IDF cosine
similarity for environments without the heavy ML dependency.
"""

import math
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ─── Optional heavy imports ──────────────────────────────────────────────────

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _ST_AVAILABLE = True
except ImportError:
    SentenceTransformer = None  # type: ignore
    _ST_AVAILABLE = False

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    _NP_AVAILABLE = False


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class Cluster:
    """A semantic cluster of similar prompts."""
    cluster_id: str
    centroid: List[float]           # mean embedding vector
    member_ids: List[str] = field(default_factory=list)   # prompt_ids
    representative_text: str = ""   # first member's text (for display)

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "centroid": self.centroid,
            "member_ids": self.member_ids,
            "representative_text": self.representative_text,
        }

    @staticmethod
    def from_dict(d: dict) -> "Cluster":
        c = Cluster(d["cluster_id"], d["centroid"])
        c.member_ids = d["member_ids"]
        c.representative_text = d.get("representative_text", "")
        return c


# ─── Fallback: character n-gram TF-IDF cosine similarity ─────────────────────

def _ngram_vector(text: str, n: int = 3, vocab_size: int = 512) -> List[float]:
    """Build a hashed n-gram frequency vector (no external dependencies)."""
    vec = [0.0] * vocab_size
    text = text.lower()
    for i in range(len(text) - n + 1):
        gram = text[i:i + n]
        idx = int(hashlib.md5(gram.encode()).hexdigest(), 16) % vocab_size
        vec[idx] += 1.0
    # L2-normalise
    magnitude = math.sqrt(sum(v * v for v in vec))
    if magnitude > 0:
        vec = [v / magnitude for v in vec]
    return vec


def _cosine_similarity_plain(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ─── Main clusterer ───────────────────────────────────────────────────────────

class VectorSimilarityClusterer:
    """
    Groups prompts by semantic similarity.

    Strategy:
      1. Encode each prompt to an embedding vector.
      2. Compare with existing cluster centroids.
      3. Assign to nearest cluster if cosine similarity >= threshold,
         otherwise create a new cluster.
      4. Update the cluster centroid as a running mean.

    Args:
        model_name: sentence-transformers model (default: all-MiniLM-L6-v2).
        threshold: Minimum cosine similarity to join an existing cluster (0-1).
        use_sentence_transformers: Force enable/disable; None = auto-detect.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        threshold: float = 0.80,
        use_sentence_transformers: Optional[bool] = None,
    ):
        self.threshold = threshold
        self._clusters: Dict[str, Cluster] = {}  # cluster_id → Cluster

        # Decide which backend to use
        if use_sentence_transformers is None:
            self._use_st = _ST_AVAILABLE
        else:
            self._use_st = use_sentence_transformers and _ST_AVAILABLE

        self._model = None
        if self._use_st:
            try:
                self._model = SentenceTransformer(model_name)
            except Exception:
                self._use_st = False

    # ------------------------------------------------------------------
    @property
    def backend(self) -> str:
        return "sentence-transformers" if self._use_st else "ngram-cosine"

    def _embed(self, text: str) -> List[float]:
        """Return an embedding vector for the given text."""
        if self._use_st and self._model is not None:
            vec = self._model.encode([text], convert_to_numpy=True)[0]
            return vec.tolist()
        return _ngram_vector(text)

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if _NP_AVAILABLE:
            a_arr = np.array(a, dtype=float)
            b_arr = np.array(b, dtype=float)
            norm_a = np.linalg.norm(a_arr)
            norm_b = np.linalg.norm(b_arr)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))
        return _cosine_similarity_plain(a, b)

    def _update_centroid(self, cluster: Cluster, new_vec: List[float]):
        """Incremental centroid update (running mean)."""
        n = len(cluster.member_ids)  # before appending new member
        if _NP_AVAILABLE:
            centroid = np.array(cluster.centroid, dtype=float)
            new_v = np.array(new_vec, dtype=float)
            updated = (centroid * n + new_v) / (n + 1)
            cluster.centroid = updated.tolist()
        else:
            cluster.centroid = [
                (c * n + v) / (n + 1)
                for c, v in zip(cluster.centroid, new_vec)
            ]

    # ------------------------------------------------------------------
    def assign(self, prompt_id: str, text: str) -> Tuple[str, float]:
        """
        Assign a prompt to a cluster.

        Returns:
            (cluster_id, similarity_score)
        """
        vec = self._embed(text)

        best_cluster_id: Optional[str] = None
        best_sim = -1.0

        for cid, cluster in self._clusters.items():
            sim = self._cosine(vec, cluster.centroid)
            if sim > best_sim:
                best_sim = sim
                best_cluster_id = cid

        if best_cluster_id is not None and best_sim >= self.threshold:
            # Join existing cluster
            cluster = self._clusters[best_cluster_id]
            self._update_centroid(cluster, vec)
            cluster.member_ids.append(prompt_id)
            return best_cluster_id, best_sim
        else:
            # Create new cluster
            new_id = f"C{len(self._clusters) + 1:03d}"
            new_cluster = Cluster(
                cluster_id=new_id,
                centroid=vec,
                member_ids=[prompt_id],
                representative_text=text[:120],
            )
            self._clusters[new_id] = new_cluster
            return new_id, 1.0

    def assign_batch(
        self, prompt_ids: List[str], texts: List[str]
    ) -> List[Tuple[str, float]]:
        return [self.assign(pid, t) for pid, t in zip(prompt_ids, texts)]

    # ------------------------------------------------------------------
    @property
    def num_clusters(self) -> int:
        return len(self._clusters)

    def get_cluster(self, cluster_id: str) -> Optional[Cluster]:
        return self._clusters.get(cluster_id)

    def all_clusters(self) -> List[Cluster]:
        return list(self._clusters.values())

    def summary(self) -> dict:
        sizes = [len(c.member_ids) for c in self._clusters.values()]
        return {
            "num_clusters": self.num_clusters,
            "total_members": sum(sizes),
            "avg_cluster_size": sum(sizes) / len(sizes) if sizes else 0.0,
            "max_cluster_size": max(sizes) if sizes else 0,
            "backend": self.backend,
        }

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {cid: c.to_dict() for cid, c in self._clusters.items()}

    def load_dict(self, data: dict):
        for cid, cd in data.items():
            self._clusters[cid] = Cluster.from_dict(cd)
