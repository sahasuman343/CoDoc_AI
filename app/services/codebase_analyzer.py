import os
import git
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser
import asyncio
from app.models.request_models import InputType, FileInfo, ProjectStructure
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CodebaseAnalyzer:
    """Service for analyzing codebases from various sources"""
    
    def __init__(self):
        # Initialize tree-sitter parsers for different languages
        self.python_language = Language(tspython.language())
        self.javascript_language = Language(tsjavascript.language())
        
        self.python_parser = Parser(self.python_language)
        self.js_parser = Parser(self.javascript_language)
        
        # File extensions to language mapping
        self.language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.rs': 'rust',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'objective-c',
            '.pl': 'perl',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.sql': 'sql',
            '.md': 'markdown',
            '.txt': 'text'
        }
        
        # Common binary file extensions to ignore
        self.binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.a', '.lib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.pdf',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.pyc', '.pyo', '.class', '.o', '.obj'
        }
    
    async def analyze_codebase(self, source: str, input_type: InputType) -> Dict[str, Any]:
        """Main method to analyze a codebase"""
        logger.info(f"Starting analysis of {input_type}: {source}")
        
        try:
            if input_type == InputType.GITHUB_URL:
                return await self._analyze_github_repo(source)
            elif input_type == InputType.LOCAL_PATH:
                return await self._analyze_local_path(source)
            else:
                raise ValueError(f"Unsupported input type: {input_type}")
        except Exception as e:
            logger.error(f"Error analyzing codebase: {str(e)}")
            raise
    
    async def _analyze_github_repo(self, github_url: str) -> Dict[str, Any]:
        """Analyze a GitHub repository"""
        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp()
        
        try:
            logger.info(f"Cloning repository: {github_url}")
            # Clone the repository
            repo = git.Repo.clone_from(github_url, temp_dir)
            
            # Analyze the cloned repository
            result = await self._analyze_directory(temp_dir)
            result['source'] = github_url
            result['source_type'] = 'github'
            
            return result
            
        except Exception as e:
            logger.error(f"Error cloning/analyzing GitHub repo: {str(e)}")
            raise
        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def _analyze_local_path(self, local_path: str) -> Dict[str, Any]:
        """Analyze a local directory"""
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Path does not exist: {local_path}")
        
        if not os.path.isdir(local_path):
            raise ValueError(f"Path is not a directory: {local_path}")
        
        result = await self._analyze_directory(local_path)
        result['source'] = local_path
        result['source_type'] = 'local'
        
        return result
    
    async def _analyze_directory(self, directory_path: str) -> Dict[str, Any]:
        """Analyze directory structure and files"""
        files = []
        directories = []
        total_lines = 0
        technologies = set()
        
        # Walk through directory
        for root, dirs, filenames in os.walk(directory_path):
            # Skip common directories to ignore
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', 'venv', 'env', 'build', 'dist',
                'target', '.git', '.svn', '.hg'
            }]
            
            # Add directories to list
            for dir_name in dirs:
                relative_dir = os.path.relpath(os.path.join(root, dir_name), directory_path)
                directories.append(relative_dir)
            
            # Analyze files
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, directory_path)
                
                # Skip hidden files and common ignore patterns
                if filename.startswith('.') or filename.endswith('.log'):
                    continue
                
                file_info = await self._analyze_file(file_path, relative_path)
                if file_info:
                    files.append(file_info)
                    total_lines += file_info.lines
                    
                    if file_info.language:
                        technologies.add(file_info.language)
        
        # Determine project name
        project_name = os.path.basename(directory_path)
        if project_name == '.' or not project_name:
            project_name = "Analyzed Project"
        
        # Create project structure
        structure = ProjectStructure(
            name=project_name,
            files=files,
            directories=directories,
            total_files=len(files),
            total_lines=total_lines
        )
        
        return {
            'structure': structure,
            'technologies': sorted(list(technologies)),
            'total_files': len(files),
            'total_lines': total_lines
        }
    
    async def _analyze_file(self, file_path: str, relative_path: str) -> FileInfo | None:
        """Analyze a single file"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            # Skip binary files
            if file_extension in self.binary_extensions:
                return None
            
            # Get file stats
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # Skip very large files (> 1MB)
            if file_size > 1024 * 1024:
                return None
            
            # Determine language
            language = self.language_map.get(file_extension, 'unknown')
            
            # Count lines for text files
            lines = 0
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = sum(1 for _ in f)
            except Exception:
                # If we can't read as text, skip this file
                return None
            
            return FileInfo(
                path=relative_path,
                type=file_extension,
                size=file_size,
                lines=lines,
                language=language
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {str(e)}")
            return None