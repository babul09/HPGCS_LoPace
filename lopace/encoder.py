"""
Learned Compression Encoder - HPGCS Component 6

Compresses packed token sequences into a latent representation and then
applies a selectable base compressor for final byte-level entropy reduction.

Prototype design
----------------
The full architecture calls for an Embedding → Transformer → Latent pipeline.
For this prototype a lightweight approach is used:

  1. Token IDs are packed into binary (done by ResidualTextTokenizer).
  2. A fixed hash-based embedding computes a 64-dim latent vector
     (used for analysis / visualisation only).
    3. The **stored** compressed bytes are compressor-compressed packed tokens,
     which guarantees lossless reconstruction without a trained decoder.

This satisfies the architecture specification ("a simplified encoder may
initially be used") while correctly demonstrating every pipeline stage.
"""

import hashlib
import math
import struct
import gzip
import zlib
import lzma
from typing import List, Tuple

try:
    import zstandard as zstd
    _ZSTD_AVAILABLE = True
except ImportError:
    zstd = None  # type: ignore
    _ZSTD_AVAILABLE = False

try:
    import lz4.frame as lz4f
    _LZ4_AVAILABLE = True
except ImportError:
    lz4f = None  # type: ignore
    _LZ4_AVAILABLE = False

try:
    import brotli
    _BROTLI_AVAILABLE = True
except ImportError:
    brotli = None  # type: ignore
    _BROTLI_AVAILABLE = False

try:
    import snappy
    _SNAPPY_AVAILABLE = True
except ImportError:
    snappy = None  # type: ignore
    _SNAPPY_AVAILABLE = False

try:
    import numpy as np
    _NP_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    _NP_AVAILABLE = False


LATENT_DIM = 64   # dimension of the prototype latent vector


# ─── Lightweight hash-based embedding ────────────────────────────────────────

def _token_to_vec(token_id: int, dim: int = LATENT_DIM) -> List[float]:
    """
    Map a single token ID to a deterministic unit vector using a hash.

    This is a fixed (non-learned) embedding for prototype purposes.
    A real system would use a learned embedding table.
    """
    seed = hashlib.shake_256(str(token_id).encode()).digest(dim)
    vec = [(b / 127.5) - 1.0 for b in seed]  # scale to [-1, 1]
    # L2-normalise
    mag = math.sqrt(sum(v * v for v in vec))
    return [v / mag for v in vec] if mag > 0 else vec


def compute_latent_vector(token_ids: List[int]) -> List[float]:
    """
    Compute a mean-pooled latent vector over a sequence of token IDs.

    Returns a list of LATENT_DIM floats representing the prompt's
    compressed semantic signature.
    """
    if not token_ids:
        return [0.0] * LATENT_DIM

    if _NP_AVAILABLE:
        matrix = np.array([_token_to_vec(t) for t in token_ids], dtype=float)
        return matrix.mean(axis=0).tolist()
    else:
        # Pure Python mean pool
        vecs = [_token_to_vec(t) for t in token_ids]
        n = len(vecs)
        return [sum(v[i] for v in vecs) / n for i in range(LATENT_DIM)]


def quantize_latent(latent: List[float]) -> bytes:
    """
    Quantize a float32 latent vector to int8 bytes for compact storage.

    Maps each float from [-1, 1] → [-127, 127] as signed bytes.
    """
    clamped = [max(-1.0, min(1.0, v)) for v in latent]
    ints = [round(v * 127) for v in clamped]
    return struct.pack(f"{len(ints)}b", *ints)


def dequantize_latent(data: bytes) -> List[float]:
    """Reverse of quantize_latent."""
    ints = struct.unpack(f"{len(data)}b", data)
    return [v / 127.0 for v in ints]


# ─── Main encoder / decoder ───────────────────────────────────────────────────

