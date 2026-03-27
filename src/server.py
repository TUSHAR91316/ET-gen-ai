import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from engine import (
    ContentOpsWorkflow,
    ContentRequest,
    DEFAULT_GUARDRAILS,
    CHANNELS_DEFAULT,
    DEFAULT_LANGUAGES,
)
import uvicorn
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Enterprise Content Ops Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
RUNS_DIR = os.path.join(BASE_DIR, "runs")

os.makedirs(RUNS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

workflow = ContentOpsWorkflow(output_dir=RUNS_DIR)
runs_store = {}  # In-memory store for active job states

class GenerateDraftRequest(BaseModel):
    spec: str
    audience: str
    channels: List[str]
    languages: List[str]
    compliance_threshold: float

class ApproveRequest(BaseModel):
    job_id: str
    decision: str
    human_feedback: Optional[str] = None

@app.post("/api/preview")
def create_preview(req: GenerateDraftRequest):
    content_req = ContentRequest(
        spec=req.spec,
        audience=req.audience,
        channels=req.channels,
        languages=req.languages,
        guardrails=DEFAULT_GUARDRAILS
    )
    
    drafted_assets, compliance_report, strategy = workflow.preview_draft_and_compliance(
        content_req, compliance_threshold=req.compliance_threshold
    )
    
    runs_store[content_req.job_id] = {
        "request": content_req,
        "drafted_assets": drafted_assets,
        "compliance_report": compliance_report,
        "strategy": strategy
    }
    
    # Dump to JSON friendly format
    import dataclasses
    def to_dict(obj): return dataclasses.asdict(obj) if dataclasses.is_dataclass(obj) else obj
    
    return {
        "job_id": content_req.job_id,
        "drafted_assets": [to_dict(a) for a in drafted_assets],
        "compliance_report": to_dict(compliance_report),
        "strategy": strategy
    }

@app.post("/api/approve")
def approve_and_run(req: ApproveRequest):
    if req.job_id not in runs_store:
        return {"error": "Job not found"}, 404
        
    state = runs_store[req.job_id]
    original_req = state["request"]
    
    if req.decision == "Request edits":
        if not req.human_feedback:
            return {"error": "Feedback required for edits"}, 400
            
        new_req = ContentRequest(
            spec=original_req.spec + "\n\nHUMAN_FEEDBACK: " + req.human_feedback,
            audience=original_req.audience,
            channels=original_req.channels,
            languages=original_req.languages,
            guardrails=original_req.guardrails,
            job_id=req.job_id
        )
        
        drafted_assets, compliance_report, strategy = workflow.preview_draft_and_compliance(
            new_req, compliance_threshold=0.85
        )
        runs_store[new_req.job_id] = {
            "request": new_req,
            "drafted_assets": drafted_assets,
            "compliance_report": compliance_report,
            "strategy": strategy
        }
        
        import dataclasses
        def to_dict(obj): return dataclasses.asdict(obj) if dataclasses.is_dataclass(obj) else obj
        
        return {
            "updated": True,
            "job_id": new_req.job_id,
            "drafted_assets": [to_dict(a) for a in drafted_assets],
            "compliance_report": to_dict(compliance_report)
        }
        
    else:
        # Approved
        def auto_approve(draft_payload, report):
            return {"approved": True, "mode": "manual_ui_approved"}
            
        run = workflow.run(
            original_req,
            approval_callback=auto_approve,
            auto_approve=False
        )
        
        return run.to_json()


@app.get("/")
def get_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    print("Starting FastAPI Server...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
