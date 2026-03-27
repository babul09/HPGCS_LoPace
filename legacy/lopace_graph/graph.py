"""
Prompt Graph Decomposer & Reusable Node Manager - HPGCS Components 2 & 3

Converts parsed prompt components into a directed graph representation.
Maintains a registry of reusable nodes to avoid storing duplicate content.
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    nx = None
    _NX_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PromptNode:
    """A single node in the prompt graph."""
    node_id: str          # e.g. "SYS001"
    component_type: str   # e.g. "system", "user_query"
    content: str          # original text content
    content_hash: str     # SHA-256 of content (for deduplication)
    frequency: int = 1    # how many prompts reference this node

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "component_type": self.component_type,
            "content": self.content,
            "content_hash": self.content_hash,
            "frequency": self.frequency,
        }

    @staticmethod
    def from_dict(d: dict) -> "PromptNode":
        return PromptNode(**d)


@dataclass
class PromptGraph:
    """A graph representation of a single prompt."""
    prompt_id: str
    node_ids: List[str] = field(default_factory=list)   # ordered path
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (src, dst)

    def path_string(self) -> str:
        """Human-readable node path: SYS001 → INST002 → USR003"""
        return " → ".join(self.node_ids)

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "node_ids": self.node_ids,
            "edges": self.edges,
        }

    @staticmethod
    def from_dict(d: dict) -> "PromptGraph":
        g = PromptGraph(d["prompt_id"], d["node_ids"])
        g.edges = [tuple(e) for e in d["edges"]]
        return g


# ─────────────────────────────────────────────────────────────────────────────
# Reusable Node Manager
# ─────────────────────────────────────────────────────────────────────────────

class ReusableNodeManager:
    """
    Manages a registry of reusable prompt components.

    Nodes are deduplicated by content hash.  The same content always maps to
    the same node_id so it is stored once and referenced many times.

    Node IDs follow the convention: <TYPE_PREFIX><3-digit-counter>
    e.g. SYS001, USR042, CTX007
    """

    _PREFIX_MAP = {
        "system":       "SYS",
        "instruction":  "INS",
        "context":      "CTX",
        "tool":         "TOL",
        "assistant":    "AST",
        "user_query":   "USR",
        "human":        "HMN",
        "question":     "QST",
        "answer":       "ANS",
        "unstructured": "UNS",
    }

    def __init__(self):
        self._nodes: Dict[str, PromptNode] = {}         # node_id → PromptNode
        self._hash_to_id: Dict[str, str] = {}           # content_hash → node_id
        self._counters: Dict[str, int] = {}             # prefix → count

    # ------------------------------------------------------------------
    def _content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _next_id(self, component_type: str) -> str:
        prefix = self._PREFIX_MAP.get(component_type.split("_")[0], "UNS")
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:03d}"

    # ------------------------------------------------------------------
    def get_or_create(self, component_type: str, content: str) -> PromptNode:
        """
        Return an existing node for this content or create a new one.

        If the content already exists the node's frequency counter is
        incremented and the existing node is returned.
        """
        h = self._content_hash(content)
        if h in self._hash_to_id:
            node = self._nodes[self._hash_to_id[h]]
            node.frequency += 1
            return node

        node_id = self._next_id(component_type)
        node = PromptNode(
            node_id=node_id,
            component_type=component_type,
            content=content,
            content_hash=h,
        )
        self._nodes[node_id] = node
        self._hash_to_id[h] = node_id
        return node

    def get_by_id(self, node_id: str) -> Optional[PromptNode]:
        return self._nodes.get(node_id)

    def get_by_hash(self, content: str) -> Optional[PromptNode]:
        h = self._content_hash(content)
        nid = self._hash_to_id.get(h)
        return self._nodes.get(nid) if nid else None

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)

    @property
    def reuse_savings(self) -> int:
        """Total bytes saved by node reuse."""
        return sum(
            len(n.content.encode()) * (n.frequency - 1)
            for n in self._nodes.values()
            if n.frequency > 1
        )

    def all_nodes(self) -> List[PromptNode]:
        return list(self._nodes.values())

    def to_dict(self) -> dict:
        return {nid: n.to_dict() for nid, n in self._nodes.items()}

    def load_dict(self, data: dict):
        """Restore state from a serialised dict."""
        for nid, nd in data.items():
            node = PromptNode.from_dict(nd)
            self._nodes[nid] = node
            self._hash_to_id[node.content_hash] = nid
            prefix = nid[:3]
            num = int(nid[3:])
            self._counters[prefix] = max(self._counters.get(prefix, 0), num)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Graph Decomposer
# ─────────────────────────────────────────────────────────────────────────────

class PromptGraphDecomposer:
    """
    Converts a ParsedPrompt into a directed graph.

    Each component becomes a node (via ReusableNodeManager) and adjacent
    components are connected with a directed edge representing prompt flow.
    """

    def __init__(self, node_manager: ReusableNodeManager):
        self.node_manager = node_manager

    def decompose(self, parsed_prompt, prompt_id: str) -> PromptGraph:
        """
        Build a PromptGraph from a ParsedPrompt.

        Args:
            parsed_prompt: ParsedPrompt returned by PromptParser.
            prompt_id: Unique identifier for this prompt.

        Returns:
            PromptGraph with node path and edges.
        """
        graph = PromptGraph(prompt_id=prompt_id)
        components = parsed_prompt.component_list()

        for ctype, content in components:
            node = self.node_manager.get_or_create(ctype, content)
            graph.node_ids.append(node.node_id)

        # Create directed edges between adjacent nodes
        for i in range(len(graph.node_ids) - 1):
            graph.edges.append((graph.node_ids[i], graph.node_ids[i + 1]))

        return graph

    def to_networkx(self, graphs: List[PromptGraph]):
        """
        Build a NetworkX directed graph from a list of PromptGraphs.

        Requires networkx to be installed.

        Returns:
            nx.DiGraph with node and edge attributes.
        """
        if not _NX_AVAILABLE:
            raise ImportError("networkx is required: pip install networkx")

        G = nx.DiGraph()

        for pg in graphs:
            for nid in pg.node_ids:
                node = self.node_manager.get_by_id(nid)
                if node and not G.has_node(nid):
                    G.add_node(
                        nid,
                        label=nid,
                        component_type=node.component_type,
                        content_preview=node.content[:60],
                        frequency=node.frequency,
                    )

            for src, dst in pg.edges:
                if G.has_edge(src, dst):
                    G[src][dst]["weight"] = G[src][dst].get("weight", 1) + 1
                else:
                    G.add_edge(src, dst, weight=1)

        return G

    def graph_summary(self, graphs: List[PromptGraph]) -> dict:
        """Return summary statistics about the decomposed graphs."""
        all_node_ids = {nid for g in graphs for nid in g.node_ids}
        reused = [
            n for n in self.node_manager.all_nodes()
            if n.node_id in all_node_ids and n.frequency > 1
        ]
        return {
            "total_prompts": len(graphs),
            "unique_nodes": self.node_manager.total_nodes,
            "reused_nodes": len(reused),
            "reuse_rate_pct": (
                len(reused) / self.node_manager.total_nodes * 100
                if self.node_manager.total_nodes else 0
            ),
            "bytes_saved_by_reuse": self.node_manager.reuse_savings,
        }
