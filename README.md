# Codebase Documentation Generator

## Overview

This is a production-ready AI-powered codebase analysis and documentation generation service built with FastAPI. The application analyzes code repositories (from GitHub URLs or local paths) and generates comprehensive documentation including project overviews, file-specific documentation, sequence diagrams, and class diagrams. It leverages tree-sitter for actual code parsing and GROQ's fast AI API for intelligent documentation generation.

**Key Features:**
- **Real Code Analysis**: Uses tree-sitter to parse and extract classes, functions, imports, and dependencies from actual source code
- **AI-Powered Documentation**: Generates meaningful documentation based on parsed code content using GROQ's fast inference
- **Visual Diagrams**: Creates sequence diagrams and class diagrams in Mermaid format based on actual code structure
- **Flexible Input**: Supports both GitHub repository URLs and local directory paths
- **Production Security**: Comprehensive path validation and symlink protection for safe local directory analysis
- **Configurable Analysis**: Respects user parameters like max_files, include_diagrams, include_documentation

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **FastAPI**: Chosen for its modern async support, automatic API documentation, and strong type validation with Pydantic models
- **Async/Await Pattern**: Enables concurrent processing of multiple analysis requests without blocking

### Code Analysis Engine
- **Tree-sitter Parsers**: Used for accurate syntax parsing of multiple programming languages (Python, JavaScript, TypeScript, Java, C++, etc.)
- **Multi-language Support**: Extensible language detection and parsing system supporting 15+ programming languages
- **Git Integration**: Direct GitHub repository cloning for remote codebase analysis

### AI Documentation Service
- **GROQ API Integration**: Uses llama-3.1-8b-instant model for fast, intelligent code documentation generation
- **Contextual Analysis**: Generates project overviews and file-specific documentation based on actual code content rather than generic templates

### Data Models
- **Pydantic Models**: Strong type validation for API requests and responses
- **Structured Analysis Results**: Organized data models for file information, project structure, and analysis responses

### Request Processing
- **Background Tasks**: Long-running analysis operations handled asynchronously
- **In-memory Storage**: Analysis results stored temporarily (designed for database integration in production)
- **Status Tracking**: RESTful endpoints for checking analysis progress and retrieving results

### Error Handling and Logging
- **Structured Logging**: Consistent logging across all services with timestamp and level formatting
- **Exception Management**: Comprehensive error handling with detailed logging for debugging

## External Dependencies

### AI Services
- **GROQ API**: Primary AI service for code analysis and documentation generation (requires GROQ_API_KEY environment variable)

### Code Analysis Libraries
- **tree-sitter-python**: Python syntax parsing
- **tree-sitter-javascript**: JavaScript/TypeScript syntax parsing
- **GitPython**: Git repository operations and cloning

### Web Framework
- **FastAPI**: Core web framework with built-in validation and documentation
- **Uvicorn**: ASGI server for running the FastAPI application
- **CORS Middleware**: Cross-origin resource sharing support for frontend integration

### Development Tools
- **Pydantic**: Data validation and serialization
- **Python Standard Library**: File system operations, logging, and async operations

The architecture is designed to be modular and extensible, with clear separation between code analysis, AI documentation generation, and API handling components.