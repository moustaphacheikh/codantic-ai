import re
import os
import glob
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

def grep(
    working_directory: str,
    pattern: str,
    path: str = None,
    include: str = None,
    file_type: str = None,
    ignore_case: bool = False,
    mode: str = "files_with_matches",
    before: int = 0,
    after: int = 0,
    context: int = 0,
    line_number: bool = False,
    count: Optional[int] = None,
    multiline: bool = False
) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        
        if path is None:
            path = working_directory
        elif not os.path.isabs(path):
            path = os.path.join(working_directory, path)
        
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(abs_working_dir):
            return f'Error: Cannot search in path "{path}" as it is outside the permitted working directory'
        
        # Determine files to search
        if include:
            search_pattern = os.path.join(abs_path, include)
        elif file_type:
            type_patterns = {
                "py": "**/*.py",
                "js": "**/*.js",
                "ts": "**/*.{ts,tsx}",
                "java": "**/*.java",
                "go": "**/*.go",
                "rust": "**/*.rs",
                "cpp": "**/*.{cpp,cxx,cc,c}",
                "h": "**/*.{h,hpp}",
            }
            if file_type in type_patterns:
                search_pattern = os.path.join(abs_path, type_patterns[file_type])
            else:
                search_pattern = os.path.join(abs_path, f"**/*.{file_type}")
        else:
            search_pattern = os.path.join(abs_path, "**/*")
        
        files = glob.glob(search_pattern, recursive=True)
        files = [f for f in files if os.path.isfile(f)]
        
        # Compile regex pattern
        flags = re.IGNORECASE if ignore_case else 0
        if multiline:
            flags |= re.MULTILINE | re.DOTALL
        
        regex = re.compile(pattern, flags)
        
        results = []
        file_matches = []
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if multiline:
                    matches = list(regex.finditer(content))
                else:
                    lines = content.split('\n')
                    matches = []
                    for i, line in enumerate(lines):
                        for match in regex.finditer(line):
                            matches.append((i + 1, line, match))
                
                if matches:
                    file_matches.append(file_path)
                    
                    if mode == "content":
                        if multiline:
                            for match in matches:
                                results.append(f"{file_path}: {match.group()}")
                        else:
                            for line_num, line, match in matches:
                                context_lines = []
                                
                                # Add context
                                if context > 0:
                                    before = after = context
                                
                                if before > 0:
                                    start = max(0, line_num - before - 1)
                                    for i in range(start, line_num - 1):
                                        if i < len(lines):
                                            prefix = f"{i+1}-" if line_number else ""
                                            context_lines.append(f"{file_path}:{prefix}{lines[i]}")
                                
                                # Add matching line
                                prefix = f"{line_num}:" if line_number else ""
                                context_lines.append(f"{file_path}:{prefix}{line}")
                                
                                if after > 0:
                                    end = min(len(lines), line_num + after)
                                    for i in range(line_num, end):
                                        if i < len(lines):
                                            prefix = f"{i+1}-" if line_number else ""
                                            context_lines.append(f"{file_path}:{prefix}{lines[i]}")
                                
                                results.extend(context_lines)
                    
                    elif mode == "count":
                        count = len(matches)
                        results.append(f"{file_path}: {count}")
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        if mode == "files_with_matches":
            results = file_matches
        
        if not results:
            return f"No matches found for pattern '{pattern}'"
        
        # Apply count limit
        if count:
            results = results[:count]
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error: {e}"

class GrepParams(BaseModel):
    """Parameters for the grep tool."""
    pattern: str = Field(
        description="The regular expression pattern to search for in file contents"
    )
    path: str | None = Field(
        default=None,
        description="File or directory to search in. Defaults to current working directory"
    )
    include: str | None = Field(
        default=None,
        description="Glob pattern to filter files (e.g. '*.js', '*.{ts,tsx}')"
    )
    file_type: str | None = Field(
        default=None,
        description="File type to search (e.g., 'js', 'py', 'rust', 'go', 'java')"
    )
    ignore_case: bool = Field(
        default=False,
        description="Case insensitive search. Default is False"
    )
    mode: Literal["content", "files_with_matches", "count"] = Field(
        default="files_with_matches",
        description="Output mode: 'content' shows matching lines, 'files_with_matches' shows file paths, 'count' shows match counts"
    )
    before: int = Field(
        default=0,
        description="Number of lines to show before each match (requires mode: 'content')",
        ge=0
    )
    after: int = Field(
        default=0,
        description="Number of lines to show after each match (requires mode: 'content')",
        ge=0
    )
    context: int = Field(
        default=0,
        description="Number of lines to show before and after each match (requires mode: 'content')",
        ge=0
    )
    line_number: bool = Field(
        default=False,
        description="Show line numbers in output (requires mode: 'content')"
    )
    count: Optional[int] = Field(
        default=None,
        description="Limit output to first N lines/entries",
        gt=0
    )
    multiline: bool = Field(
        default=False,
        description="Enable multiline mode where patterns can span lines. Default is False"
    )


grep_tool_definition = ToolDefinition(
    name="grep",
    description="""A powerful search tool for finding patterns in file contents.

Usage:
- Supports full regex syntax for complex pattern matching
- Filter files with file_type parameter (py, js, ts, java, etc.)
- Use case_insensitive=True for flexible matching  
- Returns matching lines with line numbers and file paths
- More efficient than bash grep commands for code search""",
    parameters_json_schema=GrepParams.model_json_schema(),
)