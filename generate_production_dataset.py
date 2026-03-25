"""
Generate a realistic production-style prompt dataset.

Simulates a real LLM application where:
  - 3 different "apps" (chatbot, code assistant, RAG system)
  - Each app has a fixed system prompt used for ALL its users
  - Each app has shared tool descriptions
  - Users ask unique questions
  - Some RAG contexts are shared (popular documents)

This represents the ACTUAL use case for corpus dedup:
  a company running LLM apps at scale.
"""

import json
import random
from typing import List, Dict

random.seed(42)

# ─── App 1: Customer Support Bot ──────────────────────────────────────────────

APP1_SYSTEM = """You are a customer support assistant for TechCorp Inc.

Company Information:
- Founded: 2015
- Products: CloudSync Pro, DataFlow Enterprise, SecureVault
- Support hours: 24/7
- Escalation policy: If issue cannot be resolved in 3 messages, create a ticket
- Tone: Professional, empathetic, solution-oriented

You have access to the following knowledge:
- Product documentation and FAQs
- Known issues database (updated daily)
- Pricing and subscription tiers
- Return and refund policies

Always:
1. Greet the customer by name if available
2. Acknowledge their issue before providing solutions
3. Provide step-by-step instructions
4. Offer to escalate if the issue persists
5. End with a satisfaction check

Never:
- Share internal documentation links
- Discuss unreleased features
- Make promises about timelines without checking
- Provide competitor comparisons"""

APP1_TOOLS = """Available tools:
1. lookup_customer(email: str) -> dict
   Returns: {name, plan, account_age_days, open_tickets, last_contact}

2. search_knowledge_base(query: str, product: str = None) -> list[dict]
   Returns: [{title, content, relevance_score, article_id}]

3. create_ticket(customer_email: str, subject: str, priority: str, description: str) -> dict
   Returns: {ticket_id, estimated_response_time}
   Priority levels: low, medium, high, critical

4. check_service_status(service: str) -> dict
   Returns: {status, uptime_pct, last_incident, affected_regions}

5. process_refund(customer_email: str, amount: float, reason: str) -> dict
   Returns: {refund_id, status, estimated_processing_days}"""

APP1_QUERIES = [
    "I can't log into my CloudSync Pro account. I've tried resetting my password three times.",
    "How do I upgrade from the Basic plan to Enterprise?",
    "My data sync has been stuck at 45% for the past 2 hours.",
    "I want to cancel my subscription and get a refund for the remaining months.",
    "Is there a way to set up automatic backups with SecureVault?",
    "I'm getting an error code E-4502 when trying to export my data.",
    "Can I add more team members to my current plan without upgrading?",
    "The mobile app keeps crashing after the latest update.",
    "How do I integrate DataFlow Enterprise with our existing Salesforce setup?",
    "I accidentally deleted some important files. Can they be recovered?",
    "What's the difference between the Pro and Enterprise plans?",
    "My invoice shows a charge I don't recognize.",
    "How do I set up two-factor authentication?",
    "The API rate limits are too low for our usage. Can they be increased?",
    "I need to transfer my account to a different email address.",
]

# ─── App 2: Code Review Assistant ─────────────────────────────────────────────

APP2_SYSTEM = """You are a senior code review assistant specializing in Python, JavaScript, and Go.

Review Guidelines:
1. Security: Check for SQL injection, XSS, CSRF, insecure deserialization
2. Performance: Identify N+1 queries, unnecessary allocations, blocking I/O
3. Maintainability: Follow SOLID principles, DRY, proper naming conventions
4. Testing: Suggest test cases for edge cases and error paths
5. Documentation: Ensure public APIs have docstrings/JSDoc

Severity Levels:
- 🔴 Critical: Security vulnerabilities, data loss risks, crashes
- 🟡 Warning: Performance issues, code smells, missing error handling
- 🟢 Suggestion: Style improvements, refactoring opportunities, best practices

Output Format:
For each issue found:
  [SEVERITY] File:Line — Description
  Suggested fix: ...
  
End with a summary: X critical, Y warnings, Z suggestions"""

APP2_TOOLS = """Available tools:
1. analyze_code(code: str, language: str) -> dict
   Returns: {ast_valid, complexity_score, lines_of_code, functions, classes}

2. check_dependencies(requirements: str) -> list[dict]
   Returns: [{package, current_version, latest_version, vulnerabilities}]

3. run_linter(code: str, language: str, config: dict = None) -> list[dict]
   Returns: [{line, column, rule, message, severity}]

4. search_cve(package: str, version: str) -> list[dict]
   Returns: [{cve_id, severity, description, fixed_in_version}]

5. suggest_tests(code: str, language: str) -> list[str]
   Returns: list of suggested test case descriptions"""

APP2_QUERIES = [
    "Please review this Python function that handles user authentication.",
    "Check this JavaScript React component for any issues.",
    "Review my Go HTTP handler for the /api/users endpoint.",
    "Is this database query safe from SQL injection?",
    "Review this Dockerfile for security best practices.",
    "Check if this async Python code has any race conditions.",
    "Review this REST API error handling implementation.",
    "Is this password hashing implementation secure?",
    "Review this data pipeline for performance bottlenecks.",
    "Check this WebSocket implementation for memory leaks.",
]

