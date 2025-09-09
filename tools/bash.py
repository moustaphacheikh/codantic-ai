import subprocess
import os
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

def bash(working_directory: str, command: str, audit_log: str, timeout: int = 120, run_in_background: bool = False) -> str:
    try:
        abs_working_dir = os.path.abspath(working_directory)
        
        if run_in_background:
            # Start process in background
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=abs_working_dir
            )
            return f"Command started in background with PID: {process.pid}"
        else:
            # Run command synchronously
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=abs_working_dir
            )
            
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += result.stderr
            
            if result.returncode != 0:
                return f"Command failed with exit code {result.returncode}:\n{output}"
            
            return output if output else ""
    
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return f"Error: Command not found: {command}"
    except PermissionError:
        return f"Error: Permission denied executing: {command}"
    except Exception as e:
        return f"Error: {e}"

class BashParams(BaseModel):
    """Parameters for the bash tool."""
    command: str = Field(
        description="The bash command to execute"
    )
    audit_log: str = Field(
        description="Required: Concise summary of command (min 10 words and max 20) for audit compliance. Like a git commit title - describe WHAT not WHY. Examples: 'Install project dependencies', 'Run unit tests', 'Build production bundle'"
    )
    timeout: int = Field(
        default=120,
        description="Optional timeout in seconds (default 120 seconds, max 600)",
        le=600
    )
    run_in_background: bool = Field(
        default=False,
        description="Set to true to run this command in the background. Default is False"
    )
    


bash_tool_definition = ToolDefinition(
    name="bash",
    description="""Executes bash commands in the working directory with proper error handling.

Usage:
- Commands run in the specified working directory  
- Quote file paths with spaces using double quotes
- Use timeout parameter for long-running commands (max 600 seconds)
- Use run_in_background=True for processes that don't need immediate output
- Explain non-trivial commands before execution for user understanding
- Avoid using commands like 'find', 'grep', 'cat' - use dedicated tools instead

COMPLIANCE: The audit_log parameter is REQUIRED for enterprise audit trails.
Provide a clear, concise summary (min 10 words and max 20) describing the command being executed.
Format like a git commit title: action + target + optional context.
Examples: 'Install npm dependencies', 'Run integration tests', 'Build Docker image'""",
    parameters_json_schema=BashParams.model_json_schema(),
)