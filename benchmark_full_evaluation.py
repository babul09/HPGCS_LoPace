"""
Full Evaluation: Corpus-Level Dedup vs All Baselines

Produces paper-ready results including:
  1. Per-prompt Zstd (base paper baseline)
  2. Per-prompt Hybrid BPE+Zstd (base paper best)
  3. Zstd with dictionary training (base paper's #1 future work)
  4. Corpus-level component dedup (proposed method)

Tests across:
  - Controlled reuse rates (0%, 10%, 50%, 80%, 100%)
  - Corpus sizes (1 to 10,000)
  - Realistic vs worst-case scenarios

Usage:
    python benchmark_full_evaluation.py
    python benchmark_full_evaluation.py --n 5000
    python benchmark_full_evaluation.py --real-data
"""

import argparse
import csv
import json
import os
import random
import sys
import time
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    _ZSTD = False

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore

# ─── Realistic Content Pools ─────────────────────────────────────────────────

SYSTEM_PROMPTS_POOL = [
    # 1 — Python assistant (long)
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
    # 2 — Data science
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
        "Discuss assumptions, limitations, and when to use alternatives."
    ),
    # 3 — DevOps
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
        "Always prioritize security best practices."
    ),
    # 4 — Web development
    (
        "You are a full-stack web developer specializing in modern JavaScript "
        "frameworks. You have deep expertise in React, Next.js, Node.js, and "
        "TypeScript. Help users build scalable, accessible, and performant "
        "web applications.\n\n"
        "Technical stack expertise:\n"
        "- Frontend: React 18+, Next.js 14+, Tailwind CSS, Radix UI\n"
        "- Backend: Node.js, Express, Fastify, tRPC\n"
        "- Database: PostgreSQL, Prisma ORM, Redis, MongoDB\n"
        "- Auth: NextAuth.js, Clerk, JWT, OAuth 2.0\n"
        "- Testing: Jest, React Testing Library, Playwright, Cypress\n"
        "- Deployment: Vercel, AWS, Docker, GitHub Actions\n\n"
        "Always follow accessibility (WCAG 2.1 AA) guidelines. "
        "Use TypeScript for all code examples. Prefer server components "
        "and server actions in Next.js where appropriate."
    ),
    # 5 — Security analyst
    (
        "You are a cybersecurity analyst and penetration testing expert. "
        "Help users understand security vulnerabilities, implement secure "
        "coding practices, and design defense-in-depth architectures.\n\n"
        "Areas of expertise:\n"
        "- Web security: OWASP Top 10, XSS, CSRF, SQL injection, SSRF\n"
        "- Network security: firewalls, IDS/IPS, VPN, zero trust architecture\n"
        "- Cryptography: TLS, PKI, key management, hashing, encryption\n"
        "- Cloud security: IAM, security groups, KMS, audit logging\n"
        "- Compliance: SOC 2, GDPR, HIPAA, PCI DSS\n"
        "- Incident response: SIEM, forensics, threat hunting, playbooks\n\n"
        "Always explain the attack vector, impact, and remediation. "
        "Provide secure code examples alongside vulnerable versions. "
        "Never provide exploit code that could be used maliciously."
    ),
]

TOOL_DESCRIPTIONS_POOL = [
    (
        "Available tools:\n\n"
        "1. search(query: str, max_results: int = 10) -> list[dict]\n"
        "   Search the knowledge base. Returns: [{title, content, score, url}]\n\n"
        "2. calculate(expression: str, precision: int = 6) -> float\n"
        "   Evaluate math expressions. Supports: arithmetic, trig, log, stats\n\n"
        "3. get_weather(city: str, units: str = 'metric') -> dict\n"
        "   Get weather data. Returns: {temp, humidity, wind, description}\n\n"
        "4. send_email(to: str, subject: str, body: str) -> bool\n"
        "   Send an email. Returns: True if successful\n\n"
        "5. run_code(language: str, code: str, timeout: int = 30) -> dict\n"
        "   Execute code in sandbox. Returns: {stdout, stderr, exit_code}"
    ),
    (
        "Available tools:\n\n"
        "1. query_database(sql: str, database: str = 'default') -> list[dict]\n"
        "   Execute read-only SQL. Max 10000 rows, SELECT only\n\n"
        "2. read_file(path: str, encoding: str = 'utf-8') -> str\n"
        "   Read file contents. Supported: .txt, .csv, .json, .yaml, .py\n\n"
        "3. write_file(path: str, content: str, mode: str = 'w') -> dict\n"
        "   Write to file. Returns: {success, bytes_written, path}\n\n"
        "4. http_request(url: str, method: str = 'GET', body: dict = None) -> dict\n"
        "   HTTP request. Returns: {status_code, headers, body, elapsed_ms}"
    ),
]

