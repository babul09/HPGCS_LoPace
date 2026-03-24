
"""
Full Evaluation: Corpus-Level Dedup vs All Baselines

Produces paper-ready results including:
    Per-prompt Zstd (base paper baseline)
    Per-prompt Hybrid BPE+Zstd (base paper best)
    Zstd with dictionary training (base paper's #1 future work)
    Corpus-level component dedup (proposed method)

Tests across:
    Controlled reuse rates (0%, 10%, 50%, 80%, 100%)
    Corpus sizes (1 to 10,000)
    Realistic vs worst-case scenarios
    Real-world datasets from JSON files

Usage:
    python benchmark_full_evaluation.py
    python benchmark_full_evaluation.py --n 5000
    python benchmark_full_evaluation.py --real-data dataset.json
    python benchmark_full_evaluation.py --real-data dataset.json --json-field prompt
    python benchmark_full_evaluation.py --real-data dataset.json --json-field conversations --nested-field value
    python benchmark_full_evaluation.py --real-data-dir ./datasets/
"""

import argparse
import csv
import glob
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

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

# ─── Real Dataset Loader ────────────────────────────────────────────────────

def load_real_dataset(
    filepath: str,
    json_field: Optional[str] = None,
    nested_field: Optional[str] = None,
    max_prompts: Optional[int] = None,
    min_length: int = 10,
) -> Tuple[List[str], Dict]:
    """
    Load prompts from a real JSON dataset file.

    Supports many common formats:
        - JSON array of strings: ["prompt1", "prompt2", ...]
        - JSON array of objects: [{"prompt": "...", ...}, ...]
        - JSON Lines (JSONL): one JSON object per line
        - ShareGPT format: [{"conversations": [{"from": "human", "value": "..."}]}, ...]
        - Alpaca format: [{"instruction": "...", "input": "...", "output": "..."}, ...]
        - OpenAI format: [{"messages": [{"role": "user", "content": "..."}]}, ...]
        - Single object with a list field: {"data": [...], "rows": [...]}

    Args:
        filepath: Path to JSON or JSONL file
        json_field: Specific field name to extract text from (auto-detected if None)
        nested_field: For nested structures (e.g., "value" within conversation turns)
        max_prompts: Maximum number of prompts to load (None = all)
        min_length: Minimum character length to include a prompt

    Returns:
        (prompts, metadata_dict)
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    file_size = filepath.stat().st_size
    print(f"\n  Loading dataset: {filepath}")
    print(f"  File size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")

    # Load raw data
    raw_data = _load_json_file(filepath)

    # Extract prompts
    prompts = _extract_prompts(raw_data, json_field, nested_field)

    # Filter and clean
    prompts = [p.strip() for p in prompts if isinstance(p, str) and len(p.strip()) >= min_length]

    # Deduplicate while preserving order (to measure natural redundancy)
    # We do NOT deduplicate here — the whole point is to measure how well
    # the compression handles natural duplicates
    if max_prompts and len(prompts) > max_prompts:
        prompts = prompts[:max_prompts]

    if not prompts:
        raise ValueError(
            f"No valid prompts extracted from {filepath}. "
            f"Try specifying --json-field explicitly. "
            f"Sample keys found: {_sample_keys(raw_data)}"
        )

    # Compute dataset statistics
    lengths = [len(p) for p in prompts]
    unique_prompts = len(set(prompts))

    metadata = {
        "n_prompts": len(prompts),
        "source_file": str(filepath),
        "file_size_bytes": file_size,
        "mean_prompt_chars": sum(lengths) / len(lengths),
        "median_prompt_chars": sorted(lengths)[len(lengths) // 2],
        "min_prompt_chars": min(lengths),
        "max_prompt_chars": max(lengths),
        "total_chars": sum(lengths),
        "unique_prompts": unique_prompts,
        "exact_duplicate_pct": (1 - unique_prompts / len(prompts)) * 100,
        "json_field_used": json_field or "auto-detected",
        "dataset_type": "real",
    }

    print(f"  Loaded {len(prompts):,} prompts ({unique_prompts:,} unique)")
    print(f"  Char lengths: mean={metadata['mean_prompt_chars']:.0f}, "
          f"median={metadata['median_prompt_chars']}, "
          f"range=[{metadata['min_prompt_chars']}, {metadata['max_prompt_chars']}]")
    print(f"  Exact duplicates: {metadata['exact_duplicate_pct']:.1f}%")

    return prompts, metadata


def _load_json_file(filepath: Path) -> Any:
    """Load JSON or JSONL file."""
    suffix = filepath.suffix.lower()

    # Try JSONL first (one JSON object per line)
    if suffix in ('.jsonl', '.ndjson'):
        return _load_jsonl(filepath)

    # Try standard JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        # Might be JSONL with .json extension
        try:
            return _load_jsonl(filepath)
        except Exception:
            raise ValueError(f"Could not parse {filepath} as JSON or JSONL")


def _load_jsonl(filepath: Path) -> List[Dict]:
    """Load JSON Lines file."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                if line_num <= 3:
                    raise  # First few lines should parse
                continue  # Skip malformed lines later
    return records


