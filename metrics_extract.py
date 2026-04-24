import json, glob, os

PROJ = "/home/kelvin/HPGCS_LoPace"

print("=== REAL DATA ===")
for file in sorted(glob.glob(os.path.join(PROJ, "research_real_*.json"))):
    with open(file) as f:
        data = json.load(f)
    exps = data["experiments"]
    # last experiment should be the full-cap run
    exp = exps[-1]
    m = exp["methods"]
    cap = os.path.basename(file).replace("research_real_","").replace(".json","")

    zstd  = m.get("zstd",   {}).get("ratio", 0)
    brotli= m.get("brotli", {}).get("ratio", 0)
    dedup = m.get("corpus_dedup", {}).get("ratio", 0)
    ada   = m.get("adaptive", {}).get("ratio", 0)
    zd    = m.get("zstd_dict", {})
    di    = zd.get("ratio_with_dict", 0)      # isolated (includes dict overhead)
    dc    = zd.get("ratio_without_dict", 0)   # cached edge (payload only)
    print(f"  {cap:>6} prompts | Zstd={zstd:.2f}x | Brotli={brotli:.2f}x | Dedup={dedup:.2f}x | Adapt={ada:.2f}x | DictIsolated={di:.2f}x | DictCached={dc:.2f}x")

print("\n=== SYNTHETIC ===")
with open(os.path.join(PROJ, "research_synthetic.json")) as f:
    syn = json.load(f)
for exp in syn["experiments"]:
    m = exp["methods"]
    name  = exp["experiment"]
    zstd  = m.get("zstd",   {}).get("ratio", 0)
    brotli= m.get("brotli", {}).get("ratio", 0)
    dedup = m.get("corpus_dedup", {}).get("ratio", 0)
    ada   = m.get("adaptive", {}).get("ratio", 0)
    print(f"  {name:<40} | Zstd={zstd:.2f}x | Brotli={brotli:.2f}x | Dedup={dedup:.2f}x | Adapt={ada:.2f}x")

print("\n=== COMPLETE METHOD COMPARISON (real 5K) ===")
with open(os.path.join(PROJ, "research_real_5000.json")) as f:
    d5k = json.load(f)
m5 = d5k["experiments"][-1]["methods"]
for key in ["zstd", "gzip", "brotli", "cascade", "hybrid", "zstd_dict", "corpus_dedup", "corpus_dedup_chunked", "delta", "adaptive"]:
    r = m5.get(key, {})
    ratio = r.get("ratio", r.get("ratio_with_dict", 0))
    print(f"  {key:<25} {ratio:.2f}x")

print("\n=== SYNTHETIC 80% - complete ===")
m80 = next(e["methods"] for e in syn["experiments"] if "80" in e["experiment"])
for key in ["zstd", "brotli", "corpus_dedup", "adaptive"]:
    r = m80.get(key, {})
    print(f"  {key:<20} {r.get('ratio',0):.2f}x")
