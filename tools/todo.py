import json
import os
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_ai.tools import ToolDefinition

TODO_FILE = "todos.json"

def todo_list(working_directory: str) -> str:
    """List all todos"""
    try:
        todo_path = os.path.join(working_directory, TODO_FILE)
        if not os.path.exists(todo_path):
            return "No todos found"
        
        with open(todo_path, 'r') as f:
            todos = json.load(f)
        
        if not todos:
            return "No todos found"
        
        result = "Todos:\n"
        for i, todo in enumerate(todos, 1):
            status = "✓" if todo.get("done", False) else "○"
            result += f"{i}. {status} {todo['task']}\n"
        
        return result.strip()
    except Exception as e:
        return f"Error: {e}"

def todo_add(working_directory: str, task: str) -> str:
    """Add a new todo"""
    try:
        todo_path = os.path.join(working_directory, TODO_FILE)
        
        todos = []
        if os.path.exists(todo_path):
            with open(todo_path, 'r') as f:
                todos = json.load(f)
        
        todos.append({"task": task, "done": False})
        
        with open(todo_path, 'w') as f:
            json.dump(todos, f, indent=2)
        
        return f"Added: {task}"
    except Exception as e:
        return f"Error: {e}"

def todo_done(working_directory: str, index: int) -> str:
    """Mark todo as done"""
    try:
        todo_path = os.path.join(working_directory, TODO_FILE)
        if not os.path.exists(todo_path):
            return "No todos found"
        
        with open(todo_path, 'r') as f:
            todos = json.load(f)
        
        if index < 1 or index > len(todos):
            return f"Invalid todo number: {index}"
        
        todos[index - 1]["done"] = True
        
        with open(todo_path, 'w') as f:
            json.dump(todos, f, indent=2)
        
        return f"Marked done: {todos[index - 1]['task']}"
    except Exception as e:
        return f"Error: {e}"

def todo_remove(working_directory: str, index: int) -> str:
    """Remove a todo"""
    try:
        todo_path = os.path.join(working_directory, TODO_FILE)
        if not os.path.exists(todo_path):
            return "No todos found"
        
        with open(todo_path, 'r') as f:
            todos = json.load(f)
        
        if index < 1 or index > len(todos):
            return f"Invalid todo number: {index}"
        
        task = todos.pop(index - 1)["task"]
        
        with open(todo_path, 'w') as f:
            json.dump(todos, f, indent=2)
        
        return f"Removed: {task}"
    except Exception as e:
        return f"Error: {e}"

class TodoParams(BaseModel):
    """Parameters for the todo tool."""
    action: Literal["list", "add", "done", "remove"] = Field(
        description="Action to perform: 'list', 'add', 'done', 'remove'"
    )
    task: str | None = Field(
        default=None,
        description="Task description (required for 'add')"
    )
    index: int | None = Field(
        default=None,
        description="Todo number (required for 'done' and 'remove')",
        gt=0
    )


todo_tool_definition = ToolDefinition(
    name="todo",
    description="""Task management tool for tracking progress on complex tasks.

Usage:
- Use 'add' to create new tasks when starting multi-step work
- Use 'done' to mark tasks complete and track progress
- Use 'list' to see current task status
- Use 'remove' to clean up irrelevant tasks
- Essential for breaking down complex tasks into manageable steps""",
    parameters_json_schema=TodoParams.model_json_schema(),
)

def todo(working_directory: str, action: str, task: str | None = None, index: int | None = None) -> str:
    """Main todo function"""
    if action == "list":
        return todo_list(working_directory)
    elif action == "add":
        if not task:
            return "Error: Task required for add action"
        return todo_add(working_directory, task)
    elif action == "done":
        if not index:
            return "Error: Index required for done action"
        return todo_done(working_directory, index)
    elif action == "remove":
        if not index:
            return "Error: Index required for remove action"
        return todo_remove(working_directory, index)
    else:
        return f"Error: Unknown action '{action}'"