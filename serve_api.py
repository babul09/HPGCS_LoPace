import time
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from evaluation.data_generators import generate_corpus
from evaluation.datasets import load_real_dataset
from evaluation.runner import run_experiment

app = FastAPI(title="HPGCS Benchmark API")
WORKSPACE_ROOT = Path(__file__).resolve().parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class BenchmarkRequest(BaseModel):
    mode: str  # "synthetic" or "real"
    n_prompts: int = 1000
    system_reuse: float = 0.8
    include_tools: float = 0.4
    include_context: float = 0.3
    real_data_path: str = ""
    json_field: str = ""

@app.post("/api/benchmark")
async def execute_benchmark(req: BenchmarkRequest):
    try:
        if req.mode == "real":
            if not req.real_data_path:
                raise HTTPException(status_code=400, detail="real_data_path is required for real mode.")
            try:
                prompts, meta = load_real_dataset(
                    req.real_data_path,
                    json_field=req.json_field if req.json_field else None,
                    max_prompts=req.n_prompts if req.n_prompts > 0 else None
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to load dataset: {str(e)}")
        else:
            # Synthetic
            n_unique_systems = max(1, int(req.n_prompts * (1 - req.system_reuse)))
            prompts, meta = generate_corpus(
                n_prompts=req.n_prompts,
                system_reuse=req.system_reuse,
                n_unique_systems=n_unique_systems,
                include_tools=req.include_tools,
                include_context=req.include_context
            )
            
        results = run_experiment("Web UI Triggered Run", prompts, meta)
        
        # Clean up large marginal lists before returning
        for m in results["methods"].values():
            m.pop("marginal_costs", None)
            
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmark-results")
async def load_benchmark_results(path: str = "evaluation_results.json"):
    try:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = WORKSPACE_ROOT / candidate
        candidate = candidate.resolve()

        root = WORKSPACE_ROOT.resolve()
        if candidate != root and root not in candidate.parents:
            raise HTTPException(status_code=400, detail="Path must be inside the project workspace.")

        if candidate.suffix.lower() != ".json":
            raise HTTPException(status_code=400, detail="Only .json result files are supported.")

        if not candidate.exists() or not candidate.is_file():
            raise HTTPException(status_code=404, detail=f"Result file not found: {candidate}")

        with open(candidate, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, dict) or "experiments" not in payload:
            raise HTTPException(status_code=400, detail="Invalid results format. Expected top-level 'experiments'.")

        return {
            "path": str(candidate),
            "results": payload,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark results: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("serve_api:app", host="0.0.0.0", port=8000, reload=True)
