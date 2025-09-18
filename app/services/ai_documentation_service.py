import os
import json
import re
from typing import Dict, Any, List
from groq import Groq
from app.utils.logger import setup_logger
from dotenv import load_dotenv  # Import dotenv

# Load environment variables from .env file
load_dotenv()

logger = setup_logger(__name__)

class AIDocumentationService:
    """Service for generating AI-powered documentation and diagrams"""
    
    def __init__(self):
        # Fetch GROQ_API_KEY from environment variables
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Using GROQ's fastest available model for code analysis
        self.model = "llama-3.3-70b-versatile"
    
    async def generate_documentation(self, codebase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive documentation for the codebase"""
        logger.info("Generating AI documentation")
        
        try:
            # Generate project overview
            overview = await self._generate_project_overview(codebase_data)
            
            # Generate file-specific documentation
            file_docs = await self._generate_file_documentation(codebase_data)
            
            return {
                "overview": overview,
                "files": file_docs
            }
            
        except Exception as e:
            logger.error(f"Error generating documentation: {str(e)}")
            raise
    
    async def _generate_project_overview(self, codebase_data: Dict[str, Any]) -> str:
        """Generate high-level project overview using actual code analysis"""
        structure = codebase_data['structure']
        technologies = codebase_data['technologies']
        code_analysis = codebase_data.get('code_analysis', {})
        
        # Extract actual code documentation from files
        documented_files = [f for f in structure.files if f.documentation]
        code_summaries = "\n".join([f.documentation for f in documented_files[:10]])
        
        prompt = f"""
        Analyze this codebase and provide a comprehensive project overview based on actual code content:
        
        Project: {structure.name}
        Total Files: {structure.total_files}
        Total Lines of Code: {structure.total_lines}
        Technologies: {', '.join(technologies)}
        
        Code Analysis Summary:
        - Total Classes: {code_analysis.get('total_classes', 0)}
        - Total Functions: {code_analysis.get('total_functions', 0)}
        - Total Imports: {code_analysis.get('total_imports', 0)}
        
        File Structure & Code Content:
        {self._format_file_structure_with_code(structure, documented_files)}
        
        Actual Code Structure Analysis:
        {code_summaries}
        
        Based on this ACTUAL CODE CONTENT analysis, provide:
        1. Project purpose and functionality (inferred from actual code structure)
        2. Architecture overview (based on classes, modules, and dependencies)
        3. Key components and their roles (from actual classes and functions)
        4. Technology stack analysis (from imports and file types)
        5. Development patterns used (from code structure)
        6. Main data flow and interactions (from function calls and imports)
        
        Format your response as a well-structured markdown document.
        """
        
        response = self.groq_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content or ""
    
    async def _generate_file_documentation(self, codebase_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate documentation for individual files using actual code content"""
        structure = codebase_data['structure']
        file_docs = {}
        
        # First, use pre-parsed documentation for files that have it
        for file_info in structure.files:
            if file_info.documentation:
                file_docs[file_info.path] = file_info.documentation
        
        # For files without documentation, generate basic summaries
        undocumented_files = [f for f in structure.files if not f.documentation and f.language != 'unknown']
        
        # Group undocumented files by language for batch processing
        files_by_language = {}
        for file_info in undocumented_files:
            if file_info.language not in files_by_language:
                files_by_language[file_info.language] = []
            files_by_language[file_info.language].append(file_info)
        
        # Generate documentation for undocumented files
        for language, files in files_by_language.items():
            # Process files in batches of 10
            for i in range(0, len(files), 10):
                batch = files[i:i+10]
                batch_docs = await self._generate_batch_documentation(batch, language)
                file_docs.update(batch_docs)
        
        return file_docs
    
    async def _generate_batch_documentation(self, files: List, language: str) -> Dict[str, str]:
        """Generate documentation for a batch of files"""
        file_list = "\n".join([
            f"- {f.path} ({f.lines} lines, {f.size} bytes)"
            for f in files
        ])
        
        prompt = f"""
        Generate concise documentation for these {language} files:
        
        {file_list}
        
        For each file, provide:
        1. Purpose and functionality (1-2 sentences)
        2. Key components/functions/classes
        3. Dependencies and relationships
        
        Return your response as JSON in this format:
        {{
            "filename1": "documentation...",
            "filename2": "documentation..."
        }}
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            return result
            
        except Exception as e:
            logger.warning(f"Error generating batch documentation: {str(e)}")
            # Return empty documentation for files in this batch
            return {f.path: "Documentation generation failed" for f in files}
    
    async def generate_sequence_diagram(self, codebase_data: Dict[str, Any]) -> str:
        """Generate sequence diagram using Mermaid syntax"""
        logger.info("Generating sequence diagram")
        
        structure = codebase_data['structure']
        technologies = codebase_data['technologies']
        
        prompt = f"""
        Based on this codebase analysis, create a sequence diagram that shows the main flow of the application:
        
        Project: {structure.name}
        Technologies: {', '.join(technologies)}
        Key Files: {', '.join([f.path for f in structure.files[:20]])}
        
        Generate a Mermaid sequence diagram that shows:
        1. Main user interactions
        2. Key system components
        3. Data flow between components
        4. External service calls (if any)
        
        Return only the Mermaid sequence diagram syntax, starting with:
        sequenceDiagram
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            if response.choices[0].message.content:
                content = response.choices[0].message.content
                # Extract content inside ```mermaid ... ```
                match = re.search(r"```mermaid\s*([\s\S]*?)```", content)
                if match:
                    mermaid_code = match.group(1).strip()
                    # print(mermaid_code)
            
            return mermaid_code or "sequenceDiagram\n    participant User\n    participant System\n    User->>System: Request\n    System-->>User: Response"
            
        except Exception as e:
            logger.error(f"Error generating sequence diagram: {str(e)}")
            return "sequenceDiagram\n    participant User\n    participant System\n    User->>System: Request\n    System-->>User: Response"
    
    async def generate_class_diagram(self, codebase_data: Dict[str, Any]) -> str:
        """Generate class diagram using actual parsed code structure"""
        logger.info("Generating class diagram")
        
        structure = codebase_data['structure']
        technologies = codebase_data['technologies']
        code_analysis = codebase_data.get('code_analysis', {})
        
        # Focus on object-oriented languages with actual code structure
        oo_files = [f for f in structure.files if f.language in ['python', 'java', 'javascript', 'typescript', 'cpp', 'csharp'] and f.documentation]
        
        # Extract actual class information from documented files
        actual_classes = []
        for file_info in oo_files:
            if 'Classes' in file_info.documentation:
                actual_classes.append(f"From {file_info.path}: {file_info.documentation}")
        
        classes_info = "\n".join(actual_classes[:10])  # Limit to prevent token overflow
        
        prompt = f"""
        Based on ACTUAL PARSED CODE STRUCTURE, create a class diagram that shows the main classes and their relationships:
        
        Project: {structure.name}
        Total Classes Found: {code_analysis.get('total_classes', 0)}
        Object-Oriented Files: {len(oo_files)}
        Technologies: {', '.join(technologies)}
        
        ACTUAL CLASS STRUCTURE (parsed from code):
        {classes_info}
        
        Based on this REAL CODE ANALYSIS, generate a Mermaid class diagram that shows:
        1. Actual classes found in the code (with their real names)
        2. Class relationships (inferred from imports and usage)
        3. Key methods found in the code
        4. Inheritance patterns (if detected)
        
        Return only the Mermaid class diagram syntax, starting with:
        classDiagram
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            # Initialize mermaid_code with a default value
            mermaid_code = "classDiagram\n    class MainClass {\n        +method()\n    }"

            # Check if the response contains valid content
            if response and response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                # Extract content inside ```mermaid ... ```
                match = re.search(r"```mermaid\s*([\s\S]*?)```", content)
                if match:
                    mermaid_code = match.group(1).strip()

            return mermaid_code

        except Exception as e:
            logger.error(f"Error generating class diagram: {str(e)}")
            # Return default class diagram in case of an error
            return "classDiagram\n    class MainClass {\n        +method()\n    }"
    
    def _format_file_structure(self, structure) -> str:
        """Format file structure for AI prompt"""
        lines = []
        
        # Add directories
        for directory in structure.directories[:20]:  # Limit to first 20
            lines.append(f"📁 {directory}/")
        
        # Add files grouped by language
        files_by_lang = {}
        for file_info in structure.files:
            lang = file_info.language or 'other'
            if lang not in files_by_lang:
                files_by_lang[lang] = []
            files_by_lang[lang].append(file_info)
        
        for lang, files in files_by_lang.items():
            lines.append(f"\n{lang.upper()} files:")
            for file_info in files[:10]:  # Limit files per language
                lines.append(f"  📄 {file_info.path} ({file_info.lines} lines)")
        
        return "\n".join(lines)
    
    def _format_file_structure_with_code(self, structure, documented_files) -> str:
        """Format file structure including actual code content"""
        lines = []
        
        # Add directories
        for directory in structure.directories[:15]:  # Limit to prevent token overflow
            lines.append(f"📁 {directory}/")
        
        # Add files with actual code content
        files_by_lang = {}
        for file_info in structure.files:
            lang = file_info.language or 'other'
            if lang not in files_by_lang:
                files_by_lang[lang] = []
            files_by_lang[lang].append(file_info)
        
        for lang, files in files_by_lang.items():
            lines.append(f"\n{lang.upper()} files:")
            for file_info in files[:8]:  # Reduced limit to prevent token overflow
                if file_info in documented_files and file_info.documentation:
                    # Show actual code structure
                    lines.append(f"  📄 {file_info.path} ({file_info.lines} lines)")
                    lines.append(f"    {file_info.documentation[:200]}...")
                else:
                    lines.append(f"  📄 {file_info.path} ({file_info.lines} lines)")
        
        return "\n".join(lines)