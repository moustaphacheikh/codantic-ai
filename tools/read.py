import os
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

MAX_CHARS = 10000

def read(working_directory: str, path: str, skip: int = 0, lines: int | None = None) -> str:
   try:
       abs_working_dir = os.path.abspath(working_directory)
       abs_file_path = os.path.abspath(os.path.join(working_directory, path))
       if not abs_file_path.startswith(abs_working_dir):
           return f'Error: Cannot read "{path}" as it is outside the permitted working directory'
       
       with open(abs_file_path, 'r') as f:
           if skip == 0 and lines is None:
               return f.read(MAX_CHARS)
           
           file_lines = f.readlines()
           start_idx = skip
           
           if start_idx >= len(file_lines):
               return f"Error: Skip value {skip} exceeds file length"
           
           end_idx = start_idx + lines if lines else len(file_lines)
           return ''.join(file_lines[start_idx:end_idx])[:MAX_CHARS]
           
   except FileNotFoundError:
       return f"Error: File not found: {path}"
   except PermissionError:
       return f"Error: Permission denied: {path}"
   except Exception as e:
       return f"Error: {e}"
   

class ReadParams(BaseModel):
    """Parameters for the read tool."""
    path: str = Field(
        description="The path to the file to read, relative to the working directory"
    )
    skip: int = Field(
        default=0,
        description="Number of lines to skip from the beginning (0-indexed). Default is 0",
        ge=0
    )
    lines: int | None = Field(
        default=None,
        description="Number of lines to read. If not specified, reads all remaining lines",
        ge=1
    )


read_tool_definition = ToolDefinition(
    name="read",
    description="""Reads a file from the local filesystem. You can access any file directly by using this tool.

Usage:
- The path parameter is relative to the working directory
- By default, reads the entire file (up to 10,000 characters)
- Use skip parameter to start reading from a specific line (0-indexed)  
- Use lines parameter to limit how many lines to read
- You can call multiple read tools in parallel to examine multiple files efficiently""",
    parameters_json_schema=ReadParams.model_json_schema(),
)