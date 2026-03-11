"""
Residual Text Tokenizer - HPGCS Component 5

Converts residual (non-reusable) prompt text into token ID sequences using
tiktoken BPE tokenization, then packs the IDs into compact binary form.
"""

import struct
from typing import List, Tuple, Optional

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None  # type: ignore
    _TIKTOKEN_AVAILABLE = False


class ResidualTextTokenizer:
    """
    Tokenises text using tiktoken BPE and packs token IDs into binary.

    The binary format is:
        [1-byte flag: 0 = uint16, 1 = uint32][packed token IDs…]

    uint16 is used when all token IDs fit in [0, 65535]; otherwise uint32.

    Args:
        model: tiktoken encoding name (default: "cl100k_base").
    """

    def __init__(self, model: str = "cl100k_base"):
        if not _TIKTOKEN_AVAILABLE:
            raise ImportError("tiktoken is required: pip install tiktoken")
        self.model = model
        self._enc = tiktoken.get_encoding(model)

    # ------------------------------------------------------------------
    def tokenize(self, text: str) -> List[int]:
        """Convert text to a list of token IDs."""
        return list(self._enc.encode(text, disallowed_special=()))

    def detokenize(self, token_ids: List[int]) -> str:
        """Convert a list of token IDs back to text."""
        return self._enc.decode(token_ids)

    # ------------------------------------------------------------------
    def pack(self, token_ids: List[int]) -> bytes:
        """
        Pack a list of token IDs into compact binary bytes.

        Returns:
            bytes: [1-byte format flag][packed uint16 or uint32 token IDs]
        """
        if not token_ids:
            return struct.pack("B", 0)  # empty, uint16 flag

        max_id = max(token_ids)
        min_id = min(token_ids)
        use_u32 = max_id > 65535 or min_id < 0

        fmt_byte = 1 if use_u32 else 0
        fmt_char = "I" if use_u32 else "H"

        try:
            payload = struct.pack(f"{len(token_ids)}{fmt_char}", *token_ids)
        except (struct.error, OverflowError):
            # Safety fallback
            fmt_byte = 1
            payload = struct.pack(f"{len(token_ids)}I", *token_ids)

        return struct.pack("B", fmt_byte) + payload

    def unpack(self, data: bytes) -> List[int]:
        """
        Unpack binary-packed token IDs back to a list of ints.

        Args:
            data: bytes produced by pack().

        Returns:
            List of token IDs.
        """
        if len(data) < 1:
            raise ValueError("Invalid packed data: missing format byte")

        fmt_byte = struct.unpack("B", data[:1])[0]
        payload = data[1:]

        if fmt_byte == 1:
            if len(payload) % 4 != 0:
                raise ValueError("Corrupt data: uint32 payload not divisible by 4")
            return list(struct.unpack(f"{len(payload)//4}I", payload))
        else:
            if len(payload) % 2 != 0:
                raise ValueError("Corrupt data: uint16 payload not divisible by 2")
            return list(struct.unpack(f"{len(payload)//2}H", payload))

    # ------------------------------------------------------------------
    def encode(self, text: str) -> bytes:
        """Tokenize and pack in one step."""
        return self.pack(self.tokenize(text))

    def decode(self, data: bytes) -> str:
        """Unpack and detokenize in one step."""
        return self.detokenize(self.unpack(data))

    # ------------------------------------------------------------------
    def token_count(self, text: str) -> int:
        return len(self.tokenize(text))

    def compression_ratio(self, text: str) -> float:
        """Bytes in UTF-8 vs bytes in packed representation."""
        orig = len(text.encode("utf-8"))
        packed = len(self.encode(text))
        return orig / packed if packed else 0.0
