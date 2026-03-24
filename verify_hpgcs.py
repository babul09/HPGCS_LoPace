"""Quick smoke test for the HPGCS pipeline."""
import sys

try:
    from lopace import (
        HPGCS, PromptParser, ReusableNodeManager, PromptGraphDecomposer,
        VectorSimilarityClusterer, ResidualTextTokenizer,
        LearnedCompressionEncoder, GraphStorageDatabase,
        PromptReconstructionEngine,
    )
    print("✓ All imports OK")

    hpgcs = HPGCS()
    text = "System: You are a helpful assistant.\nUser: What is 2+2?"
    result = hpgcs.compress_and_reconstruct(text)

    assert result["exact_match"], "Reconstruction mismatch!"
    assert result["hash_match"],  "Hash mismatch!"
    assert result["compression_ratio"] > 0, "Bad CR"

    print(f"✓ Pipeline OK")
    print(f"  Compression Ratio : {result['compression_ratio']:.2f}×")
    print(f"  Space Savings     : {result['space_savings_pct']:.1f}%")
    print(f"  Graph Path        : {result['graph_path']}")
    print(f"  Cluster           : {result['cluster_id']}")
    print(f"  Exact Match       : {result['exact_match']}")
    print(f"  Hash Match        : {result['hash_match']}")

    # Multi-prompt batch
    prompts = [
        "System: You are a helpful assistant.\nUser: Explain gravity.",
        "System: You are a helpful assistant.\nUser: Describe relativity.",
        "User: What is the capital of France?",
    ]
    results = hpgcs.compress_batch(prompts)
    print(f"\n✓ Batch compression: {len(results)} prompts")

    stats = hpgcs.database_stats()
    print(f"  Total prompts     : {stats['total_prompts']}")
    print(f"  Unique nodes      : {stats['unique_nodes']}")
    print(f"  Clusters          : {stats['num_clusters']}")
    print(f"  Overall CR        : {stats['overall_compression_ratio']:.2f}×")

    print("\n✓ All checks passed")

except Exception as e:
    print(f"✗ FAILED: {e}", file=sys.stderr)
    import traceback; traceback.print_exc()
    sys.exit(1)
