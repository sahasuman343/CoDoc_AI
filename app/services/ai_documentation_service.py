import os
import json
from typing import Dict, Any, List
from groq import Groq
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class AIDocumentationService:
    """Service for generating AI-powered documentation and diagrams"""
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        # Using GROQ's fastest model for code analysis
        self.model = "llama-3.1-70b-versatile"
    
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
        """Generate high-level project overview"""
        structure = codebase_data['structure']
        technologies = codebase_data['technologies']
        
        prompt = f"""
        Analyze this codebase and provide a comprehensive project overview:
        
        Project: {structure.name}
        Total Files: {structure.total_files}
        Total Lines of Code: {structure.total_lines}
        Technologies: {', '.join(technologies)}
        
        File Structure:
        {self._format_file_structure(structure)}
        
        Please provide:
        1. Project purpose and functionality
        2. Architecture overview
        3. Key components and their roles
        4. Technology stack analysis
        5. Development patterns used
        
        Format your response as a well-structured markdown document.
        """
        
        response = self.groq_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content or ""
    
    async def _generate_file_documentation(self, codebase_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate documentation for individual files"""
        structure = codebase_data['structure']
        file_docs = {}
        
        # Group files by language for batch processing
        files_by_language = {}
        for file_info in structure.files:
            if file_info.language not in files_by_language:
                files_by_language[file_info.language] = []
            files_by_language[file_info.language].append(file_info)
        
        # Generate documentation for each language group
        for language, files in files_by_language.items():
            if language == 'unknown':
                continue
                
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
            
            return response.choices[0].message.content or "sequenceDiagram\n    participant User\n    participant System\n    User->>System: Request\n    System-->>User: Response"
            
        except Exception as e:
            logger.error(f"Error generating sequence diagram: {str(e)}")
            return "sequenceDiagram\n    participant User\n    participant System\n    User->>System: Request\n    System-->>User: Response"
    
    async def generate_class_diagram(self, codebase_data: Dict[str, Any]) -> str:
        """Generate class diagram using Mermaid syntax"""
        logger.info("Generating class diagram")
        
        structure = codebase_data['structure']
        technologies = codebase_data['technologies']
        
        # Focus on object-oriented languages
        oo_files = [f for f in structure.files if f.language in ['python', 'java', 'javascript', 'typescript', 'cpp', 'csharp']]
        
        prompt = f"""
        Based on this codebase analysis, create a class diagram that shows the main classes and their relationships:
        
        Project: {structure.name}
        Object-Oriented Files: {', '.join([f.path for f in oo_files[:15]])}
        Technologies: {', '.join(technologies)}
        
        Generate a Mermaid class diagram that shows:
        1. Main classes/entities
        2. Class relationships (inheritance, composition, association)
        3. Key methods and properties
        4. Interfaces (if applicable)
        
        Return only the Mermaid class diagram syntax, starting with:
        classDiagram
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            return response.choices[0].message.content or "classDiagram\n    class MainClass {\n        +method()\n    }"
            
        except Exception as e:
            logger.error(f"Error generating class diagram: {str(e)}")
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