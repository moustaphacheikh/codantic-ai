from typing import List
from pydantic_ai.direct import model_request_sync
from pydantic_ai.messages import ModelRequest, ModelMessage, UserPromptPart, SystemPromptPart
from pydantic_ai.models import ModelRequestParameters
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from tools.execute_tool import execute_tool, tools_definitions,icons
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
import os
import json

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


class AgentLoop:
    """Simple agentic loop with conversation history and tool calling."""

    def __init__(self, model_name: str = 'openai/gpt-4.1-mini', working_directory: str = '.'):
        if OPENROUTER_API_KEY is None:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        self.model = OpenAIChatModel(
                model_name,
                provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
            )
        self.working_directory = working_directory
        self.context: List[ModelMessage] = []
        self.max_iterations = 20 # Prevent infinite loops
        self.console = Console()  # Rich console for formatted output
        
        with open('system.txt', 'r') as f:
            system_content = f.read().strip()

        # System prompt to guide the agent - use ModelRequest
        system_message = ModelRequest(
            parts=[
                SystemPromptPart(content=system_content)
            ]
        )
        
        # Add system message to context
        self.context.append(system_message)

    def _display_tool_call(self, part, tool_return_part):
        """Display tool call info in a rich panel."""
        tool_name = getattr(part, 'tool_name', None)
        args = getattr(part, 'args', None)
        content = Text()
        
        # Parse tool result from ToolReturnPart content
        try:
            tool_result = json.loads(tool_return_part.content)
        except (json.JSONDecodeError, TypeError):
            tool_result = {"result": tool_return_part.content}

        # Show args preview for all tools
        if args:
            try:
                # Parse args if it's a string
                if isinstance(args, str):
                    parsed_args = json.loads(args)
                elif isinstance(args, dict):
                    parsed_args = args
                else:
                    parsed_args = {}

                # Show preview of args (excluding audit_log and working_directory)
                args_preview = {k:v for k, v in parsed_args.items()
                                if k not in ['audit_log', 'working_directory']}

                if args_preview:
                    content.append(f"Args: {args_preview}\n", style="dim cyan")
            except (json.JSONDecodeError, TypeError):
                pass
        # Show result with success/error indicator
        if isinstance(tool_result, dict) and 'error' in tool_result:
            content.append("❌ ", style="red")
            content.append(tool_result['error'], style="red")
            border_style = "red"
        elif isinstance(tool_result, dict) and 'output' in tool_result:
            content.append("✅ ", style="green")
            output = tool_result['output']
            if output.strip():
                content.append(output, style="green")
            else:
                content.append("Command completed (no output)", style="green")
            border_style = "blue"
        else:
            audit_log_text = "Tool executed"
            if args:
                try:
                    # Parse args if it's a string
                    if isinstance(args, str):
                        parsed_args = json.loads(args)
                    elif isinstance(args, dict):
                        parsed_args = args
                    else:
                        parsed_args = {}
                    
                    if 'audit_log' in parsed_args:
                        audit_log_text = parsed_args['audit_log']
                except (json.JSONDecodeError, TypeError):
                    pass
            
            content.append(audit_log_text, style="magenta")
            border_style = "blue"
        # Icon selection based on tool type
        panel = Panel(
            content,
            title=f"{icons.get(tool_name, '🔧')} {tool_name.title() if tool_name else ''}",
            title_align="left",
            border_style=border_style,
            padding=(0, 1)
        )
        self.console.print(panel)
    
    def _display_response(self, part):
        """Display response text in a rich panel with markdown formatting."""
        text_content = getattr(part, 'content', str(part))
        markdown = Markdown(text_content)
        response_panel = Panel(
            markdown,
            title="💬 Response",
            title_align="left",
            border_style="green",
            padding=(0, 1)
        )
        self.console.print(response_panel)
    
    def _display_error(self, error_message):
        """Display error message in a rich panel."""
        error_panel = Panel(
            Text(error_message, style="bold red"),
            title="❌ Error",
            title_align="left",
            border_style="red",
            padding=(0, 1)
        )
        self.console.print(error_panel)
    
    def _display_user_input(self, user_input):
        """Display user input in a rich panel."""
        user_panel = Panel(
            Text(user_input, style="white"),
            title="👤 You",
            title_align="left",
            border_style="blue",
            padding=(0, 1)
        )
        self.console.print(user_panel)
    
    def run(self, user_input: str) -> str:
        """Run a complete conversation turn with potential tool calling."""
        # Display user input
        self._display_user_input(user_input)
        
        # Add user input to context as ModelRequest
        user_message = ModelRequest(parts=[UserPromptPart(content=user_input)])
        self.context.append(user_message)
        
        for _ in range(self.max_iterations):
            # Make request to model with current context
            try:
                model_response = model_request_sync(
                    self.model,
                    self.context,
                    model_request_parameters=ModelRequestParameters(
                        function_tools=tools_definitions,
                        allow_text_output=True,
                    ),
                )
                
                # Add model response to context
                self.context.append(model_response)
                
                # Process response parts
                has_tool_calls = False
                tool_return_parts = []
                
                for part in model_response.parts:
                    if hasattr(part, 'tool_name') and part.tool_name:
                        has_tool_calls = True
                        
                        # Execute tool - now returns ToolReturnPart directly
                        tool_return_part = execute_tool(part, self.working_directory)
                        
                        # Display tool call info
                        self._display_tool_call(part, tool_return_part)
                        
                        # Append tool return part for next iteration
                        tool_return_parts.append(tool_return_part)

                    else:
                        # Display response
                        self._display_response(part)
                
                # If there were tool calls, add tool results and continue loop
                if has_tool_calls and tool_return_parts:
                    # Create a ModelRequest with tool return parts
                    tool_message = ModelRequest(parts=tool_return_parts)
                    self.context.append(tool_message)
                    continue  # Continue the loop for model to process tool results
                
                # If no tool calls, we have the final response
                return "Completed"
                
            except Exception as e:
                self._display_error(str(e))
                return f"Error: {str(e)}"
        
        return "Maximum iterations reached."
    
    def chat(self):
        """Interactive chat interface."""

        while True:
            user_input = input("  ").strip()
            print("\033[A\033[K", end="")
            
            # Run the model loop
            self.run(user_input)