CONTEXT_PASSAGES_POOL = [
    (
        "Context from documentation:\n\n"
        "The transformers library provides thousands of pretrained models for "
        "NLP, computer vision, and audio. Supports PyTorch, TensorFlow, JAX.\n\n"
        "Key features: AutoModel classes, Pipeline API, Trainer API, "
        "Hub integration, ONNX/TorchScript export.\n\n"
        "  from transformers import AutoTokenizer, AutoModel\n"
        "  tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')\n"
        "  model = AutoModel.from_pretrained('bert-base-uncased')\n"
        "  outputs = model(**tokenizer('Hello world', return_tensors='pt'))"
    ),
    (
        "Context from documentation:\n\n"
        "Flask is a lightweight WSGI web application framework designed for "
        "quick starts and scalable applications.\n\n"
        "Core: Application factory, Blueprints, Jinja2, Werkzeug.\n"
        "Extensions: Flask-SQLAlchemy, Flask-Login, Flask-RESTful.\n"
        "Deploy with Gunicorn/uWSGI, use Flask-Migrate for DB migrations."
    ),
    (
        "Context from documentation:\n\n"
        "FastAPI is a modern, fast web framework for building APIs with Python "
        "3.8+ based on standard type hints. Built on Starlette and Pydantic.\n\n"
        "Features: automatic OpenAPI docs, async support, dependency injection, "
        "WebSocket support, background tasks, middleware.\n\n"
        "  from fastapi import FastAPI\n"
        "  app = FastAPI()\n"
        "  @app.get('/items/{item_id}')\n"
        "  async def read_item(item_id: int, q: str = None):\n"
        "      return {'item_id': item_id, 'q': q}"
    ),
]

USER_QUERIES_POOL = [
    "How do I sort a dictionary by value in Python?",
    "Explain list comprehensions vs generator expressions.",
    "Write a function for the longest common subsequence.",
    "How do I handle file encoding errors in Python 3?",
    "Implement a retry decorator with exponential backoff.",
    "Set up logging with rotating file handlers.",
    "Explain async/await with a web scraping example.",
    "Write a context manager for database transactions.",
    "How do I profile memory usage and find leaks?",
    "Best practices for Python packaging with pyproject.toml?",
    "Implement a self-balancing AVL tree.",
    "Explain metaclasses with a practical ORM example.",
    "Use multiprocessing Pool for CPU-bound tasks.",
    "Write a cache decorator with TTL and max size.",
    "Implement the observer pattern with weak references.",
    "Explain Python's GIL and threading implications.",
    "Create a REST API with FastAPI and authentication.",
    "Write a comprehensive email validation function.",
    "Implement token bucket rate limiting.",
    "Explain Python descriptor protocol with examples.",
    "How do I create custom iterators and generators?",
    "Implement a thread-safe singleton pattern.",
    "Write a binary search with edge case handling.",
    "How do I use dataclasses with validation?",
    "Implement a simple pub/sub message broker.",
    "Explain Python's MRO and cooperative multiple inheritance.",
    "Write a command-line tool with argparse and subcommands.",
    "How do I implement custom comparison operators?",
    "Create a simple ORM using descriptors and metaclasses.",
    "Implement connection pooling for database access.",
]


# ─── Data Generator ───────────────────────────────────────────────────────────

