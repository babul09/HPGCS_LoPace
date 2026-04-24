import json

# Inspect structure
d = json.load(open('research_real_200.json'))
print("Top-level keys:", list(d.keys()))
exps = d.get('experiments', d)
if isinstance(exps, list):
    exp = exps[-1]
elif isinstance(exps, dict):
    exp = exps
print("Experiment keys:", list(exp.keys()))
print("Methods keys:", list(exp['methods'].keys()))
zd = exp['methods'].get('zstd_dict', {})
print("zstd_dict keys:", list(zd.keys()))
print("zstd_dict sample:", {k: zd[k] for k in list(zd.keys())[:5]})
