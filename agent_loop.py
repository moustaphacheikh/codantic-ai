from typing import List
from tools.call_functions import tools_definitions, execute_tool
from pydantic_ai.direct import model_request_sync
from pydantic_ai.messages import ModelRequest, ModelMessage, UserPromptPart, SystemPromptPart, ToolReturnPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.usage import RunUsage
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown


class AgentLoop:
    """Simple agentic loop with conversation history and tool calling."""

    def __init__(self, model_name: str = 'google-gla:gemini-2.5-flash', working_directory: str = '.', max_context_tokens: int = 100000, trim_ratio: float = 0.5):
        self.model_name = model_name
        self.working_directory = working_directory
        self.context: List[ModelMessage] = []
        self.max_iterations = 20 # Prevent infinite loops
        self.max_context_tokens = max_context_tokens  # Keep context under token limit
        self.total_usage = RunUsage()  # Track cumulative usage
        self.last_input_tokens = 0  # Track last API input token count
        self.trim_ratio = trim_ratio  # Fraction of messages to keep when trimming (0.5 = 50%)
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
        self.system_messages_count = 1  # Track how many system messages to preserve
    
    def _update_token_usage(self, model_response):
        """Update token usage tracking from API response."""
        # Use the proper incr() method to update usage and increment requests
        self.total_usage.incr(model_response.usage)
        self.total_usage.requests += 1  # RequestUsage doesn't increment requests, so we do it manually
        self.last_input_tokens = model_response.usage.input_tokens or 0
    
    def _get_token_info(self, model_response):
        """Get token usage information as formatted string."""
        request_tokens = model_response.usage.input_tokens or 0
        response_tokens = model_response.usage.output_tokens or 0
        total_tokens = self.total_usage.total_tokens or 0
        return f"📊 Tokens: +{request_tokens} input, +{response_tokens} output (total: {total_tokens})"
    
    def _trim_context(self):
        """Trim context when over token limit, always keep system prompt."""
        if not self.last_input_tokens > self.max_context_tokens and len(self.context) > 1:
            return
            
        # Calculate target: trim_ratio of messages to keep
        target_messages = int(len(self.context) * self.trim_ratio)
        if target_messages < 2:  # Always keep at least system + 1 message
            target_messages = 2
            
        # Remove oldest messages (keep system at index 0)
        messages_to_remove = len(self.context) - target_messages
        for _ in range(messages_to_remove):
            if len(self.context) > 2:  # Keep system + at least 1 message
                self.context.pop(1)  # Remove oldest non-system message
        
        # Display trimming info
        self._display_context_trimming(messages_to_remove, len(self.context))
    
    def _format_args_preview(self, args):
        """Format args for display with length limit."""
        if not args:
            return "{}"
        
        formatted_args = {}
        for key, value in args.items():
            value_str = str(value)
            if len(value_str) > 10:
                formatted_args[key] = value_str[:10] + "..."
            else:
                formatted_args[key] = value_str
        return formatted_args
    
    def _format_result_preview(self, result):
        """Format result for display with length limit."""
        result_str = str(result)
        if len(result_str) > 100:
            return result_str[:97] + "..."
        return result_str
    
    def _display_iteration_info(self, iteration, model_response):
        """Display iteration and token info in a rich panel."""
        token_info = self._get_token_info(model_response)
        iteration_content = Text()
        iteration_content.append(f"Iteration {iteration}\n", style="bold yellow")
        iteration_content.append(token_info, style="cyan")
        
        iter_panel = Panel(
            iteration_content,
            title="💭 Processing",
            title_align="left",
            border_style="yellow",
            padding=(0, 1)
        )
        self.console.print(iter_panel)
    
    def _display_tool_call(self, tool_name, args, result, audit_log=None):
        """Display tool call info in a rich panel with audit log for file operations."""
        content = Text()
        
        # Show audit log as primary description for compliance
        if audit_log:
            content.append(f"{audit_log}\n", style="white")
        
        # Show key context based on tool type
        if tool_name in ['write', 'edit', 'multiedit'] and isinstance(args, dict):
            if 'path' in args:
                content.append("→ ", style="dim")
                content.append(f"{args['path']}\n", style="cyan")
        elif tool_name == 'bash' and isinstance(args, dict):
            if 'command' in args:
                content.append("$ ", style="dim")
                command_preview = args['command']
                if len(command_preview) > 50:
                    command_preview = command_preview[:47] + "..."
                content.append(f"{command_preview}\n", style="cyan")
        elif tool_name in ['read', 'grep', 'glob'] and isinstance(args, dict):
            if 'path' in args:
                content.append("→ ", style="dim")
                content.append(f"{args['path']}\n", style="cyan")
        
        # Show result with success/error indicator
        if isinstance(result, dict) and 'error' in result:
            content.append("❌ ", style="red")
            content.append(result['error'], style="red")
            border_style = "red"
        else:
            content.append("✅ ", style="green")
            if isinstance(result, dict) and 'result' in result:
                content.append(result['result'], style="green")
            else:
                content.append("Success", style="green")
            border_style = "blue"
        
        # Icon selection based on tool type
        icons = {
            'write': '📝',
            'edit': '✏️',
            'multiedit': '📁',
            'bash': '🔧',
            'read': '📖',
            'grep': '🔍',
            'glob': '📂',
            'ls': '📁',
            'todo': '📝'
        }
        icon = icons.get(tool_name, '🔧')
        
        panel = Panel(
            content,
            title=f"{icon} {tool_name.title()}",
            title_align="left",
            border_style=border_style,
            padding=(0, 1)
        )
        self.console.print(panel)
    
    def _display_response(self, text_content):
        """Display response text in a rich panel with markdown formatting."""
        markdown = Markdown(text_content)
        response_panel = Panel(
            markdown,
            title="💬 Response",
            title_align="left",
            border_style="green",
            padding=(0, 1)
        )
        self.console.print(response_panel)
    
    def _display_context_trimming(self, messages_to_remove, total_messages):
        """Display context trimming info in a rich panel."""
        trim_content = Text()
        trim_content.append(f"Trimming context: {self.last_input_tokens} tokens > {self.max_context_tokens} limit\n", style="bold orange1")
        trim_content.append(f"Removed {messages_to_remove} old messages, kept {total_messages} messages", style="bold orange1")
        
        trim_panel = Panel(
            trim_content,
            title="🔄 Context Management",
            title_align="left",
            border_style="orange1",
            padding=(0, 1)
        )
        self.console.print(trim_panel)
    
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
        
        # Trim context to stay within token limits
        self._trim_context()
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Make request to model with current context
            try:
                model_response = model_request_sync(
                    self.model_name,
                    self.context,
                    model_request_parameters=ModelRequestParameters(
                        function_tools=tools_definitions,
                        allow_text_output=True,
                    ),
                )
                
                # Track actual token usage from API
                self._update_token_usage(model_response)
                
                # Add model response to context
                self.context.append(model_response)
                
                # Display iteration and token info
                self._display_iteration_info(iteration, model_response)
                
                # Process response parts
                has_tool_calls = False
                final_text_response = ""
                tool_return_parts = []
                
                for part in model_response.parts:
                    if hasattr(part, 'tool_name') and part.tool_name:
                        has_tool_calls = True
                        
                        # Format args and execute tool
                        args_preview = self._format_args_preview(part.args)
                        tool_result = execute_tool(part, self.working_directory)
                        result_preview = self._format_result_preview(tool_result)
                        
                        # Extract audit log for compliance display
                        audit_log = None
                        if hasattr(part, 'args') and part.args:
                            if isinstance(part.args, dict):
                                audit_log = part.args.get('audit_log')
                            elif hasattr(part.args, 'audit_log'):
                                audit_log = part.args.audit_log
                        
                        # Display tool call info with audit log
                        self._display_tool_call(part.tool_name, part.args, tool_result, audit_log)
                        
                        # Create tool return part
                        tool_return = ToolReturnPart(
                            tool_name=part.tool_name,
                            content=str(tool_result),
                            tool_call_id=getattr(part, 'tool_call_id', 'default')
                        )
                        tool_return_parts.append(tool_return)
                        
                    else:
                        # Text response
                        text_content = getattr(part, 'content', str(part))
                        final_text_response += text_content
                        
                        # Display response
                        self._display_response(text_content)
                
                # If there were tool calls, add tool results and continue loop
                if has_tool_calls and tool_return_parts:
                    # Create a ModelRequest with tool return parts
                    tool_message = ModelRequest(parts=tool_return_parts)
                    self.context.append(tool_message)
                    
                    # Trim context after adding tool results
                    self._trim_context()
                    continue  # Continue the loop for model to process tool results
                
                # If no tool calls, we have the final response
                return final_text_response.strip() if final_text_response else "Task completed."
                
            except Exception as e:
                self._display_error(str(e))
                return f"Error: {str(e)}"
        
        return "Maximum iterations reached."
    
    def loop(self):
        """Interactive chat interface."""

        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                # Clear the prompt line so only the box shows
                print("\033[A\033[K", end="")
                
                if user_input.lower() == 'q':
                    break

                if not user_input:
                    continue

                # Run the agentic loop
                self.run(user_input)
                
            except Exception as e:
                print(f"\n❌ Error: {e}")