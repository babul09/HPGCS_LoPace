import os
import sys

def get_block(lines, start, end):
    return "".join(lines[start-1:end])

def main():
    with open("benchmark_full_evaluation.py", "r", encoding="utf-8") as f:
        lines = f.readlines()

    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/__init__.py", "w") as f: f.write("")

    # 1. data_generators.py
    dg = """import random
from typing import List, Dict, Tuple, Optional, Any
""" + get_block(lines, 49, 238) + get_block(lines, 740, 846)
    with open("evaluation/data_generators.py", "w", encoding="utf-8") as f: f.write(dg)

    # 2. datasets.py
    ds = """import glob
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
""" + get_block(lines, 240, 738)
    with open("evaluation/datasets.py", "w", encoding="utf-8") as f: f.write(ds)

    # 3. baselines.py
    bl_imports = """import gzip
import brotli
import zstandard as zstd
import time
from typing import List, Dict, Tuple, Optional, Any

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore
from lopace.delta_store import DeltaStore
from lopace.adaptive_store import AdaptiveStore

try:
    _ZSTD = True
except ImportError:
    _ZSTD = False

"""
    bl = bl_imports + get_block(lines, 847, 1117)
    with open("evaluation/baselines.py", "w", encoding="utf-8") as f: f.write(bl)

    # 4. runner.py
    rn_imports = """import time
import csv
from typing import List, Dict, Tuple, Optional, Any
import zstandard as zstd

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore
from .baselines import (
    baseline_zstd, baseline_gzip, baseline_brotli, baseline_zstd_dictionary,
    baseline_hybrid, corpus_dedup_method, corpus_dedup_chunked,
    delta_compression_method, adaptive_routing_method
)

"""
    rn = rn_imports + get_block(lines, 1118, 1323) + get_block(lines, 1571, 1604)
    with open("evaluation/runner.py", "w", encoding="utf-8") as f: f.write(rn)

    # 5. Modify benchmark_full_evaluation.py
    new_main = get_block(lines, 1, 48) + """
from evaluation.data_generators import generate_corpus, generate_zero_reuse_corpus
from evaluation.datasets import load_real_dataset, load_multiple_datasets, analyze_dataset_redundancy
from evaluation.runner import run_experiment, scaling_analysis, _print_scaling_table, _save_scaling_csv

# Legacy compatibility
try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    _ZSTD = False

""" + get_block(lines, 1326, 1569) + get_block(lines, 1605, 1607)

    with open("benchmark_full_evaluation.py", "w", encoding="utf-8") as f: f.write(new_main)

    print("Successfully structured evaluations.")

if __name__ == "__main__":
    main()
