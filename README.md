# **CoDoc AI**: An AI powered Documentation Generator

## Overview

An AI-powered tool for analyzing codebases and generating documentation, including project overviews, file-specific details, and visual diagrams (sequence and class diagrams). It supports multiple programming languages and integrates with GitHub repositories or local directories.

## Key Features
- **Code Parsing**: Uses tree-sitter to extract classes, functions, imports, and dependencies.
- **AI-Generated Documentation**: Leverages GROQ API for intelligent, context-aware documentation.
- **Visual Diagrams**: Generates Mermaid-based sequence and class diagrams.
- **Flexible Input**: Accepts GitHub URLs or local paths.
- **Secure Analysis**: Validates paths and protects against symlink attacks.
- **Configurable**: Supports parameters like `max_files`, `include_diagrams`, and `include_documentation`.

## Setup and Run

### Prerequisites
- Python 3.8+
- GROQ API Key (set as `GROQ_API_KEY` environment variable)

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd Codebase_doc_maker
   ```
2. Set up a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
      uv sync
   ```

### Running the Application
1. Start the FastAPI server:
   ```bash
   python main.py
   ```
2. Access the API documentation at `http://127.0.0.1:8000/docs`.

3. Start the frontend:
    ```bash
    streamlit run app.py
    ```


## External Dependencies
- **AI Services**: GROQ API for documentation generation.
- **Code Analysis**: tree-sitter for syntax parsing, GitPython for repository operations.
- **Web Framework**: FastAPI with Uvicorn.

## Notes
- Results are stored in-memory; database integration is planned for production.
- Ensure `GROQ_API_KEY` is set in your environment before running the application.