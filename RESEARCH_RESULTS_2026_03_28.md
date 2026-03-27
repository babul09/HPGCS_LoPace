# HPGCS Research Results (Synthetic + Real)

- **Generated:** 2026-03-28
- **Real-data max prompts evaluated:** 200, 1000, 2000, 5000
- **Synthetic source:** `research_results_2026_03_28.json`

## Evaluation Scope

- Baselines: Zstd, gzip/DEFLATE sweep (L1/L6/L9), Brotli sweep (Q1/Q5/Q9/Q11), hybrid cascades (Brotli→Zstd, Zstd→LZ4HC), Hybrid BPE+Zstd, Zstd dictionary
- Corpus methods: Corpus Dedup, Chunked Corpus Dedup, Delta Compression
- Meta-selector: Adaptive Router (best ratio from measured methods)

## Real Data Summary Across Prompt Caps

| Max Prompts | Loaded Prompts | Zstd | Gzip | Brotli | Cascade | Hybrid | Zstd+Dict | Dedup | Adaptive | Adaptive Strategy |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 200 | 200 | 3.07x | 3.01x | 3.85x | 3.82x | 3.45x | 2.67x | 1.96x | 3.85x | brotli |
| 1000 | 1,000 | 3.14x | 3.05x | 3.90x | 3.88x | 3.53x | 3.67x | 2.00x | 3.90x | brotli |
| 2000 | 2,000 | 3.21x | 3.14x | 4.00x | 3.97x | 3.61x | 3.88x | 2.04x | 4.00x | brotli |
| 5000 | 5,000 | 3.22x | 3.15x | 4.00x | 3.98x | 3.60x | 3.99x | 2.03x | 4.00x | brotli |

## Experiment: Real (max-prompts=200)

- **Prompts:** 200
- **Mean chars/prompt:** 6240.6
- **Total chars:** 1,248,123
- **Exact duplicates:** 0.0%

### Method Results

| Method | Stored Bytes | Ratio | Savings | Time (s) | Notes |
|---|---:|---:|---:|---:|---|
| Per-prompt Zstd | 407,434 | 3.07x | 67.4% | 0.09 |  |
| Gzip/DEFLATE (best level) | 415,102 | 3.01x | 66.8% | 0.01 | best level L6 |
| Brotli (best quality) | 325,093 | 3.85x | 74.0% | 0.98 | best quality Q11 |
| Hybrid Cascade (best) | 327,085 | 3.82x | 73.8% | 1.00 | brotli11_to_zstd15 |
| Per-prompt Hybrid | 361,981 | 3.45x | 71.0% | 2.98 |  |
| Zstd + Dictionary | 337,335 | 2.67x | 62.5% | 0.16 | no-overhead ratio 3.71x; dict 131,072 B |
| Corpus Dedup | 636,747 | 1.96x | 49.1% | 0.14 |  |
| Corpus Dedup (chunked) | 663,836 | 1.88x | 46.9% | 0.13 |  |
| Delta Compression | 407,434 | 3.07x | 67.4% | 0.23 |  |
| Adaptive Router | 325,093 | 3.85x | 74.0% | 0.00 | selected brotli |

## Experiment: Real (max-prompts=1000)

- **Prompts:** 1,000
- **Mean chars/prompt:** 6772.6
- **Total chars:** 6,772,602
- **Exact duplicates:** 0.1%

### Method Results

| Method | Stored Bytes | Ratio | Savings | Time (s) | Notes |
|---|---:|---:|---:|---:|---|
| Per-prompt Zstd | 2,160,259 | 3.14x | 68.2% | 0.46 |  |
| Gzip/DEFLATE (best level) | 2,221,682 | 3.05x | 67.3% | 0.06 | best level L6 |
| Brotli (best quality) | 1,740,462 | 3.90x | 74.3% | 5.57 | best quality Q11 |
| Hybrid Cascade (best) | 1,750,429 | 3.88x | 74.2% | 6.02 | brotli11_to_zstd15 |
| Per-prompt Hybrid | 1,923,372 | 3.53x | 71.7% | 13.58 |  |
| Zstd + Dictionary | 1,718,372 | 3.67x | 72.7% | 0.98 | no-overhead ratio 3.95x; dict 131,072 B |
| Corpus Dedup | 3,387,470 | 2.00x | 50.1% | 0.73 |  |
| Corpus Dedup (chunked) | 3,501,647 | 1.94x | 48.4% | 0.75 |  |
| Delta Compression | 2,160,259 | 3.14x | 68.2% | 1.07 |  |
| Adaptive Router | 1,740,462 | 3.90x | 74.3% | 0.00 | selected brotli |

