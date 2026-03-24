"""
Prompt Parser Module - HPGCS Component 1

Parses incoming prompts into structured components using rule-based segmentation.
Recognises common delimiter keywords used in LLM prompt construction.
"""

import re
from typing import Dict, List, Tuple, Optional

_DELIMITER_FINDER = re.compile(
    r"^((?:system|instruction|context|tool|assistant|user|human|question|answer)\s*:\s*)",
    re.IGNORECASE | re.MULTILINE,
)

_KEYWORD_TO_CTYPE = {
    "system": "system",
    "instruction": "instruction",
    "context": "context",
    "tool": "tool",
    "assistant": "assistant",
    "user": "user_query",
    "human": "human",
    "question": "question",
    "answer": "answer",
}



# Ordered list of (component_type, regex_pattern_for_delimiter)
_COMPONENT_RULES: List[Tuple[str, str]] = [
    ("system",      r"^system\s*:\s*"),
    ("instruction", r"^instruction\s*:\s*"),
    ("context",     r"^context\s*:\s*"),
    ("tool",        r"^tool\s*:\s*"),
    ("assistant",   r"^assistant\s*:\s*"),
    ("user_query",  r"^user\s*:\s*"),
    ("human",       r"^human\s*:\s*"),
    ("question",    r"^question\s*:\s*"),
    ("answer",      r"^answer\s*:\s*"),
]

# Pre-compile all patterns (case-insensitive, multiline so ^ anchors to each line)
_COMPILED_RULES: List[Tuple[str, re.Pattern]] = [
    (ctype, re.compile(pattern, re.IGNORECASE | re.MULTILINE))
    for ctype, pattern in _COMPONENT_RULES
]

# Single pattern that matches ANY delimiter (used for splitting)
_SPLIT_PATTERN = re.compile(
    r"(?=^(?:system|instruction|context|tool|assistant|user|human|question|answer)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)


class ParsedPrompt:
    """Container for a parsed prompt's structured components."""

    def __init__(self, components: Dict[str, str], raw_text: str):
        self.components: Dict[str, str] = components  # type -> content
        self.raw_text: str = raw_text
        self.has_structure: bool = len(components) > 1 or (
            len(components) == 1 and list(components.keys())[0] != "unstructured"
        )

    def __repr__(self) -> str:
        keys = list(self.components.keys())
        return f"ParsedPrompt(components={keys}, has_structure={self.has_structure})"

    def component_list(self) -> List[Tuple[str, str]]:
        """Return ordered (component_type, content) pairs."""
        return list(self.components.items())


class PromptParser:
    """
    Rule-based prompt parser.

    Splits a prompt string into labelled components based on well-known
    delimiter keywords (System:, User:, Instruction:, Context:, …).

    If no delimiters are found the entire text is returned as a single
    'unstructured' component.
    """

    def parse(self, text: str) -> ParsedPrompt:
        """
        Parse a prompt string into its structural components.

        Args:
            text: Raw prompt string.

        Returns:
            ParsedPrompt containing a dict mapping component_type → content.

        Example:
            >>> parser = PromptParser()
            >>> result = parser.parse("System: You are helpful\\nUser: What is AI?")
            >>> result.components
            {'system': 'You are helpful', 'user_query': 'What is AI?'}
        """
        if not text or not text.strip():
            return ParsedPrompt({"unstructured": ""}, text)

        segments = _SPLIT_PATTERN.split(text)
        segments = [s for s in segments if s.strip()]

        if not segments:
            return ParsedPrompt({"unstructured": text.strip()}, text)

        components: Dict[str, str] = {}
        unnamed_count = 0

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            matched = False
            for ctype, pattern in _COMPILED_RULES:
                m = pattern.match(segment)
                if m:
                    content = segment[m.end():].strip()
                    # Avoid key collision by appending suffix
                    key = ctype
                    suffix = 2
                    while key in components:
                        key = f"{ctype}_{suffix}"
                        suffix += 1
                    components[key] = content
                    matched = True
                    break

            if not matched:
                unnamed_count += 1
                key = "unstructured" if unnamed_count == 1 else f"unstructured_{unnamed_count}"
                components[key] = segment

        if not components:
            components = {"unstructured": text.strip()}

        return ParsedPrompt(components, text)

    def get_component_type(self, text: str) -> str:
        """
        Detect the type of a single-component text snippet.

        Returns the component type label or 'unstructured' if none matches.
        """
        for ctype, pattern in _COMPILED_RULES:
            if pattern.match(text.strip()):
                return ctype
        return "unstructured"

    def parse_batch(self, texts: List[str]) -> List[ParsedPrompt]:
        """Parse a list of prompts."""
        return [self.parse(t) for t in texts]

    def parse_segments(self, text: str) -> List[dict]:
        """
        Parse prompt into lossless-reconstructable segments.

        Unlike parse(), this method preserves exact delimiters and whitespace
        so that ''.join(segment values) == original text.

        Returns a list of segments, each being either:
            {"type": "literal", "text": "System: "}
                — delimiter / formatting text, stored inline per-prompt
            {"type": "ref", "content": "...", "ctype": "system"}
                — component content, deduplicated across corpus

        Invariant:
            ''.join(s["text"] if s["type"]=="literal" else s["content"]
                    for s in segments) == text
        """
        if not text:
            return [{"type": "ref", "content": "", "ctype": "unstructured"}]

        matches = list(_DELIMITER_FINDER.finditer(text))

        if not matches:
            # No role delimiters — entire text is one component
            return [{"type": "ref", "content": text, "ctype": "unstructured"}]

        segments: List[dict] = []

        # ── Preamble: any text before the first delimiter ──
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()]
            segments.append({
                "type": "ref",
                "content": preamble,
                "ctype": "unstructured",
            })

        # ── Process each delimited section ──
        for i, m in enumerate(matches):
            # The exact delimiter text (e.g. "System: ", "user:  ")
            segments.append({"type": "literal", "text": m.group(0)})

            # Determine component type from the keyword
            keyword = m.group(1).strip().rstrip(":").strip().lower()
            ctype = _KEYWORD_TO_CTYPE.get(keyword, "unstructured")

            # Content runs from end of delimiter to start of next delimiter
            content_start = m.end()
            content_end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )
            content = text[content_start:content_end]

            if content:  # skip empty (back-to-back delimiters)
                segments.append({
                    "type": "ref",
                    "content": content,
                    "ctype": ctype,
                })

        # ── Verify lossless reconstruction ──
        rebuilt = "".join(
            s["text"] if s["type"] == "literal" else s["content"]
            for s in segments
        )
        if rebuilt != text:
            # Fallback: store entire text as single unstructured node
            return [{"type": "ref", "content": text, "ctype": "unstructured"}]

        return segments
