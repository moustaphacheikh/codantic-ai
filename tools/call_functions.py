from .read import read, read_tool_definition
from .write import write, write_tool_definition
from .ls import ls, ls_tool_definition
from .edit import edit, edit_tool_definition
from .multiedit import multiedit, multiedit_tool_definition
from .glob import glob, glob_tool_definition
from .grep import grep, grep_tool_definition
from .bash import bash, bash_tool_definition
from .todo import todo, todo_tool_definition

# List of tool definitions for Pydantic AI
tools_definitions = [
    read_tool_definition,
    write_tool_definition,
    ls_tool_definition,
    edit_tool_definition,
    multiedit_tool_definition,
    glob_tool_definition,
    grep_tool_definition,
    bash_tool_definition,
    todo_tool_definition,
]


def execute_tool(function_call_part, working_directory, verbose=False):
    """Execute a function call with the provided arguments."""
    function_map = {
        "read": read,
        "write": write,
        "ls": ls,
        "edit": edit,
        "multiedit": multiedit,
        "glob": glob,
        "grep": grep,
        "bash": bash,
        "todo": todo,
    }
    
    # Pydantic AI uses tool_name attribute, not name
    function_name = function_call_part.tool_name
    if function_name not in function_map:
        return {
            "error": f"Unknown function: {function_name}"
        }
    
    # Add working_directory to args
    # Handle both dict and string args from Pydantic AI
    if isinstance(function_call_part.args, dict):
        args = dict(function_call_part.args)
    elif function_call_part.args is None:
        args = {}
    else:
        # If args is a string, try to parse it as JSON
        import json
        try:
            args = json.loads(function_call_part.args)
        except (json.JSONDecodeError, TypeError):
            args = {}
    
    args["working_directory"] = working_directory
    
    try:
        function_result = function_map[function_name](**args)
        return {"result": function_result}
    except Exception as e:
        return {"error": f"Function execution failed: {str(e)}"}