class LearnedCompressionEncoder:
    """
    Prototype learned compression encoder.

    Encodes packed token bytes into a compressor-compressed blob.
    Also produces a quantized latent vector for analysis.

    Args:
        zstd_level: Zstandard compression level (1–22, default 15).
        base_compressor: Base backend for packed token compression.
    """

    @staticmethod
    def available_base_compressors() -> List[str]:
        compressors = []
        if _ZSTD_AVAILABLE:
            compressors.append("zstd")
        if _LZ4_AVAILABLE:
            compressors.append("lz4")
        if _BROTLI_AVAILABLE:
            compressors.append("brotli")
        if _SNAPPY_AVAILABLE:
            compressors.append("snappy")
        compressors.extend(["gzip", "deflate", "lzma"])
        return compressors

    def __init__(self, zstd_level: int = 15, base_compressor: str = "zstd"):
        if not (1 <= zstd_level <= 22):
            raise ValueError("zstd_level must be between 1 and 22")
        self.base_compressor = base_compressor.lower().strip()
        if self.base_compressor not in self.available_base_compressors():
            raise ValueError(
                f"Unsupported or unavailable base_compressor='{base_compressor}'. "
                f"Available: {self.available_base_compressors()}"
            )
        self.zstd_level = zstd_level

    def _level_9(self) -> int:
        return max(1, min(9, round(self.zstd_level * 9 / 22)))

    def _brotli_quality(self) -> int:
        return max(0, min(11, round(self.zstd_level * 11 / 22)))

    def _compress_payload(self, packed_tokens: bytes) -> bytes:
        backend = self.base_compressor
        if backend == "zstd":
            return zstd.compress(packed_tokens, level=self.zstd_level)
        if backend == "lz4":
            return lz4f.compress(packed_tokens)
        if backend == "brotli":
            return brotli.compress(packed_tokens, quality=self._brotli_quality())
        if backend == "snappy":
            return snappy.compress(packed_tokens)
        if backend == "gzip":
            return gzip.compress(packed_tokens, compresslevel=self._level_9())
        if backend == "deflate":
            return zlib.compress(packed_tokens, level=self._level_9())
        if backend == "lzma":
            preset = max(0, min(9, round(self.zstd_level * 9 / 22)))
            return lzma.compress(packed_tokens, preset=preset)
        raise ValueError(f"Unsupported compressor backend: {backend}")

    def _decompress_payload(self, compressed_blob: bytes) -> bytes:
        backend = self.base_compressor
        if backend == "zstd":
            return zstd.decompress(compressed_blob)
        if backend == "lz4":
            return lz4f.decompress(compressed_blob)
        if backend == "brotli":
            return brotli.decompress(compressed_blob)
        if backend == "snappy":
            return snappy.decompress(compressed_blob)
        if backend == "gzip":
            return gzip.decompress(compressed_blob)
        if backend == "deflate":
            return zlib.decompress(compressed_blob)
        if backend == "lzma":
            return lzma.decompress(compressed_blob)
        raise ValueError(f"Unsupported compressor backend: {backend}")

    # ------------------------------------------------------------------
    def encode(
        self, packed_tokens: bytes, token_ids: List[int]
    ) -> Tuple[bytes, bytes]:
        """
        Encode packed token bytes into a compressed blob.

        Args:
            packed_tokens: Binary-packed token IDs (from ResidualTextTokenizer).
            token_ids: Original token ID list (for latent vector computation).

        Returns:
            (compressed_blob, quantized_latent_bytes)
            - compressed_blob: Compressed token data (used for storage).
            - quantized_latent_bytes: Compact latent vector (for analysis).
        """
        # Step 1: Compress the packed token data with selected backend
        compressed_blob = self._compress_payload(packed_tokens)

        # Step 2: Compute prototype latent vector
        latent = compute_latent_vector(token_ids)
        quantized_latent = quantize_latent(latent)

        return compressed_blob, quantized_latent

    def decode(self, compressed_blob: bytes) -> bytes:
        """
        Decompress a compressed blob back to packed token bytes.

        Args:
            compressed_blob: Bytes produced by encode().

        Returns:
            Packed token bytes (pass to ResidualTextTokenizer.decode()).
        """
        return self._decompress_payload(compressed_blob)

    # ------------------------------------------------------------------
    def latent_vector_from_blob(self, compressed_blob: bytes) -> List[float]:
        """
        Re-derive the latent vector from a stored compressed blob.
        (Convenience for reconstruction analysis.)
        """
        try:
            from .tokenizer_module import ResidualTextTokenizer
            tok = ResidualTextTokenizer()
            packed = self.decode(compressed_blob)
            token_ids = tok.unpack(packed)
            return compute_latent_vector(token_ids)
        except Exception:
            return [0.0] * LATENT_DIM

    def compression_stats(self, packed_tokens: bytes, compressed_blob: bytes) -> dict:
        return {
            "base_compressor": self.base_compressor,
            "packed_size_bytes": len(packed_tokens),
            "compressed_size_bytes": len(compressed_blob),
            "compression_ratio": len(packed_tokens) / len(compressed_blob) if compressed_blob else 0.0,
            "compression_savings_pct": (
                (1 - len(compressed_blob) / len(packed_tokens)) * 100
                if packed_tokens else 0.0
            ),
        }
