import os
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

def glob(working_directory: str, pattern: str, path: str | None = None) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        
        if path is None:
            path = working_directory
        elif not os.path.isabs(path):
            path = os.path.join(working_directory, path)
        
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(abs_working_dir):
            return f'Error: Cannot search in path "{path}" as it is outside the permitted working directory'
        
        # Use pathlib for recursive globbing
        path_obj = Path(abs_path)
        matches = [str(p) for p in path_obj.glob(pattern) if p.is_file()]
        
        if not matches:
            return f"No files found matching pattern '{pattern}' in {path}"
        
        # Sort by modification time (most recent first)
        matches.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
        
        return "\n".join(matches)
    
    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"

class GlobParams(BaseModel):
    """Parameters for the glob tool."""
    pattern: str = Field(
        description="The glob pattern to match files against (e.g., '*.py', '**/*.js', 'src/**/*.ts')"
    )
    path: str | None = Field(
        default=None,
        description="The directory to search in. If not specified, the current working directory will be used"
    )


glob_tool_definition = ToolDefinition(
    name="glob",
    description="""Fast file pattern matching tool for finding files by name patterns.

Usage:
- Supports glob patterns like "**/*.py" or "src/**/*.ts"
- Returns matching file paths sorted by modification time
- More efficient than bash find commands for file discovery
- Use when you need to locate files by name or extension patterns""",
    parameters_json_schema=GlobParams.model_json_schema(),
)