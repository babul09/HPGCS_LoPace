# HPGCS / LoPace


<div align="center">
  <img src="https://raw.githubusercontent.com/connectaman/LoPace/main/screenshots/logo-text.png" alt="LoPace Logo" width="600"/>
</div>

**Hybrid Prompt Graph Compression System — Lossless Optimized Prompt Accurate Compression Engine**

A professional, open-source Python package for compressing and reconstructing prompts using a multi-layer graph-based pipeline. Achieve up to 80% space reduction while maintaining perfect lossless reconstruction.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/lopace.svg)](https://pypi.org/project/lopace/)
[![🤗 Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/codewithaman/LoPace)
[![arXiv](https://img.shields.io/badge/arXiv-Paper-b31b1b.svg)](https://arxiv.org/abs/2602.13266)

## The Problem: Storage Challenges with Large Prompts

When building LLM applications, storing prompts efficiently becomes a critical challenge, especially as you scale:

- **💾 Massive Storage Overhead**: Large system prompts, context windows, and conversation histories consume significant database space. For applications serving thousands of users with multiple LLM calls, this translates to gigabytes or terabytes of storage requirements.

- **🚀 Performance Bottlenecks**: Storing uncompressed prompts increases database size, slows down queries, and increases I/O operations. As your user base grows, retrieval and storage operations become progressively slower.

- **💰 Cost Implications**: Larger databases mean higher cloud storage costs, increased backup times, and more expensive infrastructure. With LLM applications handling millions of prompts, these costs compound rapidly.

- **⚡ Latency Issues**: Loading large prompts from storage adds latency to your application. Multiple LLM calls per user session multiply this problem, creating noticeable delays in response times.

## The Solution: HPGCS Compression Engine

HPGCS (Hybrid Prompt Graph Compression System) solves these challenges through a **nine-module pipeline** that combines structural graph decomposition, semantic clustering, BPE tokenization, and Zstandard entropy compression — all losslessly:

- **📉 Up to 80% Space Reduction**: The multi-layer pipeline reduces prompt storage by 70–80% on average, storing 5× less data while maintaining perfect fidelity.

- **⚡ Fast Processing**: 50–200 MB/s compression throughput with sub-linear scaling. Decompression is even faster (100–500 MB/s).

- **✅ 100% Lossless**: SHA-256 hash verification and exact-match reconstruction guarantee that every reconstructed prompt is identical to the original.

- **🎯 Production-Ready**: SQLite-backed graph database with minimal memory footprint (under 10 MB for typical use cases) and excellent scalability.

## HPGCS Pipeline Architecture

### Compression Pipeline

\`\`\`
Prompt Input
     ↓  Module 1 — PromptParser
Structured Component Decomposition
     ↓  Modules 2 & 3 — PromptGraphDecomposer + ReusableNodeManager
Graph Representation + Node Deduplication
     ↓  Module 4 — VectorSimilarityClusterer
Semantic Cluster Assignment
     ↓  Module 5 — ResidualTextTokenizer
BPE Token Encoding + Binary Packing
     ↓  Module 6 — LearnedCompressionEncoder
Zstandard Entropy Compression
     ↓  Module 7 — GraphStorageDatabase
Persistent SQLite Storage
\`\`\`

### Reconstruction Pipeline

\`\`\`
Load from GraphStorageDatabase
     ↓  Module 6 — LearnedCompressionEncoder (decode)
Decompress Zstandard Blob
     ↓  Module 8 — PromptReconstructionEngine
Decode Latent Vector → Token Sequence → Original Prompt
\`\`\`

## Module Reference

| # | Module | Class | Responsibility |
|---|--------|-------|----------------|
| 1 | `parser.py` | `PromptParser` | Rule-based segmentation into labelled components (System, User, Context, Tool, …) |
| 2 | `graph.py` | `PromptGraphDecomposer` | Converts parsed components into a directed prompt graph |
| 3 | `graph.py` | `ReusableNodeManager` | Deduplicates repeated nodes across the prompt corpus |
| 4 | `clustering.py` | `VectorSimilarityClusterer` | Cosine-similarity clustering with sentence-transformer or n-gram fallback |
| 5 | `tokenizer_module.py` | `ResidualTextTokenizer` | BPE tokenization (tiktoken) and binary packing |
| 6 | `encoder.py` | `LearnedCompressionEncoder` | Zstandard entropy compression / decompression |
| 7 | `storage.py` | `GraphStorageDatabase` | SQLite persistence for prompts, nodes, and clusters |
| 8 | `reconstruction.py` | `PromptReconstructionEngine` | Lossless reconstruction with hash verification |

## Features

- 🧩 **Nine-Module Pipeline**: Each stage is independently testable and replaceable
- ✅ **Lossless**: Perfect reconstruction verified by SHA-256 hash matching and character-level exact match
- 📊 **Rich Analytics**: Per-prompt metrics, cluster summaries, node graphs, and database statistics
- 💾 **Persistent Storage**: SQLite-backed database keeps compressed prompts, reusable nodes, and cluster metadata
- 🔧 **Simple API**: Single `HPGCS` class handles the full pipeline
- 🔄 **Batch Compression**: Process lists of prompts in one call
- 🎯 **Legacy Compatibility**: `PromptCompressor` (Zstd / Token / Hybrid) is still available for simpler use cases

## Installation

\`\`\`bash
pip install lopace
\`\`\`

### Dependencies

- `zstandard>=0.22.0` — Zstandard entropy compression
- `tiktoken>=0.5.0` — BPE tokenization

Optional (for richer semantic clustering):
- `sentence-transformers` — Dense vector embeddings (falls back to n-gram similarity if absent)

## Quick Start

### HPGCS (Recommended)

\`\`\`python
from lopace import HPGCS

# Initialize the full pipeline (defaults to in-memory SQLite)
hpgcs = HPGCS(
    db_path=":memory:",          # or a file path for persistence
    tokenizer_model="cl100k_base",
    zstd_level=15,
    cluster_threshold=0.80,
    sentence_transformer=None,   # set to a model name to enable dense embeddings
)

prompt = "System: You are a helpful assistant.\nUser: What is entropy?"

# Compress — returns a metrics dict and stores the prompt internally
result = hpgcs.compress(prompt)
print(result["prompt_id"])            # e.g. "A3F1B2C4"
print(result["compression_ratio"])    # e.g. 3.2
print(result["space_savings_pct"])    # e.g. 68.5

# Reconstruct from the database
text, verification = hpgcs.reconstruct(result["prompt_id"])
assert verification["exact_match"]    # ✓ True
assert text == prompt                 # ✓ True
\`\`\`

### One-Shot Compress and Reconstruct

\`\`\`python
result = hpgcs.compress_and_reconstruct(prompt)
print(result["exact_match"])          # True
print(result["hash_match"])           # True
print(result["reconstructed_text"])   # identical to original
\`\`\`

### Batch Compression

\`\`\`python
prompts = ["Prompt one...", "Prompt two...", "Prompt three..."]
results = hpgcs.compress_batch(prompts)
for r in results:
    print(r["prompt_id"], r["space_savings_pct"])
\`\`\`

### Database Analytics

\`\`\`python
stats = hpgcs.database_stats()
print(stats["total_prompts"])
print(stats["unique_nodes"])
print(stats["num_clusters"])
print(stats["avg_compression_ratio"])

# List all stored prompts
for row in hpgcs.list_prompts():
    print(row["prompt_id"], row["compressed_size"])

# Inspect reusable nodes / clusters
nodes    = hpgcs.list_nodes()
clusters = hpgcs.list_clusters()
\`\`\`

## HPGCS API Reference

### `HPGCS`

Main orchestrator that combines all nine modules.

#### Constructor

\`\`\`python
HPGCS(
    db_path: str = ":memory:",
    tokenizer_model: str = "cl100k_base",
    zstd_level: int = 15,
    cluster_threshold: float = 0.80,
    sentence_transformer: Optional[str] = None,
)
\`\`\`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `str` | `":memory:"` | SQLite path; use `":memory:"` for ephemeral storage |
| `tokenizer_model` | `str` | `"cl100k_base"` | tiktoken encoding name |
| `zstd_level` | `int` | `15` | Zstandard level 1–22 (higher = better ratio, slower) |
| `cluster_threshold` | `float` | `0.80` | Cosine similarity threshold for cluster assignment |
| `sentence_transformer` | `str | None` | `None` | Embedding model name; `None` uses n-gram fallback |

#### Methods

##### `compress(text, prompt_id=None) -> dict`

Run the full compression pipeline on a single prompt. Returns a metrics dict:

\`\`\`python
{
    "prompt_id":             str,    # stable ID for later retrieval
    "original_size_bytes":   int,
    "compressed_size_bytes": int,
    "compression_ratio":     float,  # original / compressed
    "space_savings_pct":     float,  # 0–100
    "compression_time_s":    float,
    "graph_path":            str,    # human-readable node path
    "node_count":            int,
    "cluster_id":            str,
    "cluster_similarity":    float,
    "token_count":           int,
    "packed_size_bytes":     int,
    "components":            list,   # [(type, content), ...]
    "has_structure":         bool,
}
\`\`\`

##### `reconstruct(prompt_id) -> Tuple[str, dict]`

Load and reconstruct a compressed prompt. Returns `(text, verification)` where `verification` contains `exact_match`, `hash_match`, `original_hash`, `rebuilt_hash`, and timing info.

##### `compress_and_reconstruct(text) -> dict`

Compress a prompt and immediately reconstruct it, returning all metrics from both stages in a single dict.

##### `compress_batch(texts) -> List[dict]`

Compress a list of prompts sequentially; returns a list of per-prompt metrics dicts.

##### `database_stats() -> dict`

Return aggregate statistics: total prompts, unique nodes, cluster count, average compression ratio, and per-graph and per-cluster summaries.

##### `list_prompts() -> List[dict]`

Return summary rows for every stored prompt.

##### `list_nodes() -> List[dict]`

Return all reusable nodes persisted in the database.

##### `list_clusters() -> List[dict]`

Return all cluster records from the database.

##### `clear()`

Reset the entire system — drops all in-memory state and re-initializes the database.

---

## Legacy API: `PromptCompressor`

For simpler use cases that do not require graph storage or semantic clustering, the original `PromptCompressor` class is still available:

\`\`\`python
from lopace import PromptCompressor, CompressionMethod

compressor = PromptCompressor(model="cl100k_base", zstd_level=15)

prompt = "You are a helpful AI assistant..."

# Zstd only
compressed = compressor.compress(prompt, CompressionMethod.ZSTD)
original   = compressor.decompress(compressed, CompressionMethod.ZSTD)

# Token-based (BPE)
compressed = compressor.compress(prompt, CompressionMethod.TOKEN)
original   = compressor.decompress(compressed, CompressionMethod.TOKEN)

# Hybrid — combines Token + Zstd (highest ratio)
compressed = compressor.compress(prompt, CompressionMethod.HYBRID)
original   = compressor.decompress(compressed, CompressionMethod.HYBRID)

# Statistics
stats = compressor.get_compression_stats(prompt)
for method, s in stats["methods"].items():
    print(f"{method}: {s['space_saved_percent']:.1f}% saved")
\`\`\`

### `PromptCompressor` Methods

| Method | Description |
|--------|-------------|
| `compress(text, method)` | Compress using the specified `CompressionMethod` |
| `decompress(data, method)` | Decompress bytes back to original string |
| `compress_zstd(text)` | Zstandard-only compression |
| `decompress_zstd(data)` | Zstandard decompression |
| `compress_token(text)` | BPE tokenization + binary packing |
| `decompress_token(data)` | Token-based decompression |
| `compress_hybrid(text)` | Token + Zstd (best ratio) |
| `decompress_hybrid(data)` | Hybrid decompression |
| `compress_and_return_both(text, method)` | Returns `(original, compressed)` |
| `get_compression_stats(text, method=None)` | Per-method stats dict |
| `calculate_shannon_entropy(text, unit)` | Shannon entropy in bits |
| `get_theoretical_compression_limit(text)` | Theoretical minimum size via entropy |

### `CompressionMethod` Enum

\`\`\`python
CompressionMethod.ZSTD    # Zstandard dictionary compression
CompressionMethod.TOKEN   # BPE tokenization + binary packing
CompressionMethod.HYBRID  # TOKEN + ZSTD (recommended for databases)
\`\`\`

---

## How It Works

### Module Details

#### Module 1 — `PromptParser`

Rule-based segmentation using keyword delimiters (`System:`, `User:`, `Instruction:`, `Context:`, `Tool:`, `Assistant:`, `Human:`, `Question:`, `Answer:`). Falls back to a single `unstructured` component if no delimiters are detected.

#### Modules 2 & 3 — `PromptGraphDecomposer` + `ReusableNodeManager`

Converts parsed components into a directed `PromptGraph` where each node represents a structural element. `ReusableNodeManager` deduplicates nodes across all processed prompts using content hashing, enabling cross-prompt storage savings.

#### Module 4 — `VectorSimilarityClusterer`

Assigns each prompt to a semantic cluster using cosine similarity. Uses `sentence-transformers` dense embeddings when available; otherwise falls back to TF-IDF-style n-gram similarity. Threshold is configurable (default `0.80`).

#### Module 5 — `ResidualTextTokenizer`

BPE tokenization via tiktoken. Packs token IDs as `uint16` (2 bytes/token) for IDs ≤ 65 535, or `uint32` (4 bytes/token) otherwise.

#### Module 6 — `LearnedCompressionEncoder`

Applies Zstandard (LZ77 + FSE/Huffman) entropy coding to the binary token payload. Stores a compact latent representation alongside the compressed blob.

#### Module 7 — `GraphStorageDatabase`

SQLite-backed persistence layer with three tables: `prompts`, `nodes`, and `clusters`. Supports insert, upsert, and bulk retrieval operations.

#### Module 8 — `PromptReconstructionEngine`

Reverses the pipeline: decompresses → decodes token IDs → reconstructs text → verifies via SHA-256 hash comparison and character-level exact match.

### Compression Techniques

1. **LZ77 (Sliding Window)** — used internally by Zstandard to find repeated byte sequences and replace them with back-references.
2. **FSE / Huffman Coding** — Zstandard's Finite State Entropy assigns shorter codes to more-frequent symbols.
3. **BPE Tokenization** — tiktoken reduces the vocabulary before entropy coding, improving downstream compression.

### Shannon Entropy (Theoretical Limit)

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

\`\`\`python
compressor = PromptCompressor()
entropy = compressor.calculate_shannon_entropy("Your prompt")
limits  = compressor.get_theoretical_compression_limit("Your prompt")
print(f"Theoretical minimum: {limits['theoretical_min_bytes']:.2f} bytes")
print(f"Theoretical space savings: {limits['theoretical_space_savings_percent']:.1f}%")
\`\`\`

---

## Benchmarks & Performance Analysis

Benchmarks conducted on 10 diverse prompts (small, medium, large categories).

### Key Findings

| Metric | Value |
|--------|-------|
| Average space savings (Hybrid) | 70–80% |
| Compression throughput | 50–200 MB/s |
| Decompression throughput | 100–500 MB/s |
| Memory footprint (typical) | < 10 MB |
| Reconstruction fidelity | 100% (lossless) |

- Compression effectiveness increases with prompt size (larger patterns → better ratios)
- All methods verified lossless across all test cases
- Performance scales sub-linearly with prompt size

---

## Interactive Web App (Streamlit)

\`\`\`bash
streamlit run streamlit_app.py
\`\`\`

Opens at `http://localhost:8501`. Features:

- Real-time compression of user-supplied prompts
- All four industry-standard metrics:
  - Compression Ratio: CR = S_original / S_compressed
  - Space Savings: SS = 1 − S_compressed / S_original
  - Bits Per Character: BPC = Total Bits / Total Characters
  - Throughput: T = Data Size / Time
- SHA-256 hash verification + exact-match check
- Side-by-side method comparison

---

## Development

### Setup

\`\`\`bash
git clone https://github.com/connectaman/LoPace.git
cd HPGCS_LoPace
pip install -r requirements-dev.txt
\`\`\`

### Running Tests

\`\`\`bash
pytest
\`\`\`

### Versioning & Releasing

Version is derived from Git tags via `setuptools-scm` — no manual edits needed.

\`\`\`bash
git tag v0.2.0
git push origin v0.2.0
\`\`\`

CI will build and publish the tagged version to PyPI automatically.

---

## Mathematical Background

### Compression Ratio

$$CR = \frac{S_{\text{original}}}{S_{\text{compressed}}}$$

### Space Savings

$$SS = \left(1 - \frac{S_{\text{compressed}}}{S_{\text{original}}}\right) \times 100$$

### Reconstruction Error

$$E = \frac{1}{N} \sum_{i=1}^{N} \mathbb{1}(x_i \neq \hat{x}_i) = 0$$

All methods guarantee zero reconstruction error.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/ -v`)
4. Open a Pull Request

## Author

Aman Ulla

## Acknowledgments

- Built on [zstandard](https://github.com/facebook/zstd) and [tiktoken](https://github.com/openai/tiktoken)
- Optional semantic clustering via [sentence-transformers](https://www.sbert.net/)
- Inspired by the need for efficient prompt storage in production LLM applications