import os
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.tools import ToolDefinition

def write(working_directory: str, path: str, content: str, audit_log: str, directory: str = "./", force: bool = False) -> str:
   try:
       abs_working_dir = os.path.abspath(working_directory)
       
       # Handle directory path - if it's relative, make it relative to working_directory
       if not os.path.isabs(directory):
           directory = os.path.join(working_directory, directory)
       
       abs_directory = os.path.abspath(directory)
       if not abs_directory.startswith(abs_working_dir):
           return f'Error: Cannot write to directory "{directory}" as it is outside the permitted working directory'
       
       if not os.path.exists(abs_directory):
           os.makedirs(abs_directory)
       
       filepath = os.path.join(abs_directory, path)
       abs_file_path = os.path.abspath(filepath)
       if not abs_file_path.startswith(abs_working_dir):
           return f'Error: Cannot write file "{filepath}" as it is outside the permitted working directory'
       
       if os.path.exists(abs_file_path) and not force:
           return f"Error: File {abs_file_path} already exists"
       
       with open(abs_file_path, 'w' if force else 'x') as f:
           f.write(content)
       
       return f"Written to {path}"
   
   except FileExistsError:
       return f"Error: File {filepath} already exists"
   except Exception as e:
       return f"Error: {e}"
   
class WriteParams(BaseModel):
    """Parameters for the write tool."""
    path: str = Field(
        description="Name of the file to write"
    )
    content: str = Field(
        description="Content to write to the file"
    )
    audit_log: str = Field(
        description="Required: Concise summary of changes (min 10 words and max 20) for audit compliance. Like a git commit title - describe WHAT not WHY. Examples: 'Add user authentication validation', 'Create database configuration file', 'Initialize project structure'"
    )
    directory: str = Field(
        default="./",
        description="Directory path where the file will be created. Default is current directory"
    )
    force: bool = Field(
        default=False,
        description="Whether to overwrite if file exists. Default is False"
    )
    
    @field_validator('audit_log')
    @classmethod
    def validate_audit_log_length(cls, v: str) -> str:
        words = len(v.strip().split())
        if words > 10:
            raise ValueError(f'Audit log must be maximum 10 words, got {words} words')
        if not v.strip():
            raise ValueError('Audit log cannot be empty')
        return v


write_tool_definition = ToolDefinition(
    name="write",
    description="""Writes content to a file in the local filesystem.

Usage:
- Creates files in the specified directory (defaults to current directory)
- Use force=True to overwrite existing files
- ALWAYS prefer editing existing files over creating new ones
- Read the file first if it exists to understand its current content
- File paths are relative to the working directory

COMPLIANCE: The audit_log parameter is REQUIRED for enterprise audit trails.
Provide a clear, concise summary (min 10 words and max 20) describing the change being made.
Format like a git commit title: action + target + optional context.
Examples: 'Create user configuration file', 'Add database schema definitions'""",
    parameters_json_schema=WriteParams.model_json_schema(),
)