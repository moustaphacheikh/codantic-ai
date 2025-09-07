import os
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

def ls(working_directory: str, directory: str = "./") -> str:
   try:
       abs_working_dir = os.path.abspath(working_directory)
       
       # Handle directory path - if it's relative, make it relative to working_directory
       if not os.path.isabs(directory):
           directory = os.path.join(working_directory, directory)
       
       abs_directory = os.path.abspath(directory)
       if not abs_directory.startswith(abs_working_dir):
           return f'Error: Cannot list directory "{directory}" as it is outside the permitted working directory'
       
       if abs_directory.endswith("/"):
           abs_directory = abs_directory[:-1]
       
       files_list = [
           f"{abs_directory}/{os.path.join(root, filename).replace(abs_directory, '').lstrip(os.path.sep)}"
           for root, dirs, files in os.walk(abs_directory)
           for filename in files
       ]
       
       if not files_list:
           return f"No files found in {directory}"
       
       return "\n".join(files_list)
   
   except FileNotFoundError:
       return f"Error: Directory not found: {directory}"
   except PermissionError:
       return f"Error: Permission denied: {directory}"
   except Exception as e:
       return f"Error: {e}"
   

class LsParams(BaseModel):
    """Parameters for the ls tool."""
    directory: str = Field(
        default="./",
        description="Directory path to list files from"
    )


ls_tool_definition = ToolDefinition(
    name="ls",
    description="""Lists all files in a directory recursively.

Usage:
- Defaults to current directory if no path specified
- Returns full paths for all files found
- Recursively searches subdirectories
- Use before creating files to verify directory structure
- Paths are relative to the working directory""",
    parameters_json_schema=LsParams.model_json_schema(),
)