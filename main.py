from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
import uvicorn
import os
import asyncio
from datetime import datetime
import uuid

# Import our custom modules
from app.models.request_models import CodebaseAnalysisRequest, AnalysisResponse
from app.services.codebase_analyzer import CodebaseAnalyzer
from app.services.ai_documentation_service import AIDocumentationService
from app.utils.logger import setup_logger

# Initialize FastAPI app
app = FastAPI(
    title="Codebase Documentation Generator",
    description="AI-powered codebase analysis and documentation generation with sequence and class diagrams",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
logger = setup_logger(__name__)
codebase_analyzer = CodebaseAnalyzer()
ai_doc_service = AIDocumentationService()

# In-memory storage for analysis results (in production, use a database)
analysis_results = {}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Codebase Documentation Generator API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/analyze",
            "status": "/analysis/{analysis_id}/status",
            "result": "/analysis/{analysis_id}/result"
        }
    }

@app.post("/analyze", response_model=Dict[str, str])
async def start_analysis(
    request: CodebaseAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Start codebase analysis"""
    try:
        analysis_id = str(uuid.uuid4())
        
        # Initialize analysis result
        analysis_results[analysis_id] = {
            "status": "processing",
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Analysis started"
        }
        
        # Start background analysis task
        background_tasks.add_task(
            perform_analysis,
            analysis_id,
            request
        )
        
        logger.info(f"Started analysis {analysis_id} for {request.input_type}: {request.source}")
        
        return {
            "analysis_id": analysis_id,
            "status": "processing",
            "message": "Analysis started. Use the analysis_id to check status and retrieve results."
        }
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.get("/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """Get analysis status"""
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = analysis_results[analysis_id]
    return {
        "analysis_id": analysis_id,
        "status": result["status"],
        "progress": result.get("progress", 0),
        "message": result.get("message", ""),
        "started_at": result.get("started_at"),
        "completed_at": result.get("completed_at")
    }

@app.get("/analysis/{analysis_id}/result", response_model=AnalysisResponse)
async def get_analysis_result(analysis_id: str):
    """Get analysis results"""
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    result = analysis_results[analysis_id]
    
    if result["status"] == "processing":
        raise HTTPException(status_code=202, detail="Analysis still in progress")
    elif result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
    
    return result["data"]

async def perform_analysis(analysis_id: str, request: CodebaseAnalysisRequest):
    """Background task to perform codebase analysis"""
    try:
        # Update progress
        analysis_results[analysis_id]["progress"] = 10
        analysis_results[analysis_id]["message"] = "Initializing analysis..."
        
        # Step 1: Get codebase structure
        analysis_results[analysis_id]["progress"] = 20
        analysis_results[analysis_id]["message"] = "Analyzing codebase structure..."
        
        codebase_data = await codebase_analyzer.analyze_codebase(request)
        
        # Step 2: Generate documentation (conditional based on request)
        documentation = {"overview": "", "files": {}}
        if request.include_documentation:
            analysis_results[analysis_id]["progress"] = 50
            analysis_results[analysis_id]["message"] = "Generating AI documentation..."
            documentation = await ai_doc_service.generate_documentation(codebase_data)
        
        # Step 3: Generate diagrams (conditional based on request)
        sequence_diagram = None
        class_diagram = None
        if request.include_diagrams:
            analysis_results[analysis_id]["progress"] = 80
            analysis_results[analysis_id]["message"] = "Creating sequence and class diagrams..."
            sequence_diagram = await ai_doc_service.generate_sequence_diagram(codebase_data)
            class_diagram = await ai_doc_service.generate_class_diagram(codebase_data)
        
        # Complete analysis
        analysis_results[analysis_id] = {
            "status": "completed",
            "started_at": analysis_results[analysis_id]["started_at"],
            "completed_at": datetime.now().isoformat(),
            "progress": 100,
            "message": "Analysis completed successfully",
            "data": AnalysisResponse(
                analysis_id=analysis_id,
                project_overview=documentation["overview"],
                file_structure=codebase_data["structure"],
                file_documentation=documentation["files"],
                sequence_diagram=sequence_diagram,
                class_diagram=class_diagram,
                technologies_used=codebase_data["technologies"],
                total_files=codebase_data["total_files"],
                total_lines=codebase_data["total_lines"]
            )
        }
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {str(e)}")
        analysis_results[analysis_id] = {
            "status": "failed",
            "started_at": analysis_results[analysis_id]["started_at"],
            "completed_at": datetime.now().isoformat(),
            "progress": 0,
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )