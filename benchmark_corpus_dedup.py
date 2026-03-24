"""
Benchmark: Corpus-Level Dedup vs Per-Prompt Compression

This script compares:
  1. Per-prompt Zstd (base paper baseline)
  2. Per-prompt Hybrid / BPE+Zstd (base paper best method)
  3. Corpus-level component dedup (HPGCS research contribution)

Generates both synthetic and (optionally) real-world evaluations.

Usage:
    python benchmark_corpus_dedup.py
    python benchmark_corpus_dedup.py --dataset sharegpt --n 5000
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict

# Adjust path if running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    _ZSTD = False

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore


# ─── Realistic Synthetic Data ─────────────────────────────────────────────────

SYSTEM_PROMPTS = [
    (
        "You are a helpful AI assistant specialized in Python programming. "
        "Always provide code examples with detailed explanations. Be concise but thorough. "
        "Follow PEP 8 style guidelines in all code you write. Include proper error handling "
        "in all code examples using try/except blocks. When asked about libraries, always "
        "mention version compatibility requirements.\n\n"
        "Guidelines for your responses:\n"
        "1. Start with a brief explanation of the concept\n"
        "2. Provide a complete, runnable code example\n"
        "3. Explain the code line by line\n"
        "4. Mention common pitfalls and edge cases\n"
        "5. Suggest related topics the user might want to explore\n"
        "6. If the question involves multiple approaches, compare them with pros/cons\n"
        "7. Always include type hints in function signatures\n"
        "8. Add docstrings to all functions and classes\n"
        "9. Include unit test examples when appropriate\n"
        "10. Reference official documentation links when available\n\n"
        "Response format:\n"
        "- Use markdown formatting with headers, code blocks, and lists\n"
        "- Keep code blocks under 50 lines unless complexity requires more\n"
        "- Use syntax highlighting with ```python code blocks\n"
        "- Bold important terms and concepts\n"
        "- Use tables for comparing multiple approaches"
    ),
    (
        "You are a senior data science expert with 15 years of experience. "
        "Help users with statistical analysis, machine learning model development, "
        "data visualization, and experimental design. Use pandas, scikit-learn, "
        "matplotlib, seaborn, and statsmodels in your examples.\n\n"
        "Your expertise covers:\n"
        "- Supervised learning: regression, classification, ensemble methods\n"
        "- Unsupervised learning: clustering, dimensionality reduction, anomaly detection\n"
        "- Deep learning: neural networks, CNNs, RNNs, transformers\n"
        "- Statistical testing: hypothesis tests, confidence intervals, Bayesian methods\n"
        "- Feature engineering: encoding, scaling, selection, extraction\n"
        "- Model evaluation: cross-validation, metrics, bias-variance tradeoff\n"
        "- MLOps: experiment tracking, model versioning, deployment pipelines\n\n"
        "Always explain the mathematical intuition behind algorithms. "
        "Provide both theoretical background and practical implementation. "
        "Discuss assumptions, limitations, and when to use alternatives. "
        "Include data preprocessing steps and explain why they matter. "
        "When comparing models, use proper statistical tests rather than just accuracy."
    ),
    (
        "You are a DevOps and cloud infrastructure engineer. Help with Docker, "
        "Kubernetes, CI/CD pipelines, infrastructure as code, and cloud deployments "
        "across AWS, GCP, and Azure.\n\n"
        "Core competencies:\n"
        "- Container orchestration: Docker, Kubernetes, Helm, Kustomize\n"
        "- CI/CD: GitHub Actions, GitLab CI, Jenkins, ArgoCD\n"
        "- IaC: Terraform, Pulumi, CloudFormation, Ansible\n"
        "- Monitoring: Prometheus, Grafana, Datadog, ELK stack\n"
        "- Security: RBAC, network policies, secrets management, SAST/DAST\n"
        "- Networking: service mesh, ingress, load balancing, DNS\n\n"
        "Provide YAML configurations, shell commands, and Terraform/Pulumi code. "
        "Always prioritize security best practices. Explain the rationale behind "
        "architectural decisions. Include health checks and resource limits. "
        "Suggest monitoring and alerting strategies for each solution."
    ),
]

TOOL_DESCRIPTIONS = [
    (
        "Available tools:\n\n"
        "1. search(query: str, max_results: int = 10, filters: dict = None) -> list[dict]\n"
        "   Search the knowledge base for relevant documents.\n"
        "   Returns: list of {title, content, relevance_score, source_url}\n"
        "   Example: search('python sorting algorithms', max_results=5)\n\n"
        "2. calculate(expression: str, precision: int = 6) -> float\n"
        "   Evaluate mathematical expressions safely.\n"
        "   Supports: arithmetic, trigonometry, logarithms, statistics\n"
        "   Example: calculate('sqrt(144) + log(100, 10)')\n\n"
        "3. get_weather(city: str, units: str = 'metric') -> dict\n"
        "   Get current weather data for a city.\n"
        "   Returns: {temp, humidity, wind_speed, description, forecast_3day}\n"
        "   Example: get_weather('London', units='imperial')\n\n"
        "4. send_email(to: str, subject: str, body: str, cc: list = None) -> bool\n"
        "   Send an email notification.\n"
        "   Returns: True if sent successfully\n"
        "   Example: send_email('user@example.com', 'Report', 'See attached')\n\n"
        "5. run_code(language: str, code: str, timeout: int = 30) -> dict\n"
        "   Execute code in a sandboxed environment.\n"
        "   Returns: {stdout, stderr, exit_code, execution_time_ms}\n"
        "   Supported languages: python, javascript, bash, sql"
    ),
    (
        "Available tools:\n\n"
        "1. query_database(sql: str, database: str = 'default', timeout: int = 60) -> list[dict]\n"
        "   Execute a read-only SQL query against the specified database.\n"
        "   Returns: list of row dictionaries\n"
        "   Constraints: SELECT only, max 10000 rows, timeout in seconds\n\n"
        "2. read_file(path: str, encoding: str = 'utf-8', max_size_mb: int = 10) -> str\n"
        "   Read the contents of a file.\n"
        "   Returns: file content as string\n"
        "   Supported: .txt, .csv, .json, .yaml, .md, .py, .js\n\n"
        "3. write_file(path: str, content: str, mode: str = 'w') -> dict\n"
        "   Write or append to a file.\n"
        "   Returns: {success, bytes_written, path}\n"
        "   Modes: 'w' (overwrite), 'a' (append)\n\n"
        "4. http_request(url: str, method: str = 'GET', headers: dict = None, "
        "body: dict = None) -> dict\n"
        "   Make an HTTP request to an external API.\n"
        "   Returns: {status_code, headers, body, elapsed_ms}\n"
        "   Methods: GET, POST, PUT, DELETE, PATCH"
    ),
]

CONTEXT_PASSAGES = [
    (
        "Context from project documentation:\n\n"
        "The transformers library provides thousands of pretrained models for "
        "Natural Language Processing (NLP), computer vision, and audio tasks. "
        "It supports PyTorch, TensorFlow, and JAX backends with a unified API.\n\n"
        "Key features:\n"
        "- AutoModel classes for automatic model selection\n"
        "- Pipeline API for quick inference\n"
        "- Trainer API for fine-tuning with mixed precision and distributed training\n"
        "- Integration with Hugging Face Hub for model sharing\n"
        "- ONNX and TorchScript export for production deployment\n\n"
        "Installation: pip install transformers[torch]\n"
        "Minimum Python version: 3.8\n"
        "Current stable version: 4.36.0\n\n"
        "Common usage patterns:\n"
        "  from transformers import AutoTokenizer, AutoModel\n"
        "  tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')\n"
        "  model = AutoModel.from_pretrained('bert-base-uncased')\n"
        "  inputs = tokenizer('Hello world', return_tensors='pt')\n"
        "  outputs = model(**inputs)"
    ),
    (
        "Context from project documentation:\n\n"
        "Flask is a lightweight WSGI web application framework. It is designed to "
        "make getting started quick and easy, with the ability to scale up to complex "
        "applications. It provides tools, libraries, and technologies for building "
        "web applications.\n\n"
        "Core concepts:\n"
        "- Application factory pattern for configuration management\n"
        "- Blueprint system for modular application structure\n"
        "- Jinja2 template engine for HTML rendering\n"
        "- Werkzeug WSGI toolkit for request/response handling\n"
        "- Extension ecosystem: Flask-SQLAlchemy, Flask-Login, Flask-RESTful\n\n"
        "Production deployment:\n"
        "- Use Gunicorn or uWSGI as WSGI server\n"
        "- Configure proper logging and error handling\n"
        "- Set SECRET_KEY from environment variables\n"
        "- Use Flask-Migrate for database migrations\n"
        "- Enable CORS with Flask-CORS for API endpoints"
    ),
]

USER_QUERIES = [
    "How do I sort a dictionary by value in Python?",
    "Explain the difference between a list and a tuple with examples.",
    "Write a function to find the longest common subsequence of two strings.",
    "How do I handle file encoding errors in Python 3?",
    "What's the best way to implement a retry decorator with exponential backoff?",
    "How do I set up logging with rotating file handlers and custom formatters?",
    "Explain async/await in Python with a practical web scraping example.",
    "Write a context manager for database transactions with rollback support.",
    "How do I profile memory usage in a Python application and find leaks?",
    "What are the best practices for Python packaging with pyproject.toml?",
    "How do I implement a self-balancing binary search tree (AVL tree)?",
    "Explain metaclasses in Python with a practical ORM example.",
    "How do I use multiprocessing Pool for CPU-bound tasks with progress tracking?",
    "Write a decorator that caches function results with TTL and max size.",
    "How do I implement the observer pattern in Python with weak references?",
    "Explain Python's GIL and its implications for multi-threaded applications.",
    "How do I create a REST API with FastAPI including authentication?",
    "Write a comprehensive function to validate and parse email addresses.",
    "How do I implement token bucket rate limiting in Python?",
    "Explain Python descriptor protocol with a validated properties example.",
]


def generate_synthetic_corpus(
    n_prompts: int = 1000,
    system_prompt_reuse: float = 0.8,
    tool_reuse: float = 0.5,
    context_reuse: float = 0.3,
    include_tools: float = 0.4,
    include_context: float = 0.3,
) -> List[str]:
    """
    Generate a synthetic prompt corpus with controllable redundancy.

    Prompts mirror real LLM production workloads:
    - Long system instructions (500-1500 chars)
    - Tool schemas (500-1200 chars)
    - RAG context passages (500-1000 chars)
    - Unique user queries (50-150 chars)
    """
    import random

    random.seed(42)
    prompts = []
    dominant_sys = SYSTEM_PROMPTS[0]

    for i in range(n_prompts):
        parts = []

        # System prompt (always present, usually shared)
        if random.random() < system_prompt_reuse:
            parts.append(f"System: {dominant_sys}")
        else:
            parts.append(f"System: {random.choice(SYSTEM_PROMPTS)}")

        # Tool descriptions (40% of prompts)
        if random.random() < include_tools:
            if random.random() < tool_reuse:
                parts.append(f"Tool: {TOOL_DESCRIPTIONS[0]}")
            else:
                parts.append(f"Tool: {random.choice(TOOL_DESCRIPTIONS)}")

        # RAG context (30% of prompts)
        if random.random() < include_context:
            if random.random() < context_reuse:
                parts.append(f"Context: {CONTEXT_PASSAGES[0]}")
            else:
                parts.append(f"Context: {random.choice(CONTEXT_PASSAGES)}")

        # User query (always unique-ish)
        base_query = USER_QUERIES[i % len(USER_QUERIES)]
        if random.random() < 0.3:
            base_query += f" (specifically for Python {random.choice(['3.8', '3.9', '3.10', '3.11', '3.12'])})"
        parts.append(f"User: {base_query}")

        prompts.append("\n".join(parts))

    return prompts

# ─── Baseline: Per-Prompt Zstd ────────────────────────────────────────────────

def baseline_per_prompt_zstd(
    prompts: List[str], level: int = 15
) -> Dict:
    """Compress each prompt independently with Zstd (base paper baseline)."""
    if not _ZSTD:
        raise RuntimeError("zstandard not installed")

    cctx = zstd.ZstdCompressor(level=level)
    dctx = zstd.ZstdDecompressor()

    total_original = 0
    total_compressed = 0
    compressed_sizes = []
    t0 = time.perf_counter()

    for text in prompts:
        raw = text.encode("utf-8")
        compressed = cctx.compress(raw)
        # Verify lossless
        assert dctx.decompress(compressed) == raw
        total_original += len(raw)
        total_compressed += len(compressed)
        compressed_sizes.append(len(compressed))

    elapsed = time.perf_counter() - t0

    return {
        "method": "per_prompt_zstd",
        "n_prompts": len(prompts),
        "total_original": total_original,
        "total_compressed": total_compressed,
        "compression_ratio": total_original / total_compressed,
        "space_savings_pct": (1 - total_compressed / total_original) * 100,
        "mean_compressed_size": total_compressed / len(prompts),
        "elapsed_s": elapsed,
    }


# ─── Baseline: Per-Prompt Hybrid (BPE + Zstd) ────────────────────────────────

def baseline_per_prompt_hybrid(
    prompts: List[str], level: int = 15
) -> Dict:
    """BPE tokenize → binary pack → Zstd (base paper's best method)."""
    try:
        from lopace.tokenizer_module import ResidualTextTokenizer
        from lopace.encoder import LearnedCompressionEncoder
    except ImportError:
        return {"method": "per_prompt_hybrid", "error": "modules not available"}

    tokenizer = ResidualTextTokenizer(model="cl100k_base")
    encoder = LearnedCompressionEncoder(zstd_level=level, base_compressor="zstd")

    total_original = 0
    total_compressed = 0
    t0 = time.perf_counter()

    for text in prompts:
        raw = text.encode("utf-8")
        token_ids = tokenizer.tokenize(text)
        packed = tokenizer.pack(token_ids)
        blob, _ = encoder.encode(packed, token_ids)
        total_original += len(raw)
        total_compressed += len(blob)

    elapsed = time.perf_counter() - t0

    return {
        "method": "per_prompt_hybrid",
        "n_prompts": len(prompts),
        "total_original": total_original,
        "total_compressed": total_compressed,
        "compression_ratio": total_original / total_compressed,
        "space_savings_pct": (1 - total_compressed / total_original) * 100,
        "mean_compressed_size": total_compressed / len(prompts),
        "elapsed_s": elapsed,
    }


# ─── Proposed: Corpus-Level Dedup ─────────────────────────────────────────────

def corpus_dedup(prompts: List[str], level: int = 15) -> Dict:
    """Corpus-level component deduplication (proposed method)."""
    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    total_original = 0
    marginal_history = []  # track marginal cost per prompt
    t0 = time.perf_counter()

    for i, text in enumerate(prompts):
        segments = parser.parse_segments(text)
        pid = f"P{i:06d}"
        result = store.store(pid, text, segments)

        total_original += result["original_size"]
        marginal_history.append(result["marginal_bytes"])

        # Verify lossless reconstruction
        rebuilt, verif = store.retrieve(pid)
        assert verif["exact_match"], f"Reconstruction failed for prompt {i}"

    elapsed = time.perf_counter() - t0
    stats = store.corpus_stats()
    store.close()

    return {
        "method": "corpus_dedup",
        "n_prompts": len(prompts),
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["corpus_stored_bytes"],
        "compression_ratio": stats["corpus_compression_ratio"],
        "space_savings_pct": stats["corpus_space_savings_pct"],
        "n_unique_nodes": stats["n_unique_nodes"],
        "avg_refs_per_node": stats["avg_refs_per_node"],
        "blueprint_overhead_pct": stats["storage_overhead_pct"],
        "node_compression_ratio": stats["node_compression_ratio"],
        "mean_marginal_bytes": sum(marginal_history) / len(marginal_history),
        "marginal_first_10": marginal_history[:10],
        "marginal_last_10": marginal_history[-10:],
        "elapsed_s": elapsed,
    }


# ─── Scaling Analysis ─────────────────────────────────────────────────────────

def scaling_analysis(
    prompts: List[str],
    checkpoints: List[int] = None,
    level: int = 15,
) -> List[Dict]:
    """
    Measure corpus compression ratio at increasing corpus sizes.

    This produces the "learning curve" — how compression improves
    as more prompts are added and sharing opportunities increase.
    """
    if checkpoints is None:
        n = len(prompts)
        checkpoints = sorted(set(
            [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, n]
        ))
        checkpoints = [c for c in checkpoints if c <= n]

    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    if _ZSTD:
        cctx = zstd.ZstdCompressor(level=level)

    results = []
    zstd_total = 0

    for i, text in enumerate(prompts):
        # Corpus dedup
        segments = parser.parse_segments(text)
        store.store(f"P{i:06d}", text, segments)

        # Per-prompt Zstd running total
        if _ZSTD:
            zstd_total += len(cctx.compress(text.encode("utf-8")))

        n_seen = i + 1
        if n_seen in checkpoints:
            stats = store.corpus_stats()
            results.append({
                "n_prompts": n_seen,
                "corpus_dedup_ratio": stats["corpus_compression_ratio"],
                "corpus_dedup_bytes": stats["corpus_stored_bytes"],
                "per_prompt_zstd_bytes": zstd_total,
                "per_prompt_zstd_ratio": (
                    stats["total_original_bytes"] / zstd_total
                    if zstd_total else 0
                ),
                "unique_nodes": stats["n_unique_nodes"],
                "avg_reuse": stats["avg_refs_per_node"],
                "dedup_advantage_pct": (
                    (1 - stats["corpus_stored_bytes"] / zstd_total) * 100
                    if zstd_total else 0
                ),
            })

    store.close()
    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark corpus-level dedup vs per-prompt compression"
    )
    parser.add_argument(
        "--n", type=int, default=1000, help="Number of prompts"
    )
    parser.add_argument(
        "--system-reuse", type=float, default=0.8,
        help="Fraction of prompts sharing dominant system prompt"
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Save results JSON to file"
    )
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  HPGCS Corpus-Level Dedup Benchmark")
    print(f"  Generating {args.n} prompts (system reuse = {args.system_reuse})")
    print(f"{'='*70}\n")

    # Generate data
    prompts = generate_synthetic_corpus(
        n_prompts=args.n, system_prompt_reuse=args.system_reuse
    )

    total_chars = sum(len(p) for p in prompts)
    print(f"Dataset: {len(prompts)} prompts, "
          f"{total_chars:,} total characters, "
          f"mean {total_chars/len(prompts):.0f} chars/prompt\n")

    # ── Run baselines ──
    print("Running per-prompt Zstd baseline...")
    r_zstd = baseline_per_prompt_zstd(prompts)
    print(f"  Ratio: {r_zstd['compression_ratio']:.2f}x  "
          f"Savings: {r_zstd['space_savings_pct']:.1f}%  "
          f"Stored: {r_zstd['total_compressed']:,} bytes\n")

    print("Running per-prompt Hybrid (BPE+Zstd) baseline...")
    r_hybrid = baseline_per_prompt_hybrid(prompts)
    if "error" not in r_hybrid:
        print(f"  Ratio: {r_hybrid['compression_ratio']:.2f}x  "
              f"Savings: {r_hybrid['space_savings_pct']:.1f}%  "
              f"Stored: {r_hybrid['total_compressed']:,} bytes\n")
    else:
        print(f"  Skipped: {r_hybrid['error']}\n")

    # ── Run corpus dedup ──
    print("Running corpus-level dedup...")
    r_corpus = corpus_dedup(prompts)
    print(f"  Ratio: {r_corpus['compression_ratio']:.2f}x  "
          f"Savings: {r_corpus['space_savings_pct']:.1f}%  "
          f"Stored: {r_corpus['total_compressed']:,} bytes")
    print(f"  Unique nodes: {r_corpus['n_unique_nodes']}  "
          f"Avg reuse: {r_corpus['avg_refs_per_node']:.1f}x")
    print(f"  Blueprint overhead: {r_corpus['blueprint_overhead_pct']:.1f}%")
    print(f"  Mean marginal cost: {r_corpus['mean_marginal_bytes']:.0f} bytes/prompt\n")

    # ── Comparison ──
    print(f"{'='*70}")
    print(f"  COMPARISON")
    print(f"{'='*70}")
    print(f"{'Method':<30} {'Ratio':>8} {'Savings':>10} {'Stored':>14}")
    print(f"{'-'*62}")
    print(f"{'Per-prompt Zstd':<30} {r_zstd['compression_ratio']:>8.2f}x "
          f"{r_zstd['space_savings_pct']:>9.1f}% "
          f"{r_zstd['total_compressed']:>13,}")
    if "error" not in r_hybrid:
        print(f"{'Per-prompt Hybrid':<30} {r_hybrid['compression_ratio']:>8.2f}x "
              f"{r_hybrid['space_savings_pct']:>9.1f}% "
              f"{r_hybrid['total_compressed']:>13,}")
    print(f"{'Corpus-level Dedup':<30} {r_corpus['compression_ratio']:>8.2f}x "
          f"{r_corpus['space_savings_pct']:>9.1f}% "
          f"{r_corpus['total_compressed']:>13,}")

    # Advantage calculation
    if r_zstd["total_compressed"] > 0:
        advantage = (1 - r_corpus["total_compressed"] / r_zstd["total_compressed"]) * 100
        print(f"\n  → Corpus dedup uses {advantage:.1f}% less storage than per-prompt Zstd")

    # ── Scaling analysis ──
    print(f"\n{'='*70}")
    print(f"  SCALING ANALYSIS (compression ratio vs corpus size)")
    print(f"{'='*70}")
    print(f"{'N prompts':>10} {'Dedup ratio':>12} {'Zstd ratio':>12} {'Dedup advantage':>16}")
    print(f"{'-'*52}")

    scaling = scaling_analysis(prompts)
    for s in scaling:
        print(f"{s['n_prompts']:>10} "
              f"{s['corpus_dedup_ratio']:>12.2f}x "
              f"{s['per_prompt_zstd_ratio']:>12.2f}x "
              f"{s['dedup_advantage_pct']:>15.1f}%")

    # ── Save results ──
    if args.output:
        results = {
            "config": {
                "n_prompts": args.n,
                "system_reuse": args.system_reuse,
            },
            "per_prompt_zstd": r_zstd,
            "per_prompt_hybrid": r_hybrid,
            "corpus_dedup": r_corpus,
            "scaling": scaling,
        }
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()