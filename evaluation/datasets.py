import glob
import json
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
# ─── Real Dataset Loader ────────────────────────────────────────────────────

def load_real_dataset(
    filepath: str,
    json_field: Optional[str] = None,
    nested_field: Optional[str] = None,
    max_prompts: Optional[int] = None,
    min_length: int = 10,
) -> Tuple[List[str], Dict]:
    """
    Load prompts from a real JSON dataset file.

    Supports many common formats:
        - JSON array of strings: ["prompt1", "prompt2", ...]
        - JSON array of objects: [{"prompt": "...", ...}, ...]
        - JSON Lines (JSONL): one JSON object per line
        - ShareGPT format: [{"conversations": [{"from": "human", "value": "..."}]}, ...]
        - Alpaca format: [{"instruction": "...", "input": "...", "output": "..."}, ...]
        - OpenAI format: [{"messages": [{"role": "user", "content": "..."}]}, ...]
        - Single object with a list field: {"data": [...], "rows": [...]}

    Args:
        filepath: Path to JSON or JSONL file
        json_field: Specific field name to extract text from (auto-detected if None)
        nested_field: For nested structures (e.g., "value" within conversation turns)
        max_prompts: Maximum number of prompts to load (None = all)
        min_length: Minimum character length to include a prompt

    Returns:
        (prompts, metadata_dict)
    """
    filepath = Path(filepath)

    # If filepath is a directory, load all files from it
    if filepath.is_dir():
        return load_multiple_datasets(
            str(filepath),
            json_field=json_field,
            max_per_file=max_prompts,
        )

    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    file_size = filepath.stat().st_size
    print(f"\n  Loading dataset: {filepath}")
    print(f"  File size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")

    # Load raw data
    raw_data = _load_json_file(filepath)

    # Extract prompts
    prompts = _extract_prompts(raw_data, json_field, nested_field)

    # Filter and clean
    prompts = [p.strip() for p in prompts if isinstance(p, str) and len(p.strip()) >= min_length]

    # Deduplicate while preserving order (to measure natural redundancy)
    # We do NOT deduplicate here — the whole point is to measure how well
    # the compression handles natural duplicates
    if max_prompts and len(prompts) > max_prompts:
        prompts = prompts[:max_prompts]

    if not prompts:
        raise ValueError(
            f"No valid prompts extracted from {filepath}. "
            f"Try specifying --json-field explicitly. "
            f"Sample keys found: {_sample_keys(raw_data)}"
        )

    # Compute dataset statistics
    lengths = [len(p) for p in prompts]
    unique_prompts = len(set(prompts))

    metadata = {
        "n_prompts": len(prompts),
        "source_file": str(filepath),
        "file_size_bytes": file_size,
        "mean_prompt_chars": sum(lengths) / len(lengths),
        "median_prompt_chars": sorted(lengths)[len(lengths) // 2],
        "min_prompt_chars": min(lengths),
        "max_prompt_chars": max(lengths),
        "total_chars": sum(lengths),
        "unique_prompts": unique_prompts,
        "exact_duplicate_pct": (1 - unique_prompts / len(prompts)) * 100,
        "json_field_used": json_field or "auto-detected",
        "dataset_type": "real",
    }

    print(f"  Loaded {len(prompts):,} prompts ({unique_prompts:,} unique)")
    print(f"  Char lengths: mean={metadata['mean_prompt_chars']:.0f}, "
          f"median={metadata['median_prompt_chars']}, "
          f"range=[{metadata['min_prompt_chars']}, {metadata['max_prompt_chars']}]")
    print(f"  Exact duplicates: {metadata['exact_duplicate_pct']:.1f}%")

    return prompts, metadata


def _load_json_file(filepath: Path) -> Any:
    """Load JSON, JSONL, or Parquet file."""
    suffix = filepath.suffix.lower()

    # Parquet support
    if suffix == '.parquet':
        try:
            import pandas as pd
            df = pd.read_parquet(filepath)
            return df.to_dict(orient='records')
        except ImportError:
            raise ImportError("Install pandas and pyarrow: pip install pandas pyarrow")

    # JSONL
    if suffix in ('.jsonl', '.ndjson'):
        return _load_jsonl(filepath)

    # Standard JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        try:
            return _load_jsonl(filepath)
        except Exception:
            raise ValueError(f"Could not parse {filepath} as JSON or JSONL")


def _load_jsonl(filepath: Path) -> List[Dict]:
    """Load JSON Lines file."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                if line_num <= 3:
                    raise  # First few lines should parse
                continue  # Skip malformed lines later
    return records


def _sample_keys(data: Any) -> List[str]:
    """Extract sample keys from data for error messages."""
    if isinstance(data, dict):
        return list(data.keys())[:10]
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return list(first.keys())[:10]
        return [f"(list of {type(first).__name__})"]
    return [f"(type: {type(data).__name__})"]


def _extract_prompts(
    data: Any,
    json_field: Optional[str] = None,
    nested_field: Optional[str] = None,
) -> List[str]:
    """
    Extract prompt strings from various JSON structures.
    Auto-detects format if json_field is not specified.
    """
    prompts = []

    # If data is a dict with a single list field, unwrap it
    if isinstance(data, dict):
        if json_field and json_field in data:
            data = data[json_field]
        else:
            # Try common wrapper fields
            for wrapper_key in ['data', 'rows', 'samples', 'examples', 'prompts',
                                'dataset', 'records', 'items', 'instances',
                                'train', 'test', 'validation']:
                if wrapper_key in data and isinstance(data[wrapper_key], list):
                    print(f"  Auto-detected wrapper field: '{wrapper_key}'")
                    data = data[wrapper_key]
                    break
            else:
                # If still a dict, try to use all values
                if isinstance(data, dict):
                    # Maybe it's a dict of id -> prompt
                    data = list(data.values())

    # data should now be a list
    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}. Specify --json-field.")

    if not data:
        return []

    first = data[0]

    # Case 1: List of strings
    if isinstance(first, str):
        return data

    # Case 2: List of dicts
    if isinstance(first, dict):
        if json_field:
            # User specified the field
            return _extract_field(data, json_field, nested_field)

        # Auto-detect format
        keys = set(first.keys())

        # ShareGPT format: {"conversations": [{"from": "human", "value": "..."}]}
        if 'conversations' in keys:
            print("  Auto-detected format: ShareGPT")
            return _extract_sharegpt(data, nested_field)

        # OpenAI messages format: {"messages": [{"role": "user", "content": "..."}]}
        if 'messages' in keys:
            print("  Auto-detected format: OpenAI messages")
            return _extract_openai_messages(data)

        # Alpaca format: {"instruction": "...", "input": "...", "output": "..."}
        if 'instruction' in keys:
            print("  Auto-detected format: Alpaca")
            return _extract_alpaca(data)

        # Try common prompt field names
        prompt_fields = [
            'prompt', 'text', 'content', 'input', 'question',
            'query', 'instruction', 'message', 'body',
            'human', 'user', 'request', 'source',
            'context', 'sentence', 'utterance',
        ]
        for field in prompt_fields:
            if field in keys:
                values = [r[field] for r in data if field in r and isinstance(r[field], str)]
                if values:
                    print(f"  Auto-detected field: '{field}'")
                    return values

        # Try to concatenate all string fields
        print(f"  Warning: No standard field found. Keys: {list(keys)[:8]}")
        print(f"  Trying to concatenate all string values...")
        for record in data:
            text_parts = []
            for k, v in record.items():
                if isinstance(v, str) and len(v) >= 5:
                    text_parts.append(f"{k}: {v}")
            if text_parts:
                prompts.append("\n".join(text_parts))

    # Case 3: List of lists (e.g., conversation turns)
    elif isinstance(first, list):
        for conversation in data:
            parts = []
            for turn in conversation:
                if isinstance(turn, str):
                    parts.append(turn)
                elif isinstance(turn, dict):
                    for k in ['content', 'text', 'value', 'message']:
                        if k in turn:
                            parts.append(str(turn[k]))
                            break
            if parts:
                prompts.append("\n".join(parts))

    return prompts


def _extract_field(
    data: List[Dict],
    field: str,
    nested_field: Optional[str] = None,
) -> List[str]:
    """Extract a specific field from records, with optional nested extraction."""
    prompts = []
    for record in data:
        if field not in record:
            continue

        value = record[field]

        if isinstance(value, str):
            prompts.append(value)
        elif isinstance(value, list):
            # It's a list — could be conversation turns
            parts = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and nested_field and nested_field in item:
                    parts.append(str(item[nested_field]))
                elif isinstance(item, dict):
                    # Try common sub-fields
                    for k in ['content', 'text', 'value', 'message']:
                        if k in item:
                            parts.append(str(item[k]))
                            break
            if parts:
                prompts.append("\n".join(parts))
        elif isinstance(value, dict) and nested_field:
            if nested_field in value:
                prompts.append(str(value[nested_field]))
    return prompts


def _extract_sharegpt(data: List[Dict], nested_field: Optional[str] = None) -> List[str]:
    """Extract from ShareGPT format conversations."""
    prompts = []
    value_key = nested_field or 'value'

    for record in data:
        convs = record.get('conversations', [])
        if not convs:
            continue

        parts = []
        for turn in convs:
            role = turn.get('from', turn.get('role', 'unknown'))
            text = turn.get(value_key, turn.get('content', turn.get('text', '')))
            if text:
                parts.append(f"{role}: {text}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def _extract_openai_messages(data: List[Dict]) -> List[str]:
    """Extract from OpenAI messages format."""
    prompts = []
    for record in data:
        messages = record.get('messages', [])
        if not messages:
            continue

        parts = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                parts.append(f"{role}: {content}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def _extract_alpaca(data: List[Dict]) -> List[str]:
    """Extract from Alpaca format, combining instruction + input."""
    prompts = []
    for record in data:
        parts = []
        instruction = record.get('instruction', '')
        input_text = record.get('input', '')
        output_text = record.get('output', '')

        if instruction:
            parts.append(f"Instruction: {instruction}")
        if input_text:
            parts.append(f"Input: {input_text}")
        if output_text:
            parts.append(f"Output: {output_text}")

        if parts:
            prompts.append("\n".join(parts))

    return prompts


def load_multiple_datasets(
    directory: str,
    json_field: Optional[str] = None,
    max_per_file: Optional[int] = None,
) -> Tuple[List[str], Dict]:
    """Load and combine prompts from all JSON/JSONL files in a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = sorted(
        glob.glob(str(directory / "*.json")) +
        glob.glob(str(directory / "*.jsonl")) +
        glob.glob(str(directory / "*.ndjson")) +
        glob.glob(str(directory / "*.parquet"))
    )

    if not files:
        raise FileNotFoundError(f"No JSON files found in {directory}")

    all_prompts = []
    file_counts = {}

    for fpath in files:
        try:
            prompts, _ = load_real_dataset(fpath, json_field=json_field, max_prompts=max_per_file)
            file_counts[os.path.basename(fpath)] = len(prompts)
            all_prompts.extend(prompts)
        except Exception as e:
            print(f"  Warning: Skipping {fpath}: {e}")

    if not all_prompts:
        raise ValueError(f"No prompts loaded from any file in {directory}")

    lengths = [len(p) for p in all_prompts]
    unique_prompts = len(set(all_prompts))

    metadata = {
        "n_prompts": len(all_prompts),
        "source_directory": str(directory),
        "n_files": len(file_counts),
        "file_counts": file_counts,
        "mean_prompt_chars": sum(lengths) / len(lengths),
        "total_chars": sum(lengths),
        "unique_prompts": unique_prompts,
        "exact_duplicate_pct": (1 - unique_prompts / len(all_prompts)) * 100,
        "dataset_type": "real_multi",
    }

    print(f"\n  Combined: {len(all_prompts):,} prompts from {len(file_counts)} files")

    return all_prompts, metadata


def analyze_dataset_redundancy(prompts: List[str]) -> Dict:
    """
    Analyze the natural redundancy patterns in a real dataset.
    Returns detailed statistics useful for understanding compression potential.
    """
    from collections import Counter

    total_prompts = len(prompts)

    # Exact duplicate analysis
    prompt_counts = Counter(prompts)
    unique_count = len(prompt_counts)
    most_common = prompt_counts.most_common(10)

    # Prefix sharing analysis (common system prompts)
    prefix_lengths = [50, 100, 200, 500]
    prefix_sharing = {}
    for plen in prefix_lengths:
        prefixes = Counter(p[:plen] for p in prompts if len(p) >= plen)
        n_qualifying = sum(1 for p in prompts if len(p) >= plen)
        if prefixes:
            most_common_prefix = prefixes.most_common(1)[0]
            prefix_sharing[f"prefix_{plen}_chars"] = {
                "unique_prefixes": len(prefixes),
                "qualifying_prompts": n_qualifying,
                "most_common_count": most_common_prefix[1],
                "most_common_pct": most_common_prefix[1] / n_qualifying * 100 if n_qualifying else 0,
                "preview": most_common_prefix[0][:80] + "...",
            }

    # Line-level deduplication potential
    all_lines = []
    for p in prompts:
        all_lines.extend(p.split('\n'))
    all_lines = [l for l in all_lines if len(l.strip()) >= 5]
    line_counts = Counter(all_lines)
    total_lines = len(all_lines)
    unique_lines = len(line_counts)
    repeated_lines = sum(1 for c in line_counts.values() if c > 1)

    # Substring analysis (rough — check for common long substrings)
    # Use 100-char windows
    window_size = 100
    windows = Counter()
    for p in prompts[:500]:  # Sample for performance
        for i in range(0, len(p) - window_size + 1, 50):  # Step by 50
            windows[p[i:i + window_size]] += 1
    repeated_windows = sum(1 for c in windows.values() if c > 1)

    analysis = {
        "total_prompts": total_prompts,
        "unique_prompts": unique_count,
        "exact_duplicate_pct": (1 - unique_count / total_prompts) * 100 if total_prompts else 0,
        "most_duplicated": [
            {"count": count, "preview": text[:120] + ("..." if len(text) > 120 else "")}
            for text, count in most_common[:5]
        ],
        "prefix_sharing": prefix_sharing,
        "line_level": {
            "total_lines": total_lines,
            "unique_lines": unique_lines,
            "repeated_lines": repeated_lines,
            "line_reuse_pct": (1 - unique_lines / total_lines) * 100 if total_lines else 0,
        },
        "substring_windows": {
            "window_size": window_size,
            "total_windows_sampled": len(windows),
            "repeated_windows": repeated_windows,
            "repetition_pct": repeated_windows / len(windows) * 100 if windows else 0,
        },
    }

    return analysis