## Experiment: Real (max-prompts=2000)

- **Prompts:** 2,000
- **Mean chars/prompt:** 6704.6
- **Total chars:** 13,409,152
- **Exact duplicates:** 0.8%

### Method Results

| Method | Stored Bytes | Ratio | Savings | Time (s) | Notes |
|---|---:|---:|---:|---:|---|
| Per-prompt Zstd | 4,183,600 | 3.21x | 68.9% | 1.03 |  |
| Gzip/DEFLATE (best level) | 4,284,780 | 3.14x | 68.1% | 0.13 | best level L6 |
| Brotli (best quality) | 3,360,638 | 4.00x | 75.0% | 10.25 | best quality Q11 |
| Hybrid Cascade (best) | 3,380,575 | 3.97x | 74.8% | 10.59 | brotli11_to_zstd15 |
| Per-prompt Hybrid | 3,725,710 | 3.61x | 72.3% | 24.10 |  |
| Zstd + Dictionary | 3,334,466 | 3.88x | 74.2% | 1.33 | no-overhead ratio 4.03x; dict 131,072 B |
| Corpus Dedup | 6,590,142 | 2.04x | 50.9% | 1.09 |  |
| Corpus Dedup (chunked) | 6,801,559 | 1.98x | 49.4% | 1.08 |  |
| Delta Compression | 4,184,496 | 3.21x | 68.9% | 2.01 |  |
| Adaptive Router | 3,360,638 | 4.00x | 75.0% | 0.00 | selected brotli |

## Experiment: Real (max-prompts=5000)

- **Prompts:** 5,000
- **Mean chars/prompt:** 6605.8
- **Total chars:** 33,029,238
- **Exact duplicates:** 1.0%

### Method Results

| Method | Stored Bytes | Ratio | Savings | Time (s) | Notes |
|---|---:|---:|---:|---:|---|
| Per-prompt Zstd | 10,280,176 | 3.22x | 68.9% | 2.33 |  |
| Gzip/DEFLATE (best level) | 10,502,673 | 3.15x | 68.3% | 0.27 | best level L6 |
| Brotli (best quality) | 8,272,387 | 4.00x | 75.0% | 25.08 | best quality Q11 |
| Hybrid Cascade (best) | 8,322,222 | 3.98x | 74.9% | 25.09 | brotli11_to_zstd15 |
| Per-prompt Hybrid | 9,199,476 | 3.60x | 72.2% | 60.29 |  |
| Zstd + Dictionary | 8,171,808 | 3.99x | 74.9% | 3.29 | no-overhead ratio 4.05x; dict 131,072 B |
| Corpus Dedup | 16,326,238 | 2.03x | 50.7% | 2.82 |  |
| Corpus Dedup (chunked) | 16,768,337 | 1.97x | 49.3% | 2.96 |  |
| Delta Compression | 10,283,221 | 3.22x | 68.9% | 5.04 |  |
| Adaptive Router | 8,272,387 | 4.00x | 75.0% | 0.00 | selected brotli |

## Synthetic Experiments (n=100)

### Synthetic: Standard (80% reuse)

- **Prompts:** 100
- **Mean chars/prompt:** 1572.6
| Method | Ratio | Savings | Stored Bytes |
|---|---:|---:|---:|
| Per-prompt Zstd | 1.78x | 43.8% | 88,330 |
| Gzip/DEFLATE (best level) | 1.80x | 44.3% | 87,545 |
| Brotli (best quality) | 2.47x | 59.4% | 63,770 |
| Hybrid Cascade (best) | 2.43x | 58.8% | 64,770 |
| Per-prompt Hybrid | 2.22x | 54.9% | 70,938 |
| Zstd + Dictionary | 1.01x | 1.4% | 23,944 |
| Corpus Dedup | 5.38x | 81.4% | 29,245 |
| Corpus Dedup (chunked) | 5.38x | 81.4% | 29,245 |
| Delta Compression | 1.78x | 43.8% | 88,330 |
| Adaptive Router | 5.38x | 81.4% | 29,245 |

### Synthetic: Full reuse (100%)

- **Prompts:** 100
- **Mean chars/prompt:** 1649.4
| Method | Ratio | Savings | Stored Bytes |
|---|---:|---:|---:|
| Per-prompt Zstd | 1.80x | 44.6% | 91,399 |
| Gzip/DEFLATE (best level) | 1.82x | 45.1% | 90,507 |
| Brotli (best quality) | 2.54x | 60.7% | 64,896 |
| Hybrid Cascade (best) | 2.50x | 60.0% | 65,896 |
| Per-prompt Hybrid | 2.25x | 55.6% | 73,218 |
| Zstd + Dictionary | 1.10x | 8.7% | 19,489 |
| Corpus Dedup | 5.96x | 83.2% | 27,693 |
| Corpus Dedup (chunked) | 5.96x | 83.2% | 27,693 |
| Delta Compression | 1.80x | 44.6% | 91,399 |
| Adaptive Router | 5.96x | 83.2% | 27,693 |

