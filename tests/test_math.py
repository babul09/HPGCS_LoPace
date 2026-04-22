import pytest
import hashlib
from lopace.delta_store import _fast_similarity, _compute_delta, _apply_delta
from lopace.corpus_store import CorpusStore
import zstandard as zstd

def test_zstd_hashing_determinism():
    """Verify that multiple sequential calls to encode exactly yield the same deterministic hash limit limits."""
    text1 = "This is a prompt sequence."
    text2 = "This is a prompt sequence."
    cctx = zstd.ZstdCompressor(level=15)
    bytes1 = cctx.compress(text1.encode("utf-8"))
    bytes2 = cctx.compress(text2.encode("utf-8"))
    assert bytes1 == bytes2
    hash1 = hashlib.sha256(bytes1).hexdigest()
    hash2 = hashlib.sha256(bytes2).hexdigest()
    assert hash1 == hash2

def test_fast_similarity_threshold():
    """Test line-level jaccard similarities return explicit boundaries predictably."""
    text_a = "Line 1\nLine 2\nLine 3"
    text_b = "Line 1\nLine 2\nLine 4"
    text_c = "Completely\ndifferent\nstructure"

    sim_ab = _fast_similarity(text_a, text_b)
    sim_ac = _fast_similarity(text_a, text_c)

    assert sim_ab > 0.4  # High overlap
    assert sim_ac == 0.0 # No overlap

def test_delta_diff_logic():
    """Verify standard Delta storage correctly applies backward hunks."""
    source = "I am a helpful assistant.\nPlease list objects.\nThank you."
    target = "I am a helpful assistant.\nPlease describe the sky.\nThank you."
    delta = _compute_delta(source, target)
    resolved = _apply_delta(source, delta)
    assert resolved == target
