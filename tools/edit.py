import os
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.tools import ToolDefinition

def edit(working_directory: str, path: str, search: str, replace: str, audit_log: str, global_replace: bool = False) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        abs_file_path = os.path.abspath(os.path.join(working_directory, path))
        if not abs_file_path.startswith(abs_working_dir):
            return f'Error: Cannot edit "{path}" as it is outside the permitted working directory'
        
        with open(abs_file_path, 'r') as f:
            content = f.read()
        
        if search == replace:
            return "Error: search and replace cannot be the same"
        
        if search not in content:
            return f"Error: search text not found in {path}"
        
        if not global_replace and content.count(search) > 1:
            return f"Error: search text appears multiple times in {path}. Use global_replace=True to replace all occurrences"
        
        if global_replace:
            new_content = content.replace(search, replace)
        else:
            new_content = content.replace(search, replace, 1)
        
        with open(abs_file_path, 'w') as f:
            f.write(new_content)
        
        return f"Edited {path}"
    
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"

class EditParams(BaseModel):
    """Parameters for the edit tool."""
    path: str = Field(
        description="The path to the file to modify"
    )
    search: str = Field(
        description="The text to search for"
    )
    replace: str = Field(
        description="The text to replace it with"
    )
    audit_log: str = Field(
        description="Required: Concise summary of changes (min 10 words and max 20) for audit compliance. Like a git commit title - describe WHAT not WHY. Examples: 'Fix null pointer exception', 'Update API endpoint parameters', 'Remove deprecated function calls'"
    )
    global_replace: bool = Field(
        default=False,
        description="Replace all occurrences of search text. Default is False"
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


edit_tool_definition = ToolDefinition(
    name="edit",
    description="""Performs exact string replacements in files.

Usage:
- You must read the file first before editing to see its current content
- The search text must match exactly (including whitespace and formatting)
- If search text appears multiple times, use global_replace=True to replace all
- Use global_replace=True for renaming variables or functions across a file
- The edit will fail if search text is not found or is ambiguous

COMPLIANCE: The audit_log parameter is REQUIRED for enterprise audit trails.
Provide a clear, concise summary (min 10 words and max 20) describing the change being made.
Format like a git commit title: action + target + optional context.
Examples: 'Fix SQL injection vulnerability', 'Update deprecated API calls'""",
    parameters_json_schema=EditParams.model_json_schema(),
)