def generate_corpus(
    n_prompts: int,
    system_reuse: float = 0.8,
    n_unique_systems: int = 5,
    include_tools: float = 0.4,
    include_context: float = 0.3,
    tool_reuse: float = 0.5,
    context_reuse: float = 0.3,
    seed: int = 42,
) -> Tuple[List[str], Dict]:
    """
    Generate prompt corpus with precise control over redundancy.

    When system_reuse=0.0 and n_unique_systems is large,
    every prompt gets a UNIQUE system prompt (worst case for dedup).

    Returns:
        (prompts, metadata_dict)
    """
    rng = random.Random(seed)
    prompts = []

    # Build system prompt pool
    if n_unique_systems <= len(SYSTEM_PROMPTS_POOL):
        sys_pool = SYSTEM_PROMPTS_POOL[:n_unique_systems]
    else:
        # Generate additional unique system prompts
        sys_pool = list(SYSTEM_PROMPTS_POOL)
        for i in range(n_unique_systems - len(SYSTEM_PROMPTS_POOL)):
            variant = (
                f"You are AI assistant variant #{i + len(SYSTEM_PROMPTS_POOL) + 1}. "
                f"Specialized in topic area {rng.randint(1, 100)}. "
                f"Your unique expertise includes: {', '.join(rng.sample(['algorithms', 'databases', 'networking', 'security', 'ML', 'NLP', 'CV', 'robotics', 'compilers', 'OS', 'distributed systems', 'graphics', 'HCI', 'bioinformatics', 'quantum computing'], 4))}.\n\n"
                f"Guidelines:\n"
                + "\n".join(f"- Guideline {j}: Follow best practice #{rng.randint(100,999)}"
                           for j in range(1, rng.randint(5, 12)))
                + f"\n\nResponse style: {'detailed' if rng.random() > 0.5 else 'concise'}. "
                f"Always include examples. Format with markdown."
            )
            sys_pool.append(variant)

    dominant_sys = sys_pool[0]

    actual_reuse_count = 0

    for i in range(n_prompts):
        parts = []

        # System prompt
        if rng.random() < system_reuse:
            parts.append(f"System: {dominant_sys}")
            actual_reuse_count += 1
        else:
            parts.append(f"System: {rng.choice(sys_pool)}")

        # Tools
        if rng.random() < include_tools:
            if rng.random() < tool_reuse:
                parts.append(f"Tool: {TOOL_DESCRIPTIONS_POOL[0]}")
            else:
                parts.append(f"Tool: {rng.choice(TOOL_DESCRIPTIONS_POOL)}")

        # Context
        if rng.random() < include_context:
            if rng.random() < context_reuse:
                parts.append(f"Context: {CONTEXT_PASSAGES_POOL[0]}")
            else:
                parts.append(f"Context: {rng.choice(CONTEXT_PASSAGES_POOL)}")

        # User query (always present, mostly unique)
        base_query = USER_QUERIES_POOL[i % len(USER_QUERIES_POOL)]
        if rng.random() < 0.4:
            base_query += f" (for Python {rng.choice(['3.8', '3.9', '3.10', '3.11', '3.12'])})"
        if rng.random() < 0.2:
            base_query += f" Please include benchmarks and performance analysis."
        parts.append(f"User: {base_query}")

        prompts.append("\n".join(parts))

    metadata = {
        "n_prompts": n_prompts,
        "system_reuse_setting": system_reuse,
        "actual_system_reuse_pct": actual_reuse_count / n_prompts * 100,
        "n_unique_systems": n_unique_systems,
        "mean_prompt_chars": sum(len(p) for p in prompts) / n_prompts,
        "total_chars": sum(len(p) for p in prompts),
    }
    return prompts, metadata


def generate_zero_reuse_corpus(n_prompts: int, seed: int = 42) -> Tuple[List[str], Dict]:
    """
    Generate corpus where EVERY prompt has a unique system prompt.
    Worst case scenario for deduplication.
    """
    return generate_corpus(
        n_prompts=n_prompts,
        system_reuse=0.0,
        n_unique_systems=n_prompts,  # each prompt gets its own
        include_tools=0.0,
        include_context=0.0,
        seed=seed,
    )