### Synthetic: Low reuse (10%)

- **Prompts:** 100
- **Mean chars/prompt:** 1376.0
| Method | Ratio | Savings | Stored Bytes |
|---|---:|---:|---:|
| Per-prompt Zstd | 1.72x | 41.9% | 79,967 |
| Gzip/DEFLATE (best level) | 1.73x | 42.3% | 79,412 |
| Brotli (best quality) | 2.28x | 56.1% | 60,443 |
| Hybrid Cascade (best) | 2.24x | 55.3% | 61,443 |
| Per-prompt Hybrid | 2.13x | 53.0% | 64,680 |
| Zstd + Dictionary | 0.86x | -16.2% | 28,841 |
| Corpus Dedup | 4.76x | 79.0% | 28,902 |
| Corpus Dedup (chunked) | 4.76x | 79.0% | 28,902 |
| Delta Compression | 1.72x | 41.9% | 79,967 |
| Adaptive Router | 4.76x | 79.0% | 28,902 |

### Synthetic: Zero reuse (worst case)

- **Prompts:** 100
- **Mean chars/prompt:** 622.3
| Method | Ratio | Savings | Stored Bytes |
|---|---:|---:|---:|
| Per-prompt Zstd | 1.96x | 48.9% | 31,787 |
| Gzip/DEFLATE (best level) | 1.93x | 48.1% | 32,324 |
| Brotli (best quality) | 2.73x | 63.3% | 22,823 |
| Hybrid Cascade (best) | 2.62x | 61.9% | 23,729 |
| Per-prompt Hybrid | 2.33x | 57.1% | 26,679 |
| Zstd + Dictionary | 0.43x | -131.2% | 12,825 |
| Corpus Dedup | 1.53x | 34.7% | 40,667 |
| Corpus Dedup (chunked) | 1.53x | 34.7% | 40,667 |
| Delta Compression | 1.96x | 48.9% | 31,787 |
| Adaptive Router | 2.73x | 63.3% | 22,823 |

### Synthetic: Zero reuse + tools/context

- **Prompts:** 100
- **Mean chars/prompt:** 1075.5
| Method | Ratio | Savings | Stored Bytes |
|---|---:|---:|---:|
| Per-prompt Zstd | 1.90x | 47.3% | 56,727 |
| Gzip/DEFLATE (best level) | 1.89x | 47.0% | 57,050 |
| Brotli (best quality) | 2.51x | 60.1% | 42,876 |
| Hybrid Cascade (best) | 2.45x | 59.2% | 43,843 |
| Per-prompt Hybrid | 2.27x | 55.9% | 47,410 |
| Zstd + Dictionary | 0.72x | -38.6% | 17,994 |
| Corpus Dedup | 2.45x | 59.2% | 43,882 |
| Corpus Dedup (chunked) | 2.45x | 59.2% | 43,882 |
| Delta Compression | 1.90x | 47.3% | 56,727 |
| Adaptive Router | 2.51x | 60.1% | 42,876 |

## Scaling Data — Synthetic

| N | Original Bytes | Dedup Ratio | Zstd Ratio | Dict Ratio | Dedup vs Zstd |
|---:|---:|---:|---:|---:|---:|
| 1 | 2,349 | 1.37x | 1.82x | 0.02x | -32.3% |
| 2 | 4,723 | 2.30x | 1.82x | 0.04x | 20.7% |
| 5 | 9,786 | 3.44x | 1.81x | 0.07x | 47.3% |
| 10 | 17,665 | 3.71x | 1.81x | 0.13x | 51.3% |
| 25 | 42,938 | 4.64x | 1.80x | 0.32x | 61.2% |
| 50 | 81,835 | 4.67x | 1.79x | 0.58x | 61.6% |
| 100 | 157,261 | 5.38x | 1.78x | 1.01x | 66.9% |

## Scaling Data — Real (max-prompts=200)

