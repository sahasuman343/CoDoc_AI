import os
import git
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Node
import asyncio
from app.models.request_models import InputType, FileInfo, ProjectStructure, CodebaseAnalysisRequest
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
    
    async def analyze_codebase(self, request: CodebaseAnalysisRequest) -> Dict[str, Any]:
        """Main method to analyze a codebase with request parameters"""
        logger.info(f"Starting analysis of {request.input_type}: {request.source}")
        
        try:
            if request.input_type == InputType.GITHUB_URL:
                return await self._analyze_github_repo(request)
            elif request.input_type == InputType.LOCAL_PATH:
                return await self._analyze_local_path(request)
            else:
                raise ValueError(f"Unsupported input type: {request.input_type}")
        except Exception as e:
            logger.error(f"Error analyzing codebase: {str(e)}")
            raise
    
    async def _analyze_github_repo(self, request: CodebaseAnalysisRequest) -> Dict[str, Any]:
        """Analyze a GitHub repository"""
        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp()
        
        try:
            logger.info(f"Cloning repository: {request.source}")
            # Clone the repository
            repo = git.Repo.clone_from(request.source, temp_dir)
            
            # Analyze the cloned repository
            result = await self._analyze_directory(temp_dir, request)
            result['source'] = request.source
            result['source_type'] = 'github'
            
            return result
            
        except Exception as e:
            logger.error(f"Error cloning/analyzing GitHub repo: {str(e)}")
            raise
        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def _validate_path_security(self, path: str) -> str:
        """Validate path security and return the real path"""
        # Resolve all symlinks to get the real, canonical path
        try:
            real_path = os.path.realpath(path)
        except (OSError, ValueError) as e:
            raise ValueError(f"Cannot resolve path '{path}': {str(e)}")
        
        # Define allowed base directories with real paths to prevent symlink bypasses
        allowed_base_dirs = [
            os.path.realpath('/workspace'),  # Replit workspace
            os.path.realpath('/home'),       # User home directories
            os.path.realpath('/tmp'),        # Temporary directory
            os.path.realpath('./'),          # Current working directory
        ]
        
        # Validate path using proper path comparison (not string matching)
        path_allowed = False
        for base_dir in allowed_base_dirs:
            try:
                # Use commonpath to check if real_path is within base_dir
                common = os.path.commonpath([real_path, base_dir])
                if common == base_dir:
                    path_allowed = True
                    break
            except ValueError:
                # Paths are on different drives (Windows) or other path errors
                continue
        
        if not path_allowed:
            raise ValueError(f"Access denied: Path '{path}' (resolves to '{real_path}') is not within allowed directories")
        
        # Define forbidden directories with real paths
        forbidden_dirs = [
            os.path.realpath('/etc'),
            os.path.realpath('/proc'),
            os.path.realpath('/sys'),
            os.path.realpath('/dev'),
            os.path.realpath('/root'),
            os.path.realpath('/usr/bin'),
            os.path.realpath('/usr/sbin'),
            os.path.realpath('/sbin'),
            os.path.realpath('/bin'),
            os.path.realpath('/var/log'),
            os.path.realpath('/boot')
        ]
        
        # Check if the real path is within any forbidden directory
        for forbidden_dir in forbidden_dirs:
            try:
                common = os.path.commonpath([real_path, forbidden_dir])
                if common == forbidden_dir:
                    raise ValueError(f"Access denied: Cannot analyze system directory '{forbidden_dir}'")
            except ValueError:
                # Different drives or path errors - safe to continue
                continue
        
        return real_path

    async def _analyze_local_path(self, request: CodebaseAnalysisRequest) -> Dict[str, Any]:
        """Analyze a local directory with comprehensive security validation"""
        local_path = request.source
        
        # Validate the initial path and get the real path
        real_path = self._validate_path_security(local_path)
        
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Path does not exist: {local_path} (resolved to {real_path})")
        
        if not os.path.isdir(real_path):
            raise ValueError(f"Path is not a directory: {local_path} (resolved to {real_path})")
        
        # Use the real path for analysis to prevent symlink confusion
        result = await self._analyze_directory(real_path, request)
        result['source'] = local_path
        result['source_type'] = 'local'
        result['resolved_path'] = real_path
        
        return result
    
    async def _analyze_directory(self, directory_path: str, request: CodebaseAnalysisRequest) -> Dict[str, Any]:
        """Analyze directory structure and files with comprehensive security validation"""
        files = []
        directories = []
        total_lines = 0
        technologies = set()
        file_count = 0
        
        # Walk through directory with security validation for every path
        for root, dirs, filenames in os.walk(directory_path, followlinks=False):  # Don't follow symlinks
            # Validate the current root directory
            try:
                validated_root = self._validate_path_security(root)
            except ValueError as e:
                logger.warning(f"Skipping directory due to security violation: {root} - {e}")
                dirs.clear()  # Don't descend into this directory
                continue
            
            # Filter directories with security validation
            safe_dirs = []
            for d in dirs:
                dir_path = os.path.join(root, d)
                
                # Skip hidden directories and common build/cache directories
                if d.startswith('.') or d in {
                    'node_modules', '__pycache__', 'venv', 'env', 'build', 'dist',
                    'target', '.git', '.svn', '.hg', '.vscode', '.idea'
                }:
                    continue
                
                # Skip symbolic links to prevent symlink attacks
                if os.path.islink(dir_path):
                    logger.debug(f"Skipping symlink directory: {dir_path}")
                    continue
                
                # Validate directory path security
                try:
                    self._validate_path_security(dir_path)
                    safe_dirs.append(d)
                    relative_dir = os.path.relpath(dir_path, directory_path)
                    directories.append(relative_dir)
                except ValueError as e:
                    logger.warning(f"Skipping directory due to security violation: {dir_path} - {e}")
                    continue
            
            # Update the dirs list to only include safe directories
            dirs[:] = safe_dirs
            
            # Analyze files with security validation
            for filename in filenames:
                # Check max_files limit
                if request.max_files and file_count >= request.max_files:
                    logger.info(f"Reached max_files limit of {request.max_files}")
                    break
                    
                file_path = os.path.join(root, filename)
                
                # Skip hidden files and common ignore patterns
                if filename.startswith('.') or filename.endswith('.log'):
                    continue
                
                # Skip symbolic links to prevent symlink attacks
                if os.path.islink(file_path):
                    logger.debug(f"Skipping symlink file: {file_path}")
                    continue
                
                # Validate file path security
                try:
                    self._validate_path_security(file_path)
                except ValueError as e:
                    logger.warning(f"Skipping file due to security violation: {file_path} - {e}")
                    continue
                
                relative_path = os.path.relpath(file_path, directory_path)
                
                file_info = await self._analyze_file(file_path, relative_path, request.include_documentation)
                if file_info:
                    files.append(file_info)
                    total_lines += file_info.lines
                    file_count += 1
                    
                    if file_info.language:
                        technologies.add(file_info.language)
            
            # Break outer loop if max_files reached
            if request.max_files and file_count >= request.max_files:
                break
        
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
            'total_lines': total_lines,
            'code_analysis': await self._extract_code_structure(files)
        }
    
    async def _analyze_file(self, file_path: str, relative_path: str, include_documentation: bool = True) -> FileInfo | None:
        """Analyze a single file with code parsing"""
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
            
            # Read file content
            content = ""
            lines = 0
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.count('\n') + 1
            except Exception:
                # If we can't read as text, skip this file
                return None
            
            # Parse code structure if documentation is requested
            documentation = None
            if include_documentation and language in ['python', 'javascript']:
                code_info = await self._parse_code_structure(content, language)
                if code_info:
                    documentation = self._generate_file_summary(code_info, relative_path, language)
            
            return FileInfo(
                path=relative_path,
                type=file_extension,
                size=file_size,
                lines=lines,
                language=language,
                documentation=documentation
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {str(e)}")
            return None
    
    async def _parse_code_structure(self, content: str, language: str) -> Optional[Dict[str, Any]]:
        """Parse code structure using tree-sitter"""
        try:
            if language == 'python':
                return self._parse_python_code(content)
            elif language == 'javascript':
                return self._parse_javascript_code(content)
            return None
        except Exception as e:
            logger.warning(f"Error parsing {language} code: {str(e)}")
            return None
    
    def _parse_python_code(self, content: str) -> Dict[str, Any]:
        """Parse Python code structure"""
        tree = self.python_parser.parse(bytes(content, 'utf-8'))
        
        classes = []
        functions = []
        imports = []
        
        def traverse_node(node: Node):
            if node.type == 'class_definition':
                class_name = self._get_node_text(node.child_by_field_name('name'), content)
                methods = []
                for child in node.children:
                    if child.type == 'block':
                        for stmt in child.children:
                            if stmt.type == 'function_definition':
                                method_name = self._get_node_text(stmt.child_by_field_name('name'), content)
                                if method_name:
                                    methods.append(method_name)
                if class_name:
                    classes.append({'name': class_name, 'methods': methods})
            
            elif node.type == 'function_definition':
                # Only top-level functions (not methods)
                if node.parent and node.parent.type != 'block' or (node.parent.parent and node.parent.parent.type != 'class_definition'):
                    func_name = self._get_node_text(node.child_by_field_name('name'), content)
                    if func_name:
                        functions.append(func_name)
            
            elif node.type in ['import_statement', 'import_from_statement']:
                import_text = self._get_node_text(node, content)
                if import_text:
                    imports.append(import_text.strip())
            
            for child in node.children:
                traverse_node(child)
        
        traverse_node(tree.root_node)
        
        return {
            'classes': classes,
            'functions': functions,
            'imports': imports
        }
    
    def _parse_javascript_code(self, content: str) -> Dict[str, Any]:
        """Parse JavaScript code structure"""
        tree = self.js_parser.parse(bytes(content, 'utf-8'))
        
        classes = []
        functions = []
        imports = []
        
        def traverse_node(node: Node):
            if node.type == 'class_declaration':
                class_name = self._get_node_text(node.child_by_field_name('name'), content)
                methods = []
                for child in node.children:
                    if child.type == 'class_body':
                        for method in child.children:
                            if method.type == 'method_definition':
                                method_name = self._get_node_text(method.child_by_field_name('name'), content)
                                if method_name:
                                    methods.append(method_name)
                if class_name:
                    classes.append({'name': class_name, 'methods': methods})
            
            elif node.type == 'function_declaration':
                func_name = self._get_node_text(node.child_by_field_name('name'), content)
                if func_name:
                    functions.append(func_name)
            
            elif node.type in ['import_statement', 'import_declaration']:
                import_text = self._get_node_text(node, content)
                if import_text:
                    imports.append(import_text.strip())
            
            for child in node.children:
                traverse_node(child)
        
        traverse_node(tree.root_node)
        
        return {
            'classes': classes,
            'functions': functions,
            'imports': imports
        }
    
    def _get_node_text(self, node: Optional[Node], content: str) -> Optional[str]:
        """Extract text from a tree-sitter node"""
        if not node:
            return None
        return content[node.start_byte:node.end_byte]
    
    def _generate_file_summary(self, code_info: Dict[str, Any], file_path: str, language: str) -> str:
        """Generate a summary of the parsed code structure"""
        summary_parts = [f"{language.title()} file: {file_path}"]
        
        if code_info.get('classes'):
            summary_parts.append(f"Classes ({len(code_info['classes'])}): {', '.join([c['name'] for c in code_info['classes']])}")
        
        if code_info.get('functions'):
            summary_parts.append(f"Functions ({len(code_info['functions'])}): {', '.join(code_info['functions'][:10])}{'...' if len(code_info['functions']) > 10 else ''}")
        
        if code_info.get('imports'):
            summary_parts.append(f"Imports ({len(code_info['imports'])}): {'; '.join(code_info['imports'][:5])}{'...' if len(code_info['imports']) > 5 else ''}")
        
        return " | ".join(summary_parts)
    
    async def _extract_code_structure(self, files: List[FileInfo]) -> Dict[str, Any]:
        """Extract overall code structure from all analyzed files"""
        all_classes = []
        all_functions = []
        all_imports = set()
        
        for file_info in files:
            if file_info.documentation and file_info.language in ['python', 'javascript']:
                # Parse the documentation to extract structure info
                # This is a simplified approach - in a real implementation, we'd store the parsed structure
                if 'Classes' in file_info.documentation:
                    # Extract class info from documentation
                    classes_part = file_info.documentation.split('Classes')[1].split('|')[0] if 'Classes' in file_info.documentation else ""
                    if classes_part:
                        class_names = classes_part.split(':')[1].strip() if ':' in classes_part else ""
                        if class_names:
                            all_classes.extend([{'name': name.strip(), 'file': file_info.path} for name in class_names.split(', ') if name.strip()])
        
        return {
            'total_classes': len(all_classes),
            'total_functions': len(all_functions),
            'total_imports': len(all_imports),
            'classes_by_file': all_classes
        }