# ─── Baseline Methods ─────────────────────────────────────────────────────────

def baseline_zstd(prompts: List[str], level: int = 15) -> Dict:
    """Per-prompt Zstd compression."""
    cctx = zstd.ZstdCompressor(level=level)
    total_orig = 0
    total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        total_orig += len(raw)
        total_comp += len(cctx.compress(raw))
    return {
        "method": "per_prompt_zstd",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "ratio": total_orig / total_comp if total_comp else 0,
        "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0,
    }


def baseline_zstd_dictionary(prompts: List[str], level: int = 15,
                              dict_size: int = 131072,
                              train_fraction: float = 0.1) -> Dict:
    """
    Zstd with dictionary training — the base paper's #1 recommended future work.

    Trains a compression dictionary on a fraction of the corpus,
    then compresses all prompts using it.
    """
    if not _ZSTD:
        return {"method": "zstd_dictionary", "error": "zstd not available"}

    # Split into training and test (but compress ALL with the dictionary)
    n_train = max(10, int(len(prompts) * train_fraction))
    train_samples = [p.encode("utf-8") for p in prompts[:n_train]]

    # Train dictionary
    try:
        dictionary = zstd.train_dictionary(dict_size, train_samples)
    except Exception as e:
        return {"method": "zstd_dictionary", "error": str(e)}

    cctx = zstd.ZstdCompressor(level=level, dict_data=dictionary)
    dctx = zstd.ZstdDecompressor(dict_data=dictionary)

    total_orig = 0
    total_comp = 0
    dict_overhead = dict_size  # dictionary must be stored/transmitted

    for text in prompts:
        raw = text.encode("utf-8")
        compressed = cctx.compress(raw)
        # Verify lossless
        assert dctx.decompress(compressed) == raw
        total_orig += len(raw)
        total_comp += len(compressed)

    total_with_dict = total_comp + dict_overhead

    return {
        "method": "zstd_dictionary",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "total_with_dict_overhead": total_with_dict,
        "dictionary_size": dict_overhead,
        "ratio_without_dict": total_orig / total_comp if total_comp else 0,
        "ratio_with_dict": total_orig / total_with_dict if total_with_dict else 0,
        "savings_pct": (1 - total_with_dict / total_orig) * 100 if total_orig else 0,
        "train_samples": n_train,
    }


def baseline_hybrid(prompts: List[str], level: int = 15) -> Dict:
    """Per-prompt BPE + Zstd (base paper's hybrid method)."""
    try:
        from lopace.tokenizer_module import ResidualTextTokenizer
        from lopace.encoder import LearnedCompressionEncoder
    except ImportError:
        return {"method": "per_prompt_hybrid", "error": "modules not available"}

    tokenizer = ResidualTextTokenizer(model="cl100k_base")
    encoder = LearnedCompressionEncoder(zstd_level=level, base_compressor="zstd")

    total_orig = 0
    total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        token_ids = tokenizer.tokenize(text)
        packed = tokenizer.pack(token_ids)
        blob, _ = encoder.encode(packed, token_ids)
        total_orig += len(raw)
        total_comp += len(blob)

    return {
        "method": "per_prompt_hybrid",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "ratio": total_orig / total_comp if total_comp else 0,
        "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0,
    }


