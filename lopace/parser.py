"""
Prompt Parser Module - HPGCS Component 1

Parses incoming prompts into structured components using rule-based segmentation.
Recognises common delimiter keywords used in LLM prompt construction.
"""

import re
from typing import Dict, List, Tuple, Optional


# ─── Delimiter detection for parse_segments ───────────────────────────────────

_DELIMITER_FINDER = re.compile(
    r"^((?:system|instruction|context|tool|assistant|user|human|question|answer|gpt)\s*:\s*)",
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
    "gpt": "assistant",
}

# ─── Component rules for parse() ─────────────────────────────────────────────

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
    ("assistant",   r"^gpt\s*:\s*"),
]

_COMPILED_RULES: List[Tuple[str, re.Pattern]] = [
    (ctype, re.compile(pattern, re.IGNORECASE | re.MULTILINE))
    for ctype, pattern in _COMPONENT_RULES
]

_SPLIT_PATTERN = re.compile(
    r"(?=^(?:system|instruction|context|tool|assistant|user|human|question|answer|gpt)\s*:)",
    re.IGNORECASE | re.MULTILINE,
)


class ParsedPrompt:
    """Container for a parsed prompt's structured components."""

    def __init__(self, components: Dict[str, str], raw_text: str):
        self.components = components
        self.raw_text = raw_text
        self.has_structure = len(components) > 1 or (
            len(components) == 1 and list(components.keys())[0] != "unstructured"
        )

    def __repr__(self) -> str:
        keys = list(self.components.keys())
        return f"ParsedPrompt(components={keys}, has_structure={self.has_structure})"

    def component_list(self) -> List[Tuple[str, str]]:
        return list(self.components.items())


class PromptParser:
    """
    Rule-based prompt parser.

    Splits a prompt string into labelled components based on well-known
    delimiter keywords (System:, User:, human:, gpt:, etc.).
    """

    def parse(self, text: str) -> ParsedPrompt:
        """Parse a prompt string into structural components."""
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
        for ctype, pattern in _COMPILED_RULES:
            if pattern.match(text.strip()):
                return ctype
        return "unstructured"

    def parse_batch(self, texts: List[str]) -> List[ParsedPrompt]:
        return [self.parse(t) for t in texts]

    def parse_segments(self, text: str) -> List[dict]:
        """
        Parse into lossless-reconstructable segments.

        Returns list of:
            {"type": "literal", "text": "System: "}
            {"type": "ref", "content": "...", "ctype": "system"}

        Invariant: concatenation of all values == original text.
        """
        if not text:
            return [{"type": "ref", "content": "", "ctype": "unstructured"}]

        matches = list(_DELIMITER_FINDER.finditer(text))

        if not matches:
            return [{"type": "ref", "content": text, "ctype": "unstructured"}]

        segments: List[dict] = []

        if matches[0].start() > 0:
            segments.append({
                "type": "ref",
                "content": text[:matches[0].start()],
                "ctype": "unstructured",
            })

        for i, m in enumerate(matches):
            segments.append({"type": "literal", "text": m.group(0)})

            keyword = m.group(1).strip().rstrip(":").strip().lower()
            ctype = _KEYWORD_TO_CTYPE.get(keyword, "unstructured")

            content_start = m.end()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[content_start:content_end]

            if content:
                segments.append({
                    "type": "ref",
                    "content": content,
                    "ctype": ctype,
                })

        rebuilt = "".join(
            s["text"] if s["type"] == "literal" else s["content"]
            for s in segments
        )
        if rebuilt != text:
            return [{"type": "ref", "content": text, "ctype": "unstructured"}]

        return segments

    def parse_segments_chunked(
        self,
        text: str,
        min_chunk_bytes: int = 128,
        max_chunk_bytes: int = 2048,
    ) -> List[dict]:
        """
        Parse into fine-grained lossless segments for corpus dedup.

        Two-level splitting:
          1. Split on role delimiters
          2. Further split large components at paragraph/line boundaries
        """
        segments = self.parse_segments(text)

        refined: List[dict] = []

        for seg in segments:
            if seg["type"] == "literal":
                refined.append(seg)
                continue

            content = seg["content"]
            ctype = seg.get("ctype", "unstructured")
            content_bytes = len(content.encode("utf-8"))

            if content_bytes <= max_chunk_bytes:
                refined.append(seg)
                continue

            sub_chunks = self._split_into_chunks(
                content, min_chunk_bytes, max_chunk_bytes
            )

            for chunk in sub_chunks:
                refined.append({
                    "type": "ref",
                    "content": chunk,
                    "ctype": ctype,
                })

        rebuilt = "".join(
            s["text"] if s["type"] == "literal" else s["content"]
            for s in refined
        )
        if rebuilt != text:
            return [{"type": "ref", "content": text, "ctype": "unstructured"}]

        return refined

    @staticmethod
    def _split_into_chunks(
        text: str, min_bytes: int = 128, max_bytes: int = 2048,
    ) -> List[str]:
        """Split text into chunks at natural boundaries."""
        if len(text.encode("utf-8")) <= max_bytes:
            return [text]

        chunks: List[str] = []

        # Try paragraph-level first
        parts = text.split("\n\n")

        current = ""
        for part in parts:
            candidate = current + ("\n\n" if current else "") + part
            if len(candidate.encode("utf-8")) > max_bytes and len(current.encode("utf-8")) >= min_bytes:
                chunks.append(current + "\n\n")
                current = part
            else:
                current = candidate

        if current:
            chunks.append(current)

        # If still one big chunk, try line-level
        if len(chunks) == 1 and len(chunks[0].encode("utf-8")) > max_bytes:
            chunks = []
            lines = text.split("\n")
            current = ""
            for line in lines:
                candidate = current + ("\n" if current else "") + line
                if len(candidate.encode("utf-8")) > max_bytes and len(current.encode("utf-8")) >= min_bytes:
                    chunks.append(current + "\n")
                    current = line
                else:
                    current = candidate
            if current:
                chunks.append(current)

        if "".join(chunks) != text:
            return [text]

        return chunks