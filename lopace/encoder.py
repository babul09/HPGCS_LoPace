"""
Learned Compression Encoder - HPGCS Component 6

Compresses packed token sequences into a latent representation and then
applies Zstandard compression for final byte-level entropy reduction.

Prototype design
----------------
The full architecture calls for an Embedding → Transformer → Latent pipeline.
For this prototype a lightweight approach is used:

  1. Token IDs are packed into binary (done by ResidualTextTokenizer).
  2. A fixed hash-based embedding computes a 64-dim latent vector
     (used for analysis / visualisation only).
  3. The **stored** compressed bytes are the Zstd-compressed packed tokens,
     which guarantees lossless reconstruction without a trained decoder.

This satisfies the architecture specification ("a simplified encoder may
initially be used") while correctly demonstrating every pipeline stage.
"""

import hashlib
import math
import struct
from typing import List, Tuple

try:
    import zstandard as zstd
    _ZSTD_AVAILABLE = True
except ImportError:
    zstd = None  # type: ignore
    _ZSTD_AVAILABLE = False

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

    Encodes packed token bytes into a Zstd-compressed blob.
    Also produces a quantized latent vector for analysis.

    Args:
        zstd_level: Zstandard compression level (1–22, default 15).
    """

    def __init__(self, zstd_level: int = 15):
        if not _ZSTD_AVAILABLE:
            raise ImportError("zstandard is required: pip install zstandard")
        if not (1 <= zstd_level <= 22):
            raise ValueError("zstd_level must be between 1 and 22")
        self.zstd_level = zstd_level

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
            - compressed_blob: Zstd-compressed token data (used for storage).
            - quantized_latent_bytes: Compact latent vector (for analysis).
        """
        # Step 1: Zstd compress the packed token data
        compressed_blob = zstd.compress(packed_tokens, level=self.zstd_level)

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
        return zstd.decompress(compressed_blob)

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
            "packed_size_bytes": len(packed_tokens),
            "compressed_size_bytes": len(compressed_blob),
            "zstd_ratio": len(packed_tokens) / len(compressed_blob) if compressed_blob else 0.0,
            "zstd_savings_pct": (
                (1 - len(compressed_blob) / len(packed_tokens)) * 100
                if packed_tokens else 0.0
            ),
        }
