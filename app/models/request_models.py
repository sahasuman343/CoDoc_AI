from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any, List, Literal
from enum import Enum

class InputType(str, Enum):
    """Supported input types for codebase analysis"""
    GITHUB_URL = "github_url"
    LOCAL_PATH = "local_path"

class CodebaseAnalysisRequest(BaseModel):
    """Request model for codebase analysis"""
    source: str
    input_type: InputType
    include_diagrams: bool = True
    include_documentation: bool = True
    max_files: Optional[int] = 1000
    
    @validator('source')
    def validate_source(cls, v, values):
        input_type = values.get('input_type')
        if input_type == InputType.GITHUB_URL:
            if not (v.startswith('https://github.com/') or v.startswith('https://www.github.com/')):
                raise ValueError('GitHub URL must start with https://github.com/')
        elif input_type == InputType.LOCAL_PATH:
            if not v.strip():
                raise ValueError('Local path cannot be empty')
        return v

class FileInfo(BaseModel):
    """Information about a single file"""
    path: str
    type: str
    size: int
    lines: int
    language: Optional[str] = None
    documentation: Optional[str] = None

class ProjectStructure(BaseModel):
    """Project structure representation"""
    name: str
    files: List[FileInfo]
    directories: List[str]
    total_files: int
    total_lines: int

class AnalysisResponse(BaseModel):
    """Response model for completed analysis"""
    analysis_id: str
    project_overview: str
    file_structure: ProjectStructure
    file_documentation: Dict[str, str]
    sequence_diagram: Optional[str] = None
    class_diagram: Optional[str] = None
    technologies_used: List[str]
    total_files: int
    total_lines: int