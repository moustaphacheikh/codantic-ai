import os
from agent_loop import AgentLoop
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()
console = Console()

def main():
    """Run the agentic loop."""
    # Create welcome message
    title = Text("🤖 AI Agent Loop, q to quit", style="bold cyan")
    
    welcome_panel = Panel(
        f"{title}",
        border_style="bright_blue",
        padding=(1, 2),
        title="[bold]Welcome[/bold]",
        title_align="center"
    )
    
    console.print("\n")
    console.print(welcome_panel)
    console.print()
    
    # Create code directory if it doesn't exist
    code_dir = './code'
    if not os.path.exists(code_dir):
        os.makedirs(code_dir)
        console.print(f"📁 Created working directory: {code_dir}")
    
    agent = AgentLoop(working_directory=code_dir)
    agent.loop()


if __name__ == "__main__":
    main()

 