def _sample_keys(data: Any) -> List[str]:
    """Extract sample keys from data for error messages."""
    if isinstance(data, dict):
        return list(data.keys())[:10]
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return list(first.keys())[:10]
        return [f"(list of {type(first).__name__})"]
    return [f"(type: {type(data).__name__})"]


def _extract_prompts(
    data: Any,
    json_field: Optional[str] = None,
    nested_field: Optional[str] = None,
) -> List[str]:
    """
    Extract prompt strings from various JSON structures.
    Auto-detects format if json_field is not specified.
    """
    prompts = []

    # If data is a dict with a single list field, unwrap it
    if isinstance(data, dict):
        if json_field and json_field in data:
            data = data[json_field]
        else:
            # Try common wrapper fields
            for wrapper_key in ['data', 'rows', 'samples', 'examples', 'prompts',
                                'dataset', 'records', 'items', 'instances',
                                'train', 'test', 'validation']:
                if wrapper_key in data and isinstance(data[wrapper_key], list):
                    print(f"  Auto-detected wrapper field: '{wrapper_key}'")
                    data = data[wrapper_key]
                    break
            else:
                # If still a dict, try to use all values
                if isinstance(data, dict):
                    # Maybe it's a dict of id -> prompt
                    data = list(data.values())

    # data should now be a list
    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}. Specify --json-field.")

    if not data:
        return []

    first = data[0]

    # Case 1: List of strings
    if isinstance(first, str):
        return data

    # Case 2: List of dicts
    if isinstance(first, dict):
        if json_field:
            # User specified the field
            return _extract_field(data, json_field, nested_field)

        # Auto-detect format
        keys = set(first.keys())

        # ShareGPT format: {"conversations": [{"from": "human", "value": "..."}]}
        if 'conversations' in keys:
            print("  Auto-detected format: ShareGPT")
            return _extract_sharegpt(data, nested_field)

        # OpenAI messages format: {"messages": [{"role": "user", "content": "..."}]}
        if 'messages' in keys:
            print("  Auto-detected format: OpenAI messages")
            return _extract_openai_messages(data)

        # Alpaca format: {"instruction": "...", "input": "...", "output": "..."}
        if 'instruction' in keys:
            print("  Auto-detected format: Alpaca")
            return _extract_alpaca(data)

        # Try common prompt field names
        prompt_fields = [
            'prompt', 'text', 'content', 'input', 'question',
            'query', 'instruction', 'message', 'body',
            'human', 'user', 'request', 'source',
            'context', 'sentence', 'utterance',
        ]
        for field in prompt_fields:
            if field in keys:
                values = [r[field] for r in data if field in r and isinstance(r[field], str)]
                if values:
                    print(f"  Auto-detected field: '{field}'")
                    return values

        # Try to concatenate all string fields
        print(f"  Warning: No standard field found. Keys: {list(keys)[:8]}")
        print(f"  Trying to concatenate all string values...")
        for record in data:
            text_parts = []
            for k, v in record.items():
                if isinstance(v, str) and len(v) >= 5:
                    text_parts.append(f"{k}: {v}")
            if text_parts:
                prompts.append("\n".join(text_parts))

    # Case 3: List of lists (e.g., conversation turns)
    elif isinstance(first, list):
        for conversation in data:
            parts = []
            for turn in conversation:
                if isinstance(turn, str):
                    parts.append(turn)
                elif isinstance(turn, dict):
                    for k in ['content', 'text', 'value', 'message']:
                        if k in turn:
                            parts.append(str(turn[k]))
                            break
            if parts:
                prompts.append("\n".join(parts))

    return prompts