def corpus_dedup_method(prompts: List[str], level: int = 15) -> Dict:
    """Corpus-level component deduplication."""
    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    marginal_costs = []
    for i, text in enumerate(prompts):
        segments = parser.parse_segments(text)
        result = store.store(f"P{i:06d}", text, segments)
        marginal_costs.append(result["marginal_bytes"])

        # Verify every 100th prompt
        if i % 100 == 0:
            rebuilt, v = store.retrieve(f"P{i:06d}")
            assert v["exact_match"], f"Reconstruction failed at prompt {i}"

    stats = store.corpus_stats()
    store.close()

    return {
        "method": "corpus_dedup",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["corpus_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "unique_nodes": stats["n_unique_nodes"],
        "avg_reuse": stats["avg_refs_per_node"],
        "marginal_costs": marginal_costs,
    }


# ─── Scaling Analysis ─────────────────────────────────────────────────────────

def scaling_analysis(prompts: List[str], level: int = 15) -> List[Dict]:
    """Measure all methods at increasing corpus sizes."""
    n = len(prompts)
    checkpoints = sorted(set(
        [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, n]
    ))
    checkpoints = [c for c in checkpoints if c <= n]

    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)
    cctx = zstd.ZstdCompressor(level=level)

    # Try dictionary training too
    dict_cctx = None
    if n >= 20:
        try:
            train_n = max(10, n // 10)
            train_samples = [p.encode("utf-8") for p in prompts[:train_n]]
            dictionary = zstd.train_dictionary(131072, train_samples)
            dict_cctx = zstd.ZstdCompressor(level=level, dict_data=dictionary)
        except Exception:
            pass

    results = []
    zstd_total = 0
    dict_total = 0

    for i, text in enumerate(prompts):
        segments = parser.parse_segments(text)
        store.store(f"P{i:06d}", text, segments)

        raw = text.encode("utf-8")
        zstd_total += len(cctx.compress(raw))
        if dict_cctx:
            dict_total += len(dict_cctx.compress(raw))

        n_seen = i + 1
        if n_seen in checkpoints:
            stats = store.corpus_stats()
            row = {
                "n": n_seen,
                "orig": stats["total_original_bytes"],
                "dedup_stored": stats["corpus_stored_bytes"],
                "dedup_ratio": stats["corpus_compression_ratio"],
                "zstd_stored": zstd_total,
                "zstd_ratio": stats["total_original_bytes"] / zstd_total if zstd_total else 0,
                "unique_nodes": stats["n_unique_nodes"],
                "avg_reuse": stats["avg_refs_per_node"],
            }
            if dict_cctx:
                dict_with_overhead = dict_total + 131072
                row["dict_stored"] = dict_with_overhead
                row["dict_ratio"] = stats["total_original_bytes"] / dict_with_overhead if dict_with_overhead else 0
            results.append(row)

    store.close()
    return results


# ─── Experiment Runner ────────────────────────────────────────────────────────

def run_experiment(name: str, prompts: List[str], metadata: Dict) -> Dict:
    """Run all methods on a corpus and return consolidated results."""
    print(f"\n{'='*70}")
    print(f"  EXPERIMENT: {name}")
    print(f"  {metadata['n_prompts']} prompts, "
          f"mean {metadata['mean_prompt_chars']:.0f} chars/prompt, "
          f"{metadata['total_chars']:,} total chars")
    print(f"{'='*70}")

    results = {"experiment": name, "metadata": metadata, "methods": {}}

    # 1. Per-prompt Zstd
    print("  [1/4] Per-prompt Zstd...", end=" ", flush=True)
    r = baseline_zstd(prompts)
    results["methods"]["zstd"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%")

    # 2. Per-prompt Hybrid
    print("  [2/4] Per-prompt Hybrid...", end=" ", flush=True)
    r = baseline_hybrid(prompts)
    results["methods"]["hybrid"] = r
    if "error" not in r:
        print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%")
    else:
        print(f"skipped ({r['error']})")

    # 3. Zstd with dictionary
    print("  [3/4] Zstd + dictionary...", end=" ", flush=True)
    r = baseline_zstd_dictionary(prompts)
    results["methods"]["zstd_dict"] = r
    if "error" not in r:
        print(f"{r['ratio_with_dict']:.2f}x  {r['savings_pct']:.1f}% "
              f"(dict overhead: {r['dictionary_size']:,} bytes)")
    else:
        print(f"skipped ({r['error']})")

    # 4. Corpus dedup
    print("  [4/4] Corpus-level dedup...", end=" ", flush=True)
    r = corpus_dedup_method(prompts)
    results["methods"]["corpus_dedup"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['unique_nodes']} nodes, {r['avg_reuse']:.1f}x reuse)")

    # Comparison table
    print(f"\n  {'Method':<25} {'Ratio':>8} {'Savings':>10} {'Stored':>14}")
    print(f"  {'-'*57}")
    for key, label in [("zstd", "Per-prompt Zstd"),
                        ("hybrid", "Per-prompt Hybrid"),
                        ("zstd_dict", "Zstd + Dictionary"),
                        ("corpus_dedup", "Corpus Dedup")]:
        m = results["methods"].get(key, {})
        if "error" in m:
            continue
        ratio = m.get("ratio") or m.get("ratio_with_dict", 0)
        savings = m.get("savings_pct", 0)
        stored = m.get("total_compressed") or m.get("total_with_dict_overhead", 0)
        print(f"  {label:<25} {ratio:>8.2f}x {savings:>9.1f}% {stored:>13,}")

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Full HPGCS evaluation")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--output", type=str, default="evaluation_results.json")
    ap.add_argument("--csv", type=str, default="scaling_results.csv")
    args = ap.parse_args()

    all_results = []

    # ── Experiment 1: Standard (80% reuse) ────────────────────────────
    prompts, meta = generate_corpus(args.n, system_reuse=0.8)
    all_results.append(run_experiment("Standard (80% reuse)", prompts, meta))

    # ── Experiment 2: Full reuse (100%) ───────────────────────────────
    prompts, meta = generate_corpus(args.n, system_reuse=1.0)
    all_results.append(run_experiment("Full reuse (100%)", prompts, meta))

    # ── Experiment 3: Low reuse (10%) ─────────────────────────────────
    prompts, meta = generate_corpus(args.n, system_reuse=0.1, n_unique_systems=5)
    all_results.append(run_experiment("Low reuse (10%)", prompts, meta))

    # ── Experiment 4: ZERO reuse (worst case) ─────────────────────────
    prompts, meta = generate_zero_reuse_corpus(args.n)
    all_results.append(run_experiment("Zero reuse (worst case)", prompts, meta))

    # ── Experiment 5: Scaling analysis ────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SCALING ANALYSIS")
    print(f"{'='*70}")

    prompts, _ = generate_corpus(args.n, system_reuse=0.8)
    scaling = scaling_analysis(prompts)

    has_dict = "dict_ratio" in scaling[0] if scaling else False

    header = f"  {'N':>6} {'Dedup':>8} {'Zstd':>8}"
    if has_dict:
        header += f" {'Zstd+Dict':>10}"
    header += f" {'Dedup vs Zstd':>14}"
    print(header)
    print(f"  {'-'*(len(header)-2)}")

    for s in scaling:
        line = f"  {s['n']:>6} {s['dedup_ratio']:>8.2f}x {s['zstd_ratio']:>8.2f}x"
        if has_dict:
            line += f" {s.get('dict_ratio', 0):>10.2f}x"
        advantage = (1 - s['dedup_stored'] / s['zstd_stored']) * 100
        line += f" {advantage:>13.1f}%"
        print(line)

    # Save scaling CSV
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=scaling[0].keys())
            writer.writeheader()
            writer.writerows(scaling)
        print(f"\n  Scaling data saved to {args.csv}")

    # ── Save all results ──────────────────────────────────────────────
    # Remove marginal_costs from JSON (too large)
    for r in all_results:
        for m in r["methods"].values():
            m.pop("marginal_costs", None)

    output = {
        "experiments": all_results,
        "scaling": scaling,
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Full results saved to {args.output}")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SUMMARY ACROSS ALL EXPERIMENTS")
    print(f"{'='*70}")
    print(f"  {'Experiment':<30} {'Zstd':>7} {'Hybrid':>8} {'Dict':>7} {'Dedup':>7}")
    print(f"  {'-'*62}")
    for r in all_results:
        name = r["experiment"][:30]
        zr = r["methods"].get("zstd", {}).get("ratio", 0)
        hr = r["methods"].get("hybrid", {}).get("ratio", 0)
        dr = r["methods"].get("zstd_dict", {}).get("ratio_with_dict", 0)
        cr = r["methods"].get("corpus_dedup", {}).get("ratio", 0)
        print(f"  {name:<30} {zr:>7.2f}x {hr:>7.2f}x {dr:>7.2f}x {cr:>7.2f}x")


if __name__ == "__main__":
    main()