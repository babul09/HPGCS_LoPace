import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from benchmark_full_evaluation import generate_corpus, load_real_dataset, run_experiment

app = FastAPI(title="HPGCS Benchmark API")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("serve_api:app", host="0.0.0.0", port=8000, reload=True)
