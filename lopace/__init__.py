"""
LoPace - Lossless Optimized Prompt Accurate Compression Engine

Version 2 introduces the Hybrid Prompt Graph Compression System (HPGCS),
a multi-layer pipeline combining structural graph decomposition, semantic
clustering, BPE tokenization, neural encoding, and Zstandard compression.

Legacy API (v1) is preserved for backward compatibility.
"""

# ── Legacy v1 API ──────────────────────────────────────────────────────────
from .compressor import PromptCompressor, CompressionMethod

# ── HPGCS v2 API ──────────────────────────────────────────────────────────
from .hpgcs import HPGCS
from .parser import PromptParser, ParsedPrompt
from .graph import PromptGraphDecomposer, ReusableNodeManager, PromptNode, PromptGraph
from .clustering import VectorSimilarityClusterer, Cluster
from .tokenizer_module import ResidualTextTokenizer
from .encoder import LearnedCompressionEncoder
from .storage import GraphStorageDatabase, PromptRecord
from .reconstruction import PromptReconstructionEngine

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "2.0.0.dev0"

__all__ = [
    # v1
    "PromptCompressor",
    "CompressionMethod",
    # v2 – main entry point
    "HPGCS",
    # v2 – individual modules
    "PromptParser",
    "ParsedPrompt",
    "PromptGraphDecomposer",
    "ReusableNodeManager",
    "PromptNode",
    "PromptGraph",
    "VectorSimilarityClusterer",
    "Cluster",
    "ResidualTextTokenizer",
    "LearnedCompressionEncoder",
    "GraphStorageDatabase",
    "PromptRecord",
    "PromptReconstructionEngine",
]