# ─── App 3: RAG Research Assistant ────────────────────────────────────────────

APP3_SYSTEM = """You are a research assistant with access to a document knowledge base.

Instructions:
1. Always cite your sources using [DocID] format
2. If the retrieved documents don't contain the answer, say so explicitly
3. Synthesize information from multiple documents when possible
4. Distinguish between facts from documents and your own reasoning
5. Provide confidence levels: High (direct quote), Medium (inference), Low (extrapolation)

Response Structure:
- Direct Answer (1-2 sentences)
- Supporting Evidence (with citations)
- Additional Context (if relevant)
- Confidence Level and Limitations"""

APP3_CONTEXTS = [
    """Retrieved Documents:
[DOC-001] Title: Q3 2024 Financial Report
Revenue increased 23% YoY to $4.2B. Operating margin improved to 31%.
Key growth drivers: Cloud services (+45%), AI products (+120%), Enterprise contracts (+18%).
Customer retention rate: 94%. New enterprise customers: 847.
Guidance raised for Q4: expecting $4.5-4.7B revenue.

[DOC-002] Title: Market Analysis - Cloud Computing 2024
Global cloud market reached $600B in 2024. Top 3 providers control 65% of market.
Enterprise adoption rate: 78% (up from 62% in 2023). Multi-cloud strategies: 43% of enterprises.
Key trends: AI integration, edge computing, serverless architecture.""",

    """Retrieved Documents:
[DOC-003] Title: Employee Handbook - Remote Work Policy
All employees eligible for hybrid work (3 office / 2 remote days).
Equipment allowance: $2,000 for home office setup.
Core hours: 10 AM - 3 PM local time for meetings.
VPN required for all remote access. Monthly internet stipend: $75.

[DOC-004] Title: IT Security Policy v3.2
Password requirements: 16+ characters, complexity rules, 90-day rotation.
MFA required for all systems. Hardware keys for admin access.
Data classification: Public, Internal, Confidential, Restricted.
Incident reporting: security@company.com within 1 hour of discovery.""",

    """Retrieved Documents:
[DOC-005] Title: Product Roadmap 2025
Q1: AI-powered search (Project Atlas), Mobile app v3.0
Q2: Enterprise SSO integration, Advanced analytics dashboard
Q3: Multi-region deployment, Real-time collaboration features
Q4: API v3.0 launch, Developer marketplace

[DOC-006] Title: Competitive Analysis - January 2025
Competitor A: Launched AI features, pricing 15% lower, weaker enterprise support
Competitor B: Strong in APAC market, limited API capabilities
Our advantages: Enterprise reliability, comprehensive API, 24/7 support""",
]

APP3_QUERIES = [
    "What was our revenue growth in Q3 2024?",
    "Summarize the remote work policy for new employees.",
    "What are the key product launches planned for 2025?",
    "How does our cloud market share compare to competitors?",
    "What are the current password requirements?",
    "What's the guidance for Q4 revenue?",
    "How many new enterprise customers did we add?",
    "What is the equipment allowance for home office?",
    "When is the API v3.0 expected to launch?",
    "What are Competitor A's main advantages over us?",
    "What are the core hours for remote workers?",
    "How has enterprise cloud adoption changed since 2023?",
]


def generate_production_prompts(n_per_app: int = 500) -> List[str]:
    """Generate prompts simulating 3 production LLM apps."""
    prompts = []

    # App 1: Customer support (most repetitive — same system + tools for every user)
    for i in range(n_per_app):
        query = random.choice(APP1_QUERIES)
        if random.random() < 0.3:
            query += f" My account email is user{random.randint(1,10000)}@example.com."
        
        parts = [f"System: {APP1_SYSTEM}", f"Tool: {APP1_TOOLS}", f"User: {query}"]
        prompts.append("\n".join(parts))

    # App 2: Code review (same system + tools, unique code snippets)
    for i in range(n_per_app):
        query = random.choice(APP2_QUERIES)
        # Add a unique code snippet
        code_lines = random.randint(10, 30)
        query += f"\n\n```python\n# Code snippet {i}\n"
        query += "\n".join(f"    line_{j} = process(data[{j}])" for j in range(code_lines))
        query += "\n```"
        
        parts = [f"System: {APP2_SYSTEM}", f"Tool: {APP2_TOOLS}", f"User: {query}"]
        prompts.append("\n".join(parts))

    # App 3: RAG assistant (same system, shared contexts, unique queries)
    for i in range(n_per_app):
        query = random.choice(APP3_QUERIES)
        context = random.choice(APP3_CONTEXTS)  # contexts are reused!
        
        parts = [f"System: {APP3_SYSTEM}", f"Context: {context}", f"User: {query}"]
        prompts.append("\n".join(parts))

    random.shuffle(prompts)
    return prompts


if __name__ == "__main__":
    prompts = generate_production_prompts(n_per_app=500)
    
    # Save as simple JSON array
    with open("datasets/production_simulation.json", "w") as f:
        json.dump(prompts, f)
    
    total_chars = sum(len(p) for p in prompts)
    print(f"Generated {len(prompts)} prompts")
    print(f"Total: {total_chars:,} chars ({total_chars/1024/1024:.1f} MB)")
    print(f"Mean: {total_chars/len(prompts):.0f} chars/prompt")