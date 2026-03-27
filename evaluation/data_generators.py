import random
from typing import List, Dict, Tuple, Optional, Any

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

