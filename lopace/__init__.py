"""
LoPace — Lossless Optimized Prompt Accurate Compression Engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Corpus-aware prompt compression for LLM workloads.

Core modules:
    PromptCompressor    – Multi-method per-prompt compression (zstd, lz4, brotli, etc.)
    PromptParser        – Structural segmentation into typed components
    CorpusStore         – Corpus-level component deduplication
    DeltaStore          – Delta compression via centroids + unified diffs

Author: Babul Bishwas (https://github.com/babul09)
Based on original LoPace by Aman Ulla
"""

from lopace.compressor import PromptCompressor, CompressionMethod
from lopace.parser import PromptParser, ParsedPrompt
from lopace.corpus_store import CorpusStore
from lopace.delta_store import DeltaStore

__all__ = [
    # Per-prompt compression
    "PromptCompressor",
    "CompressionMethod",
    # Structural parsing
    "PromptParser",
    "ParsedPrompt",
    # Corpus-level deduplication
    "CorpusStore",
    # Delta compression
    "DeltaStore",
]