| N | Original Bytes | Dedup Ratio | Zstd Ratio | Dict Ratio | Dedup vs Zstd |
|---:|---:|---:|---:|---:|---:|
| 1 | 9,777 | 1.82x | 2.98x | 0.07x | -63.7% |
| 2 | 10,282 | 1.77x | 2.91x | 0.08x | -64.1% |
| 5 | 33,236 | 1.92x | 3.77x | 0.25x | -96.9% |
| 10 | 60,441 | 1.93x | 3.49x | 0.44x | -80.6% |
| 25 | 164,894 | 1.91x | 3.28x | 1.05x | -71.4% |
| 50 | 297,079 | 1.89x | 2.90x | 1.46x | -53.2% |
| 100 | 584,983 | 1.90x | 2.96x | 2.04x | -55.6% |
| 200 | 1,250,309 | 1.96x | 3.07x | 2.67x | -56.3% |

## Scaling Data — Real (max-prompts=1000)

| N | Original Bytes | Dedup Ratio | Zstd Ratio | Dict Ratio | Dedup vs Zstd |
|---:|---:|---:|---:|---:|---:|
| 1 | 9,777 | 1.82x | 2.98x | 0.07x | -63.7% |
| 2 | 10,282 | 1.77x | 2.91x | 0.08x | -64.1% |
| 5 | 33,236 | 1.92x | 3.77x | 0.25x | -96.9% |
| 10 | 60,441 | 1.93x | 3.49x | 0.44x | -80.6% |
| 25 | 164,894 | 1.91x | 3.28x | 1.07x | -71.4% |
| 50 | 297,079 | 1.89x | 2.90x | 1.69x | -53.2% |
| 100 | 584,983 | 1.90x | 2.96x | 2.48x | -55.6% |
| 250 | 1,584,736 | 1.96x | 3.02x | 3.17x | -53.8% |
| 500 | 3,275,445 | 1.98x | 3.11x | 3.53x | -57.1% |
| 1,000 | 6,784,814 | 2.00x | 3.14x | 3.67x | -56.8% |

## Scaling Data — Real (max-prompts=2000)

| N | Original Bytes | Dedup Ratio | Zstd Ratio | Dict Ratio | Dedup vs Zstd |
|---:|---:|---:|---:|---:|---:|
| 1 | 9,777 | 1.82x | 2.98x | 0.07x | -63.7% |
| 2 | 10,282 | 1.77x | 2.91x | 0.08x | -64.1% |
| 5 | 33,236 | 1.92x | 3.77x | 0.24x | -96.9% |
| 10 | 60,441 | 1.93x | 3.49x | 0.43x | -80.6% |
| 25 | 164,894 | 1.91x | 3.28x | 1.02x | -71.4% |
| 50 | 297,079 | 1.89x | 2.90x | 1.56x | -53.2% |
| 100 | 584,983 | 1.90x | 2.96x | 2.31x | -55.6% |
| 250 | 1,584,736 | 1.96x | 3.02x | 3.15x | -53.8% |
| 500 | 3,275,445 | 1.98x | 3.11x | 3.54x | -57.1% |
| 1,000 | 6,784,814 | 2.00x | 3.14x | 3.69x | -56.8% |
| 2,000 | 13,433,635 | 2.04x | 3.21x | 3.88x | -57.5% |

## Scaling Data — Real (max-prompts=5000)

| N | Original Bytes | Dedup Ratio | Zstd Ratio | Dict Ratio | Dedup vs Zstd |
|---:|---:|---:|---:|---:|---:|
| 1 | 9,777 | 1.82x | 2.98x | 0.07x | -63.7% |
| 2 | 10,282 | 1.77x | 2.91x | 0.08x | -64.1% |
| 5 | 33,236 | 1.92x | 3.77x | 0.24x | -96.9% |
| 10 | 60,441 | 1.93x | 3.49x | 0.42x | -80.6% |
| 25 | 164,894 | 1.91x | 3.28x | 0.99x | -71.4% |
| 50 | 297,079 | 1.89x | 2.90x | 1.45x | -53.2% |
| 100 | 584,983 | 1.90x | 2.96x | 2.13x | -55.6% |
| 250 | 1,584,736 | 1.96x | 3.02x | 3.14x | -53.8% |
| 500 | 3,275,445 | 1.98x | 3.11x | 3.67x | -57.1% |
| 1,000 | 6,784,814 | 2.00x | 3.14x | 3.77x | -56.8% |
| 2,500 | 16,867,731 | 2.03x | 3.21x | 3.94x | -58.3% |
| 5,000 | 33,095,761 | 2.03x | 3.22x | 3.99x | -58.8% |

## Reproducibility

```bash
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 200 --output research_real_200.json --csv research_real_scaling_200.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 1000 --output research_real_1000.json --csv research_real_scaling_1000.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 2000 --output research_real_2000.json --csv research_real_scaling_2000.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 5000 --output research_real_5000.json --csv research_real_scaling_5000.csv
python benchmark_full_evaluation.py --n 100 --output evaluation_results.json --csv research_scaling_2026_03_28.csv
```