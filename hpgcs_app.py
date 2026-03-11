"""
HPGCS - Hybrid Prompt Graph Compression System
Streamlit Application
"""

import hashlib
import json
import time
from typing import Dict, List, Optional

import streamlit as st

st.set_page_config(
    page_title="HPGCS – Hybrid Prompt Graph Compression",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-title {
    font-size: 2.4rem; font-weight: 700; color: #1565C0; line-height: 1.1;
}
.sub-title {
    font-size: 1.1rem; color: #555; margin-bottom: 1.5rem;
}
.pipeline-box {
    background: #F3F6FB; border-radius: 10px; padding: 1rem 1.4rem;
    border-left: 5px solid #1565C0; font-family: monospace;
    font-size: .85rem; line-height: 1.9;
}
.node-pill {
    display: inline-block; padding: .15rem .6rem; border-radius: 12px;
    font-size: .8rem; font-weight: 600; margin: .15rem .1rem;
}
.node-sys { background: #E3F2FD; color: #0D47A1; }
.node-usr { background: #E8F5E9; color: #1B5E20; }
.node-ins { background: #FFF8E1; color: #F57F17; }
.node-ctx { background: #FCE4EC; color: #880E4F; }
.node-oth { background: #F3E5F5; color: #4A148C; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🧠 HPGCS</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Hybrid Prompt Graph Compression System — '
    'Multi-layer LLM prompt storage compression</div>',
    unsafe_allow_html=True,
)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    tokenizer_model = st.selectbox(
        "Tokenizer Model",
        ["cl100k_base", "p50k_base", "r50k_base", "gpt2"],
        index=0,
        help="tiktoken BPE encoding model",
    )
    zstd_level = st.slider(
        "Zstd Compression Level", 1, 22, 15,
        help="Higher = better compression, slower speed",
    )
    cluster_threshold = st.slider(
        "Cluster Similarity Threshold", 0.50, 0.99, 0.80, step=0.01,
        help="Minimum cosine similarity to join an existing cluster",
    )

    st.markdown("---")
    st.markdown("### 🔖 Pipeline Stages")
    st.markdown("""
1. **Parser** — structural segmentation
2. **Graph Decomposer** — node extraction
3. **Node Manager** — deduplication
4. **Clusterer** — semantic grouping
5. **Tokenizer** — BPE token IDs
6. **Encoder** — latent representation
7. **Zstd** — byte-level compression
8. **Database** — graph storage
9. **Reconstructor** — exact rebuild
""")
    st.markdown("---")
    st.info(
        "**CR** = Original / Compressed\n\n"
        "**SS** = (1 − Comp/Orig) × 100\n\n"
        "**Hash Match** = SHA-256 verification\n\n"
        "**Exact Match** = char-by-char equality"
    )


# ─── Cached instances ─────────────────────────────────────────────────────────

@st.cache_resource
def get_hpgcs(tok_model: str, zstd_lvl: int, thresh: float):
    from lopace import HPGCS
    return HPGCS(
        db_path=":memory:",
        tokenizer_model=tok_model,
        zstd_level=zstd_lvl,
        cluster_threshold=thresh,
    )


@st.cache_data(max_entries=64)
def run_legacy(text: str, tok_model: str, zstd_lvl: int) -> dict:
    from lopace import PromptCompressor, CompressionMethod
    orig = len(text.encode())
    compressor = PromptCompressor(model=tok_model, zstd_level=zstd_lvl)
    out = {}
    for method in CompressionMethod:
        t0 = time.perf_counter()
        comp = compressor.compress(text, method)
        ct = time.perf_counter() - t0
        t1 = time.perf_counter()
        decomp = compressor.decompress(comp, method)
        dt = time.perf_counter() - t1
        cs = len(comp)
        out[method.value] = {
            "original_size": orig,
            "compressed_size": cs,
            "compression_ratio": orig / cs if cs else 0,
            "space_savings_pct": (1 - cs / orig) * 100 if orig else 0,
            "compress_time_ms": ct * 1000,
            "decompress_time_ms": dt * 1000,
            "exact_match": decomp == text,
        }
    return out


# ─── Helpers ──────────────────────────────────────────────────────────────────

def short_hash(text: str) -> str:
    h = hashlib.sha256(text.encode()).hexdigest()
    return f"{h[:8]}…{h[-8:]}"


def node_pill(label: str, ctype: str, preview: str) -> str:
    css = {
        "system": "node-sys", "instruction": "node-ins",
        "user_query": "node-usr", "context": "node-ctx",
    }.get(ctype.split("_")[0], "node-oth")
    safe = preview[:55].replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<span class="node-pill {css}" title="{safe}">'
        f'{label} <em style="font-weight:400">({ctype})</em></span>'
    )


# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab_pipeline, tab_compare, tab_arch = st.tabs([
    "🧠 HPGCS Pipeline",
    "📊 Method Comparison",
    "📖 Architecture",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HPGCS Pipeline
# ══════════════════════════════════════════════════════════════════════════════

with tab_pipeline:
    st.markdown("### 📝 Enter Prompts")
    st.caption(
        "Use **System:**, **Instruction:**, **User:**, **Context:** prefixes for structure. "
        "Separate multiple prompts with `---`."
    )

    DEFAULT = (
        "System: You are a helpful AI assistant designed to provide accurate, detailed, and helpful responses.\n"
        "Instruction: Answer concisely and clearly.\n"
        "User: Explain Maxwell's equations and their significance in physics.\n"
        "---\n"
        "System: You are a helpful AI assistant designed to provide accurate, detailed, and helpful responses.\n"
        "Instruction: Answer concisely and clearly.\n"
        "User: Describe Newton's second law of motion.\n"
        "---\n"
        "System: You are a coding assistant. Write clean, well-documented code.\n"
        "User: Write a Python function to compute the Fibonacci sequence recursively.\n"
        "---\n"
        "User: What is the capital of France?\n"
        "---\n"
        "System: You are a helpful AI assistant designed to provide accurate, detailed, and helpful responses.\n"
        "User: What are the main differences between supervised and unsupervised learning?"
    )

    prompt_input = st.text_area(
        "prompts", value=DEFAULT, height=260,
        label_visibility="collapsed", key="pipeline_input",
    )

    col_run, col_clr = st.columns([3, 1])
    with col_run:
        run_btn = st.button("🚀 Compress with HPGCS", type="primary", use_container_width=True)
    with col_clr:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("Cache cleared.")
            st.stop()

    if run_btn and prompt_input.strip():
        raw_prompts = [p.strip() for p in prompt_input.split("---") if p.strip()]
        if not raw_prompts:
            st.warning("Enter at least one prompt.")
            st.stop()

        hpgcs = get_hpgcs(tokenizer_model, zstd_level, cluster_threshold)
        prog = st.progress(0, text="Compressing…")
        results = []
        for i, txt in enumerate(raw_prompts):
            results.append(hpgcs.compress_and_reconstruct(txt))
            prog.progress((i + 1) / len(raw_prompts))
        prog.empty()

        # ── Global stats ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📊 Overall Statistics")
        db = hpgcs.database_stats()

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Prompts", f"{db['total_prompts']:,}")
        c2.metric("Overall CR", f"{db['overall_compression_ratio']:.2f}×")
        c3.metric("Space Saved", f"{db['overall_space_savings_pct']:.1f}%")
        c4.metric("Unique Nodes", f"{db['unique_nodes']:,}")
        c5.metric("Clusters", f"{db['num_clusters']:,}")

        r1, r2, r3 = st.columns(3)
        r1.metric("Reused Nodes", f"{db.get('graph_reused_nodes', 0):,}")
        r2.metric("Node Reuse Rate", f"{db.get('graph_reuse_rate_pct', 0):.1f}%")
        r3.metric("Bytes Saved (Reuse)", f"{db.get('graph_bytes_saved_by_reuse', 0):,} B")

        # ── Reusable node registry ────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 🔁 Reusable Node Registry")
        st.caption("Components stored once and referenced by any number of prompts.")
        nodes = hpgcs.list_nodes()
        if nodes:
            try:
                import pandas as pd
                st.dataframe(
                    pd.DataFrame([{
                        "Node ID": n["node_id"],
                        "Type": n["component_type"],
                        "Frequency": n["frequency"],
                        "Content Preview": n["content"][:80],
                        "Bytes": len(n["content"].encode()),
                    } for n in nodes]),
                    use_container_width=True, hide_index=True,
                )
            except ImportError:
                for n in nodes:
                    st.markdown(
                        f"**{n['node_id']}** ({n['component_type']}) "
                        f"×{n['frequency']} — {n['content'][:80]}"
                    )

        # ── Semantic clusters ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 🗂️ Semantic Clusters")
        st.caption(
            f"Backend: **{hpgcs.clusterer.backend}** | "
            f"Threshold: **{cluster_threshold:.2f}**"
        )
        cluster_rows = [{
            "Prompt ID": r["prompt_id"],
            "Cluster": r["cluster_id"],
            "Similarity": f"{r['cluster_similarity']:.3f}",
            "Preview": (r["components"][0][1] if r["components"] else "")[:70],
        } for r in results]
        try:
            import pandas as pd
            st.dataframe(pd.DataFrame(cluster_rows), use_container_width=True, hide_index=True)
        except ImportError:
            for row in cluster_rows:
                st.write(f"**{row['Prompt ID']}** → {row['Cluster']} (sim={row['Similarity']})")

        # ── Charts ────────────────────────────────────────────────────────
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            import pandas as pd

            st.markdown("---")
            st.markdown("## 📈 Visualisations")
            ids = [r["prompt_id"] for r in results]

            ch1, ch2 = st.columns(2)
            with ch1:
                fig = px.bar(
                    x=ids, y=[r["compression_ratio"] for r in results],
                    labels={"x": "Prompt ID", "y": "CR (×)"},
                    title="Compression Ratio per Prompt",
                    color=[r["compression_ratio"] for r in results],
                    color_continuous_scale="Blues",
                )
                fig.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

            with ch2:
                fig2 = go.Figure()
                fig2.add_bar(name="Original", x=ids,
                             y=[r["original_size_bytes"] for r in results],
                             marker_color="#1565C0")
                fig2.add_bar(name="Compressed", x=ids,
                             y=[r["compressed_size_bytes"] for r in results],
                             marker_color="#90CAF9")
                fig2.update_layout(title="Original vs Compressed Size (bytes)",
                                   barmode="group", yaxis_title="Bytes")
                st.plotly_chart(fig2, use_container_width=True)

            r0 = results[0]
            fig3 = go.Figure(go.Funnel(
                y=["UTF-8 Bytes", "BPE Packed Tokens", "Zstd Compressed"],
                x=[r0["original_size_bytes"], r0["packed_size_bytes"],
                   r0["compressed_size_bytes"]],
                textinfo="value+percent initial",
                marker={"color": ["#1565C0", "#1976D2", "#90CAF9"]},
            ))
            fig3.update_layout(
                title=f"Pipeline Size Reduction — Prompt {r0['prompt_id']}"
            )
            st.plotly_chart(fig3, use_container_width=True)

        except ImportError:
            st.info("Install `plotly` and `pandas` for charts.")

        # ── Per-prompt details ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 🔍 Per-Prompt Details")
        for idx, (txt, res) in enumerate(zip(raw_prompts, results)):
            icon = "✅" if res["exact_match"] else "❌"
            label = (
                f"Prompt #{idx+1} — {res['prompt_id']}  |  "
                f"CR {res['compression_ratio']:.2f}×  |  "
                f"Saved {res['space_savings_pct']:.1f}%  |  {icon}"
            )
            with st.expander(label, expanded=(idx == 0)):
                left, right = st.columns(2)
                with left:
                    st.markdown("**Original Prompt**")
                    st.text_area("o", value=txt, height=160, disabled=True,
                                 label_visibility="collapsed", key=f"o_{idx}")
                    st.caption(
                        f"{len(txt.encode()):,} bytes | "
                        f"{res['token_count']:,} tokens"
                    )
                with right:
                    st.markdown("**Reconstructed Prompt**")
                    st.text_area("r", value=res["reconstructed_text"] or "",
                                 height=160, disabled=True,
                                 label_visibility="collapsed", key=f"r_{idx}")
                    st.caption(
                        f"{icon} Exact Match | "
                        f"{res['compressed_size_bytes']:,} bytes stored"
                    )

                st.markdown("**Graph Nodes (Parsed Components)**")
                if res["components"]:
                    pills = " ".join(
                        node_pill(f"#{i+1}", ctype, content)
                        for i, (ctype, content) in enumerate(res["components"])
                    )
                    st.markdown(pills, unsafe_allow_html=True)

                st.markdown(
                    f"**Graph Path:** `{res['graph_path']}`  |  "
                    f"**Cluster:** `{res['cluster_id']}` "
                    f"(sim {res['cluster_similarity']:.3f})"
                )

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("CR", f"{res['compression_ratio']:.2f}×")
                m2.metric("Space Saved", f"{res['space_savings_pct']:.1f}%")
                m3.metric("Tokens", f"{res['token_count']:,}")
                m4.metric("Compress", f"{res['compression_time_s']*1000:.1f} ms")
                m5.metric("Decompress", f"{res['decompression_time_s']*1000:.1f} ms")

                h1, h2 = st.columns(2)
                with h1:
                    st.code(f"Original:      {short_hash(txt)}", language="text")
                with h2:
                    rebuilt = res["reconstructed_text"] or ""
                    st.code(f"Reconstructed: {short_hash(rebuilt)}", language="text")

                if res["hash_match"]:
                    st.success("✅ Hash Match — lossless reconstruction verified")
                else:
                    st.error("❌ Hash Mismatch")

        # ── Summary table ─────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📋 Compression Summary Table")
        try:
            import pandas as pd
            st.dataframe(
                pd.DataFrame([{
                    "ID": r["prompt_id"],
                    "Original (B)": r["original_size_bytes"],
                    "Compressed (B)": r["compressed_size_bytes"],
                    "CR (×)": round(r["compression_ratio"], 2),
                    "Savings (%)": round(r["space_savings_pct"], 1),
                    "Tokens": r["token_count"],
                    "Cluster": r["cluster_id"],
                    "Nodes": r["node_count"],
                    "Lossless": "✅" if r["exact_match"] else "❌",
                } for r in results]),
                use_container_width=True, hide_index=True,
            )
        except ImportError:
            for r in results:
                st.write(f"{r['prompt_id']}: CR={r['compression_ratio']:.2f}×")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Method Comparison
# ══════════════════════════════════════════════════════════════════════════════

with tab_compare:
    st.markdown("### 📊 HPGCS vs Legacy Methods")
    st.caption(
        "Compare the full HPGCS pipeline against Zstd-only, "
        "Token-only, and Hybrid (Token+Zstd) methods."
    )

    cmp_default = (
        "System: You are a helpful AI assistant designed to provide accurate, "
        "detailed, and helpful responses to user queries.\n"
        "Instruction: Answer concisely and clearly.\n"
        "User: Explain Maxwell's equations and their significance in modern physics."
    )
    cmp_input = st.text_area(
        "Prompt to compare", value=cmp_default, height=160, key="cmp_input"
    )
    cmp_btn = st.button("⚖️ Run Comparison", type="primary", use_container_width=True)

    if cmp_btn and cmp_input.strip():
        with st.spinner("Running all methods…"):
            hpgcs_inst = get_hpgcs(tokenizer_model, zstd_level, cluster_threshold)
            hres = hpgcs_inst.compress_and_reconstruct(cmp_input)
            legacy = run_legacy(cmp_input, tokenizer_model, zstd_level)

        orig = len(cmp_input.encode())
        rows = [
            ("HPGCS (full pipeline)", {
                "original_size": orig,
                "compressed_size":   hres["compressed_size_bytes"],
                "compression_ratio": hres["compression_ratio"],
                "space_savings_pct": hres["space_savings_pct"],
                "compress_time_ms":  hres["compression_time_s"] * 1000,
                "decompress_time_ms": hres["decompression_time_s"] * 1000,
                "exact_match": hres["exact_match"],
            }),
            ("Zstd only",             legacy.get("zstd", {})),
            ("Token (BPE)",            legacy.get("token", {})),
            ("Hybrid (Token + Zstd)", legacy.get("hybrid", {})),
        ]
        table = [{
            "Method":          name,
            "Original (B)":    d.get("original_size", orig),
            "Compressed (B)":  d.get("compressed_size", 0),
            "CR (×)":          round(d.get("compression_ratio", 0), 2),
            "Savings (%)":     round(d.get("space_savings_pct", 0), 1),
            "Compress (ms)":   round(d.get("compress_time_ms", 0), 2),
            "Decompress (ms)": round(d.get("decompress_time_ms", 0), 2),
            "Lossless":        "✅" if d.get("exact_match") else "❌",
        } for name, d in rows if d]

        try:
            import pandas as pd
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
        except ImportError:
            st.json(table)

        best = max(table, key=lambda r: r["CR (×)"])
        st.success(
            f"🏆 Best: **{best['Method']}** — "
            f"**{best['CR (×)']}×** ratio, {best['Savings (%)']}% savings"
        )

        try:
            import plotly.graph_objects as go
            colours = ["#1565C0", "#546E7A", "#558B2F", "#6A1B9A"]
            names = [r["Method"] for r in table]

            ch1, ch2 = st.columns(2)
            with ch1:
                fig = go.Figure(go.Bar(
                    x=names,
                    y=[r["CR (×)"] for r in table],
                    text=[f"{r['CR (×)']}×" for r in table],
                    textposition="outside",
                    marker_color=colours[:len(names)],
                ))
                fig.update_layout(title="Compression Ratio (×)", yaxis_title="CR",
                                  xaxis_tickangle=-20)
                st.plotly_chart(fig, use_container_width=True)

            with ch2:
                fig2 = go.Figure()
                fig2.add_bar(name="Compressed", x=names,
                             y=[r["Compressed (B)"] for r in table],
                             marker_color=colours[:len(names)])
                fig2.add_hline(y=orig, line_dash="dash", line_color="red",
                               annotation_text=f"Original ({orig} B)")
                fig2.update_layout(title="Compressed Size vs Original",
                                   yaxis_title="Bytes", xaxis_tickangle=-20)
                st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            st.info("Install `plotly` for charts.")

        st.markdown("---")
        st.markdown("### 🧠 HPGCS-Specific Details")
        d1, d2, d3 = st.columns(3)
        d1.metric("Graph Path", hres["graph_path"])
        d2.metric("Cluster", hres["cluster_id"])
        d3.metric("Tokens", f"{hres['token_count']:,}")
        st.markdown("**Parsed Components:**")
        for ctype, content in hres["components"]:
            st.markdown(f"- **{ctype}**: {content[:100]}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Architecture
# ══════════════════════════════════════════════════════════════════════════════

with tab_arch:
    st.markdown("## 🏗️ HPGCS Architecture")
    st.markdown(
        "The **Hybrid Prompt Graph Compression System** implements a 9-stage pipeline "
        "that combines structural, semantic, and statistical compression layers "
        "to significantly reduce LLM prompt storage requirements."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### Compression Pipeline")
        st.markdown(
            '<div class="pipeline-box">'
            "Prompt Input<br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 1</em><br>"
            "<strong>Prompt Parser</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 2</em><br>"
            "<strong>Prompt Graph Decomposer</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 3</em><br>"
            "<strong>Reusable Node Manager</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 4</em><br>"
            "<strong>Vector Similarity Clustering</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 5</em><br>"
            "<strong>Residual Text Tokenizer</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 6</em><br>"
            "<strong>Learned Compression Encoder</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 7</em><br>"
            "<strong>Zstandard Compression</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓ <em>Module 8</em><br>"
            "<strong>Graph Storage Database</strong>"
            "</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("### Reconstruction Pipeline")
        st.markdown(
            '<div class="pipeline-box">'
            "Query by Prompt ID<br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Load Graph Representation</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Resolve Reusable Nodes</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Decompress Stored Blob</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Decode / Unpack Tokens</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Detokenize to Text</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>Rebuild Original Prompt</strong><br>"
            "&nbsp;&nbsp;&nbsp;↓<br>"
            "<strong>SHA-256 Verification</strong>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 📦 Technology Stack")
    tech = {
        "Component":   ["Language", "Graph Processing", "Semantic Embeddings",
                        "Tokenizer", "Compression", "Storage", "Web UI"],
        "Technology":  ["Python 3.8+", "NetworkX",
                        "sentence-transformers / n-gram fallback",
                        "tiktoken (BPE)", "Zstandard (zstd)",
                        "SQLite / in-memory", "Streamlit"],
        "Module":      ["—", "lopace/graph.py", "lopace/clustering.py",
                        "lopace/tokenizer_module.py", "lopace/encoder.py",
                        "lopace/storage.py", "hpgcs_app.py"],
    }
    try:
        import pandas as pd
        st.dataframe(pd.DataFrame(tech), use_container_width=True, hide_index=True)
    except ImportError:
        for i in range(len(tech["Component"])):
            st.markdown(f"- **{tech['Component'][i]}**: {tech['Technology'][i]}")

    st.markdown("---")
    st.markdown("### 📐 Evaluation Formulas")
    st.latex(
        r"\text{Compression Ratio (CR)} = "
        r"\frac{S_{\text{original}}}{S_{\text{compressed}}}"
    )
    st.latex(
        r"\text{Space Savings (SS)} = "
        r"\left(1 - \frac{S_{\text{compressed}}}{S_{\text{original}}}\right) \times 100\%"
    )
    st.latex(
        r"E = \frac{1}{N}\sum_{i=1}^{N}\mathbf{1}(x_i \neq \hat{x}_i) "
        r"\quad \text{(reconstruction error, target = 0)}"
    )

    st.markdown("---")
    st.markdown("### 📊 Expected Compression Improvements")
    expected = {
        "Method":            ["Zstd only",
                              "Graph node deduplication",
                              "HPGCS full pipeline"],
        "Approx. Reduction": ["~4×", "~3–10×", "potentially 10–40×"],
        "Notes":             ["Byte-level entropy coding alone",
                              "Depends on prompt repetition rate",
                              "All five compression layers combined"],
    }
    try:
        import pandas as pd
        st.dataframe(pd.DataFrame(expected), use_container_width=True, hide_index=True)
    except ImportError:
        for row in zip(expected["Method"], expected["Approx. Reduction"], expected["Notes"]):
            st.markdown(f"- **{row[0]}**: {row[1]} — {row[2]}")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "HPGCS v2 · Hybrid Prompt Graph Compression System · "
    "LoPace – Lossless Optimized Prompt Accurate Compression Engine"
)
