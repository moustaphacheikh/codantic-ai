import os
from typing import List, Dict
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.tools import ToolDefinition

def multiedit(working_directory: str, path: str, edits: List[Dict[str, str]], audit_log: str) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        abs_file_path = os.path.abspath(os.path.join(working_directory, path))
        if not abs_file_path.startswith(abs_working_dir):
            return f'Error: Cannot edit "{path}" as it is outside the permitted working directory'
        
        with open(abs_file_path, 'r') as f:
            content = f.read()
        
        # Validate all edits first
        for i, edit in enumerate(edits):
            search = edit.get("search", edit.get("old_string", ""))
            replace = edit.get("replace", edit.get("new_string", ""))
            global_replace = edit.get("global_replace", edit.get("replace_all", False))
            
            if search == replace:
                return f"Error: Edit {i+1}: search and replace cannot be the same"
            
            if search not in content:
                return f"Error: Edit {i+1}: search text not found in {path}"
            
            if not global_replace and content.count(search) > 1:
                return f"Error: Edit {i+1}: search text appears multiple times. Use global_replace=True"
        
        # Apply edits sequentially
        current_content = content
        for edit in edits:
            search = edit.get("search", edit.get("old_string", ""))
            replace = edit.get("replace", edit.get("new_string", ""))
            global_replace = edit.get("global_replace", edit.get("replace_all", False))
            
            if global_replace:
                current_content = current_content.replace(search, replace)
            else:
                current_content = current_content.replace(search, replace, 1)
        
        with open(abs_file_path, 'w') as f:
            f.write(current_content)
        
        return f"Applied {len(edits)} edits to {path}"
    
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"

class EditOperation(BaseModel):
    """A single edit operation."""
    search: str = Field(
        description="The text to search for"
    )
    replace: str = Field(
        description="The text to replace it with"
    )
    global_replace: bool = Field(
        default=False,
        description="Replace all occurrences of search text. Default is False"
    )


class MultieditParams(BaseModel):
    """Parameters for the multiedit tool."""
    path: str = Field(
        description="The path to the file to modify"
    )
    edits: List[EditOperation] = Field(
        description="Array of edit operations to perform sequentially"
    )
    audit_log: str = Field(
        description="Required: Concise summary of changes (min 10 words and max 20) for audit compliance. Like a git commit title - describe WHAT not WHY. Examples: 'Refactor authentication module methods', 'Update multiple API endpoint handlers', 'Fix various null pointer exceptions'"
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


multiedit_tool_definition = ToolDefinition(
    name="multiedit",
    description="""Makes multiple targeted edits to a single file efficiently.

Usage:
- Read the file first to understand its current content
- Provide array of edit operations (search and replace pairs)
- All edits are applied sequentially in the order provided
- More efficient than multiple single edit operations
- All edits must succeed or none are applied (atomic operation)

COMPLIANCE: The audit_log parameter is REQUIRED for enterprise audit trails.
Provide a clear, concise summary (min 10 words and max 20) describing the batch changes being made.
Format like a git commit title: action + target + optional context.
Examples: 'Refactor user authentication module', 'Update multiple deprecated function calls'""",
    parameters_json_schema=MultieditParams.model_json_schema(),
)