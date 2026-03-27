"""
Prompt Reconstruction Engine - HPGCS Component 8

Reverses the compression pipeline to recover the original prompt text from
a stored PromptRecord and the associated reusable node registry.

Reconstruction steps
--------------------
1. Load the PromptRecord from the database.
2. Parse the graph JSON to recover the ordered node ID path.
3. For each node ID that exists in the reusable node manager, retrieve its
   content directly.
4. For nodes NOT in the registry (i.e. unique / residual content), decompress
   the stored blob → unpack token IDs → detokenize back to text.
5. Reassemble component texts in graph order, inserting the original delimiters
   so the rebuilt prompt matches the input format.
"""

import json
import hashlib
import time
from typing import Dict, List, Optional, Tuple


class PromptReconstructionEngine:
    """
    Reconstructs original prompts from compressed records.

    Args:
        node_manager: ReusableNodeManager holding the shared node registry.
        tokenizer:    ResidualTextTokenizer used during compression.
        encoder:      LearnedCompressionEncoder used during compression.
    """

    def __init__(self, node_manager, tokenizer, encoder):
        self._nodes = node_manager
        self._tokenizer = tokenizer
        self._encoder = encoder

    # ------------------------------------------------------------------
    def reconstruct(self, record) -> Tuple[str, dict]:
        """
        Reconstruct the original prompt from a PromptRecord.

        Args:
            record: PromptRecord retrieved from GraphStorageDatabase.

        Returns:
            (reconstructed_text, verification_dict)

        The verification_dict contains:
            exact_match    – bool
            hash_match     – bool
            original_hash  – str (SHA-256 of stored original)
            rebuilt_hash   – str (SHA-256 of rebuilt text)
        """
        t0 = time.perf_counter()

        graph_data = json.loads(record.graph_json)
        node_ids: List[str] = graph_data["node_ids"]

        component_texts: List[Tuple[str, str]] = []  # (component_type, content)

        for nid in node_ids:
            node = self._nodes.get_by_id(nid)
            if node is not None:
                # Reusable node – retrieve content directly
                component_texts.append((node.component_type, node.content))
            else:
                # Residual / unique node – decompress from stored blob
                packed = self._encoder.decode(record.compressed_blob)
                text = self._tokenizer.decode(packed)
                # We don't know the component type for the residual, use 'unstructured'
                component_texts.append(("unstructured", text))

        reconstructed = self._assemble(component_texts)
        elapsed = time.perf_counter() - t0

        # Verification
        original_hash = hashlib.sha256(record.original_text.encode()).hexdigest()
        rebuilt_hash = hashlib.sha256(reconstructed.encode()).hexdigest()
        exact = reconstructed == record.original_text

        return reconstructed, {
            "exact_match": exact,
            "hash_match": original_hash == rebuilt_hash,
            "original_hash": original_hash,
            "rebuilt_hash": rebuilt_hash,
            "reconstruction_time_s": elapsed,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _assemble(components: List[Tuple[str, str]]) -> str:
        """
        Reassemble component texts back into a single prompt string.

        Structured components get their keyword prefix re-inserted.
        Unstructured components are joined with newlines.
        """
        # Map component type → display label
        _LABEL = {
            "system":       "System",
            "instruction":  "Instruction",
            "context":      "Context",
            "tool":         "Tool",
            "assistant":    "Assistant",
            "user_query":   "User",
            "human":        "Human",
            "question":     "Question",
            "answer":       "Answer",
        }

        parts: List[str] = []
        for ctype, content in components:
            base_type = ctype.split("_")[0]  # strip numeric suffix like _2
            label = _LABEL.get(base_type) or _LABEL.get(ctype)
            if label:
                parts.append(f"{label}: {content}")
            else:
                parts.append(content)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    def reconstruct_from_db(self, prompt_id: str, db) -> Tuple[Optional[str], dict]:
        """
        Convenience wrapper: fetch record from database then reconstruct.

        Args:
            prompt_id: ID of the prompt to retrieve.
            db:        GraphStorageDatabase instance.

        Returns:
            (reconstructed_text or None, verification_dict)
        """
        record = db.get_prompt(prompt_id)
        if record is None:
            return None, {"error": f"Prompt '{prompt_id}' not found in database"}
        return self.reconstruct(record)

    def batch_reconstruct(self, records: list) -> List[Tuple[str, dict]]:
        """Reconstruct multiple records."""
        return [self.reconstruct(r) for r in records]