def _extract_field(
    data: List[Dict],
    field: str,
    nested_field: Optional[str] = None,
) -> List[str]:
    """Extract a specific field from records, with optional nested extraction."""
    prompts = []
    for record in data:
        if field not in record:
            continue

        value = record[field]

        if isinstance(value, str):
            prompts.append(value)
        elif isinstance(value, list):
            # It's a list — could be conversation turns
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and nested_field and nested_field in item:
                    parts.append(str(item[nested_field]))
                elif isinstance(item, dict):
                    # Try common sub-fields
                    for k in ['content', 'text', 'value', 'message']:
                        if k in item:
                            parts.append(str(item[k]))
                            break
            if parts:
                prompts.append("\n".join(parts))
        elif isinstance(value, dict) and nested_field:
            if nested_field in value:
                prompts.append(str(value[nested_field]))
    return prompts


def _extract_sharegpt(data: List[Dict], nested_field: Optional[str] = None) -> List[str]:
    """Extract from ShareGPT format conversations."""
    prompts = []
    value_key = nested_field or 'value'

    for record in data:
        convs = record.get('conversations', [])
        if not convs:
            continue

        parts = []
        for turn in convs:
            role = turn.get('from', turn.get('role', 'unknown'))
            text = turn.get(value_key, turn.get('content', turn.get('text', '')))
            if text:
                parts.append(f"{role}: {text}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def _extract_openai_messages(data: List[Dict]) -> List[str]:
    """Extract from OpenAI messages format."""
    prompts = []
    for record in data:
        messages = record.get('messages', [])
        if not messages:
            continue

        parts = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                parts.append(f"{role}: {content}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def _extract_alpaca(data: List[Dict]) -> List[str]:
    """Extract from Alpaca format, combining instruction + input."""
    prompts = []
    for record in data:
        parts = []
        instruction = record.get('instruction', '')
        input_text = record.get('input', '')
        output_text = record.get('output', '')

        if instruction:
            parts.append(f"Instruction: {instruction}")
        if input_text:
            parts.append(f"Input: {input_text}")
        if output_text:
            parts.append(f"Output: {output_text}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def load_multiple_datasets(
    directory: str,
    json_field: Optional[str] = None,
    max_per_file: Optional[int] = None,
) -> Tuple[List[str], Dict]:
    """Load and combine prompts from all JSON/JSONL files in a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = sorted(
        glob.glob(str(directory / "*.json")) +
        glob.glob(str(directory / "*.jsonl")) +
        glob.glob(str(directory / "*.ndjson"))
    )

    if not files:
        raise FileNotFoundError(f"No JSON files found in {directory}")

    all_prompts = []
    file_counts = {}

    for fpath in files:
        try:
            prompts, _ = load_real_dataset(fpath, json_field=json_field, max_prompts=max_per_file)
            file_counts[os.path.basename(fpath)] = len(prompts)
            all_prompts.extend(prompts)
        except Exception as e:
            print(f"  Warning: Skipping {fpath}: {e}")

    if not all_prompts:
        raise ValueError(f"No prompts loaded from any file in {directory}")

    lengths = [len(p) for p in all_prompts]
    unique_prompts = len(set(all_prompts))

    metadata = {
        "n_prompts": len(all_prompts),
        "source_directory": str(directory),
        "n_files": len(file_counts),
        "file_counts": file_counts,
        "mean_prompt_chars": sum(lengths) / len(lengths),
        "total_chars": sum(lengths),
        "unique_prompts": unique_prompts,
        "exact_duplicate_pct": (1 - unique_prompts / len(all_prompts)) * 100,
        "dataset_type": "real_multi",
    }

    print(f"\n  Combined: {len(all_prompts):,} prompts from {len(file_counts)} files")

    return all_prompts, metadata


def analyze_dataset_redundancy(prompts: List[str]) -> Dict:
    """
    Analyze the natural redundancy patterns in a real dataset.
    Returns detailed statistics useful for understanding compression potential.
    """
    from collections import Counter

    total_prompts = len(prompts)

    # Exact duplicate analysis
    prompt_counts = Counter(prompts)
    unique_count = len(prompt_counts)
    most_common = prompt_counts.most_common(10)

    # Prefix sharing analysis (common system prompts)
    prefix_lengths = [50, 100, 200, 500]
    prefix_sharing = {}
    for plen in prefix_lengths:
        prefixes = Counter(p[:plen] for p in prompts if len(p) >= plen)
        n_qualifying = sum(1 for p in prompts if len(p) >= plen)
        if prefixes:
            most_common_prefix = prefixes.most_common(1)[0]
            prefix_sharing[f"prefix_{plen}_chars"] = {
                "unique_prefixes": len(prefixes),
                "qualifying_prompts": n_qualifying,
                "most_common_count": most_common_prefix[1],
                "most_common_pct": most_common_prefix[1] / n_qualifying * 100 if n_qualifying else 0,
                "preview": most_common_prefix[0][:80] + "...",
            }

    # Line-level deduplication potential
    all_lines = []
    for p in prompts:
        all_lines.extend(p.split('\n'))
    all_lines = [l for l in all_lines if len(l.strip()) >= 5]
    line_counts = Counter(all_lines)
    total_lines = len(all_lines)
    unique_lines = len(line_counts)
    repeated_lines = sum(1 for c in line_counts.values() if c > 1)

    # Substring analysis (rough — check for common long substrings)
    # Use 100-char windows
    window_size = 100
    windows = Counter()
    for p in prompts[:500]:  # Sample for performance
        for i in range(0, len(p) - window_size + 1, 50):  # Step by 50
            windows[p[i:i + window_size]] += 1
    repeated_windows = sum(1 for c in windows.values() if c > 1)

    analysis = {
        "total_prompts": total_prompts,
        "unique_prompts": unique_count,
        "exact_duplicate_pct": (1 - unique_count / total_prompts) * 100 if total_prompts else 0,
        "most_duplicated": [
            {"count": count, "preview": text[:120] + ("..." if len(text) > 120 else "")}
            for text, count in most_common[:5]
        ],
        "prefix_sharing": prefix_sharing,
        "line_level": {
            "total_lines": total_lines,
            "unique_lines": unique_lines,
            "repeated_lines": repeated_lines,
            "line_reuse_pct": (1 - unique_lines / total_lines) * 100 if total_lines else 0,
        },
        "substring_windows": {
            "window_size": window_size,
            "total_windows_sampled": len(windows),
            "repeated_windows": repeated_windows,
            "repetition_pct": repeated_windows / len(windows) * 100 if windows else 0,
        },
    }

    return analysis


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
        "dataset_type": "synthetic",
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


def corpus_dedup_chunked(prompts: List[str], level: int = 15,
                          min_chunk: int = 128, max_chunk: int = 2048) -> Dict:
    """Corpus-level dedup with sub-component chunking."""
    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    marginal_costs = []
    for i, text in enumerate(prompts):
        segments = parser.parse_segments_chunked(
            text, min_chunk_bytes=min_chunk, max_chunk_bytes=max_chunk
        )
        result = store.store(f"P{i:06d}", text, segments)
        marginal_costs.append(result["marginal_bytes"])

        if i % 500 == 0:
            rebuilt, v = store.retrieve(f"P{i:06d}")
            assert v["exact_match"], f"Reconstruction failed at prompt {i}"

    stats = store.corpus_stats()
    store.close()

    return {
        "method": "corpus_dedup_chunked",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["corpus_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "unique_nodes": stats["n_unique_nodes"],
        "avg_reuse": stats["avg_refs_per_node"],
        "marginal_costs": marginal_costs,
        "chunk_config": {"min": min_chunk, "max": max_chunk},
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
    if "source" in metadata:
        print(f"  Source: {metadata['source']}")
    if "exact_dup_pct" in metadata:
        print(f"  Exact duplicates: {metadata['exact_dup_pct']:.1f}%")
    print(f"{'='*70}")

    results = {"experiment": name, "metadata": metadata, "methods": {}}

    t0 = time.time()

    # 1. Per-prompt Zstd
    print("  [1/5] Per-prompt Zstd...", end=" ", flush=True)
    t = time.time()
    r = baseline_zstd(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["zstd"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  ({r['time_s']:.2f}s)")

    # 2. Per-prompt Hybrid
    print("  [2/5] Per-prompt Hybrid...", end=" ", flush=True)
    t = time.time()
    r = baseline_hybrid(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["hybrid"] = r
    if "error" not in r:
        print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  ({r['time_s']:.2f}s)")
    else:
        print(f"skipped ({r['error']})")

    # 3. Zstd with dictionary
    print("  [3/5] Zstd + dictionary...", end=" ", flush=True)
    t = time.time()
    r = baseline_zstd_dictionary(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["zstd_dict"] = r
    if "error" not in r:
        print(f"{r['ratio_with_dict']:.2f}x  {r['savings_pct']:.1f}% "
              f"(dict overhead: {r['dictionary_size']:,} bytes)  ({r['time_s']:.2f}s)")
    else:
        print(f"skipped ({r['error']})")

    # 4. Corpus dedup (component-level)
    print("  [4/5] Corpus-level dedup...", end=" ", flush=True)
    t = time.time()
    r = corpus_dedup_method(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["corpus_dedup"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['unique_nodes']} nodes, {r['avg_reuse']:.1f}x reuse)  ({r['time_s']:.2f}s)")

    # 5. Corpus dedup with sub-component chunking
    print("  [5/5] Corpus dedup (chunked)...", end=" ", flush=True)
    t = time.time()
    r = corpus_dedup_chunked(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["corpus_dedup_chunked"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['unique_nodes']} nodes, {r['avg_reuse']:.1f}x reuse)  ({r['time_s']:.2f}s)")

    # Comparison table
    print(f"\n  {'Method':<30} {'Ratio':>8} {'Savings':>10} {'Stored':>14} {'Time':>8}")
    print(f"  {'-'*72}")
    for key, label in [("zstd", "Per-prompt Zstd"),
                        ("hybrid", "Per-prompt Hybrid"),
                        ("zstd_dict", "Zstd + Dictionary"),
                        ("corpus_dedup", "Corpus Dedup"),
                        ("corpus_dedup_chunked", "Corpus Dedup (chunked)")]:
        m = results["methods"].get(key, {})
        if "error" in m:
            continue
        ratio = m.get("ratio") or m.get("ratio_with_dict", 0)
        savings = m.get("savings_pct", 0)
        stored = m.get("total_compressed") or m.get("total_with_dict_overhead", 0)
        t_s = m.get("time_s", 0)
        print(f"  {label:<30} {ratio:>8.2f}x {savings:>9.1f}% {stored:>13,} {t_s:>7.1f}s")

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Full HPGCS evaluation with real dataset support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with synthetic data (default)
  python benchmark_full_evaluation.py --n 1000

  # Run with a real JSON dataset
  python benchmark_full_evaluation.py --real-data my_prompts.json

  # Specify which JSON field contains the prompts
  python benchmark_full_evaluation.py --real-data data.json --json-field prompt

  # ShareGPT format with custom value field
  python benchmark_full_evaluation.py --real-data sharegpt.json --json-field conversations --nested-field value

  # Load all JSON files from a directory
  python benchmark_full_evaluation.py --real-data-dir ./datasets/

  # Combine real and synthetic experiments
  python benchmark_full_evaluation.py --real-data data.json --include-synthetic

  # Only analyze dataset redundancy (no compression benchmarks)
  python benchmark_full_evaluation.py --real-data data.json --analyze-only

  # Limit number of prompts from real dataset
  python benchmark_full_evaluation.py --real-data huge_dataset.json --max-prompts 5000
        """
    )
    ap.add_argument("--n", type=int, default=1000,
                    help="Number of synthetic prompts to generate (default: 1000)")
    ap.add_argument("--real-data", type=str, default=None,
                    help="Path to a JSON/JSONL dataset file")
    ap.add_argument("--real-data-dir", type=str, default=None,
                    help="Path to directory containing JSON/JSONL files")
    ap.add_argument("--json-field", type=str, default=None,
                    help="JSON field containing prompt text (auto-detected if omitted)")
    ap.add_argument("--nested-field", type=str, default=None,
                    help="Nested field within list items (e.g., 'value' in ShareGPT)")
    ap.add_argument("--max-prompts", type=int, default=None,
                    help="Maximum number of prompts to load from real dataset")
    ap.add_argument("--include-synthetic", action="store_true",
                    help="Also run synthetic experiments when using --real-data")
    ap.add_argument("--analyze-only", action="store_true",
                    help="Only analyze dataset redundancy, skip compression benchmarks")
    ap.add_argument("--output", type=str, default="evaluation_results.json",
                    help="Output JSON file for results")
    ap.add_argument("--csv", type=str, default="scaling_results.csv",
                    help="Output CSV file for scaling data")
    args = ap.parse_args()

    all_results = []
    is_real_data_mode = args.real_data or args.real_data_dir

    # ═══════════════════════════════════════════════════════════════════
    # REAL DATA EXPERIMENTS
    # ═══════════════════════════════════════════════════════════════════

    if args.real_data:
        # Load the real dataset
        prompts, meta = load_real_dataset(
            args.real_data,
            json_field=args.json_field,
            nested_field=args.nested_field,
            max_prompts=args.max_prompts,
        )

        # Dataset redundancy analysis
        print(f"\n{'='*70}")
        print(f"  DATASET REDUNDANCY ANALYSIS")
        print(f"{'='*70}")

        analysis = analyze_dataset_redundancy(prompts)

        print(f"\n  Exact duplicates: {analysis['exact_duplicate_pct']:.1f}%")
        print(f"  Unique prompts: {analysis['unique_prompts']:,} / {analysis['total_prompts']:,}")

        if analysis['most_duplicated']:
            print(f"\n  Most duplicated prompts:")
            for i, item in enumerate(analysis['most_duplicated'][:5], 1):
                print(f"    {i}. ({item['count']}x) {item['preview']}")

        pl = analysis.get('prefix_sharing', {})
        if pl:
            print(f"\n  Prefix sharing analysis:")
            for key, info in pl.items():
                print(f"    {key}: {info['unique_prefixes']} unique, "
                      f"most common covers {info['most_common_pct']:.1f}% of prompts")

        ll = analysis.get('line_level', {})
        if ll:
            print(f"\n  Line-level reuse: {ll['line_reuse_pct']:.1f}% "
                  f"({ll['total_lines']:,} lines, {ll['unique_lines']:,} unique)")

        if args.analyze_only:
            # Save analysis and exit
            output = {"dataset_analysis": analysis, "metadata": meta}
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2, default=str)
            print(f"\n  Analysis saved to {args.output}")
            return

        # Run compression benchmarks on real data
        dataset_name = Path(args.real_data).stem
        all_results.append(run_experiment(
            f"Real: {dataset_name}", prompts, meta
        ))

        # Also run scaling analysis on real data
        print(f"\n{'='*70}")
        print(f"  SCALING ANALYSIS (Real Data: {dataset_name})")
        print(f"{'='*70}")

        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            csv_path = args.csv.replace('.csv', f'_real_{dataset_name}.csv')
            _save_scaling_csv(scaling, csv_path)

    elif args.real_data_dir:
        # Load from directory
        prompts, meta = load_multiple_datasets(
            args.real_data_dir,
            json_field=args.json_field,
            max_per_file=args.max_prompts,
        )

        if args.analyze_only:
            analysis = analyze_dataset_redundancy(prompts)
            output = {"dataset_analysis": analysis, "metadata": meta}
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2, default=str)
            print(f"\n  Analysis saved to {args.output}")
            return

        dir_name = Path(args.real_data_dir).name
        all_results.append(run_experiment(
            f"Real: {dir_name} (combined)", prompts, meta
        ))

        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            csv_path = args.csv.replace('.csv', f'_real_{dir_name}.csv')
            _save_scaling_csv(scaling, csv_path)

    # ═══════════════════════════════════════════════════════════════════
    # SYNTHETIC EXPERIMENTS (run by default, or with --include-synthetic)
    # ═══════════════════════════════════════════════════════════════════

    if not is_real_data_mode or args.include_synthetic:
        # ── Experiment 1: Standard (80% reuse) ────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=0.8)
        all_results.append(run_experiment("Synthetic: Standard (80% reuse)", prompts, meta))

        # ── Experiment 2: Full reuse (100%) ───────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=1.0)
        all_results.append(run_experiment("Synthetic: Full reuse (100%)", prompts, meta))

        # ── Experiment 3: Low reuse (10%) ─────────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=0.1, n_unique_systems=5)
        all_results.append(run_experiment("Synthetic: Low reuse (10%)", prompts, meta))

        # ── Experiment 4: ZERO reuse (worst case) ─────────────────────────
        prompts, meta = generate_zero_reuse_corpus(args.n)
        all_results.append(run_experiment("Synthetic: Zero reuse (worst case)", prompts, meta))

        # ── Experiment 5: Zero reuse with tools/context ───────────────────
        prompts_long_zero, meta_long_zero = generate_corpus(
            n_prompts=args.n,
            system_reuse=0.0,
            n_unique_systems=args.n,
            include_tools=0.4,
            include_context=0.3,
            tool_reuse=0.0,
            context_reuse=0.0,
            seed=99,
        )
        all_results.append(run_experiment(
            "Synthetic: Zero reuse + tools/context", prompts_long_zero, meta_long_zero
        ))

        # ── Scaling analysis on synthetic data ────────────────────────────
        print(f"\n{'='*70}")
        print(f"  SCALING ANALYSIS (Synthetic)")
        print(f"{'='*70}")

        prompts, _ = generate_corpus(args.n, system_reuse=0.8)
        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            _save_scaling_csv(scaling, args.csv)

    # ═══════════════════════════════════════════════════════════════════
    # SAVE & SUMMARIZE
    # ═══════════════════════════════════════════════════════════════════

    # Remove marginal_costs from JSON (too large)
    for r in all_results:
        for m in r["methods"].values():
            m.pop("marginal_costs", None)

    output = {
        "experiments": all_results,
        "scaling": scaling if 'scaling' in dir() else [],
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Full results saved to {args.output}")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SUMMARY ACROSS ALL EXPERIMENTS")
    print(f"{'='*70}")
    print(f"  {'Experiment':<40} {'Zstd':>7} {'Hybrid':>8} {'Dict':>7} {'Dedup':>7}")
    print(f"  {'-'*72}")
    for r in all_results:
        name = r["experiment"][:40]
        zr = r["methods"].get("zstd", {}).get("ratio", 0)
        hr = r["methods"].get("hybrid", {}).get("ratio", 0)
        dr = r["methods"].get("zstd_dict", {}).get("ratio_with_dict", 0)
        cr = r["methods"].get("corpus_dedup", {}).get("ratio", 0)
        print(f"  {name:<40} {zr:>7.2f}x {hr:>7.2f}x {dr:>7.2f}x {cr:>7.2f}x")

    # If real data was used, print additional comparison
    if is_real_data_mode:
        real_results = [r for r in all_results if r["metadata"].get("dataset_type") == "real"]
        if real_results:
            print(f"\n  {'─'*70}")
            print(f"  REAL DATA HIGHLIGHTS:")
            for r in real_results:
                dedup = r["methods"].get("corpus_dedup", {})
                zstd_r = r["methods"].get("zstd", {})
                if dedup and zstd_r and "ratio" in dedup and "ratio" in zstd_r:
                    improvement = (dedup["ratio"] / zstd_r["ratio"] - 1) * 100
                    print(f"    Corpus dedup achieves {dedup['ratio']:.2f}x compression")
                    print(f"    vs Zstd baseline {zstd_r['ratio']:.2f}x "
                          f"({'+' if improvement >= 0 else ''}{improvement:.1f}% {'better' if improvement >= 0 else 'worse'})")
                    if dedup.get("unique_nodes"):
                        print(f"    Deduplicated to {dedup['unique_nodes']} unique nodes "
                              f"with {dedup.get('avg_reuse', 0):.1f}x average reuse")


def _print_scaling_table(scaling: List[Dict]):
    """Print scaling analysis table."""
    if not scaling:
        return

    has_dict = "dict_ratio" in scaling[0]

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
        advantage = (1 - s['dedup_stored'] / s['zstd_stored']) * 100 if s['zstd_stored'] else 0
        line += f" {advantage:>13.1f}%"
        print(line)


def _save_scaling_csv(scaling: List[Dict], csv_path: str):
    """Save scaling data to CSV."""
    if not scaling:
        return
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scaling[0].keys())
        writer.writeheader()
        writer.writerows(scaling)
    print(f"\n  Scaling data saved to {csv_path}")


if __name__ == "__main__":
    main()