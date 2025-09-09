# Agent Loop Workflow - Chat & Run Methods

```mermaid
flowchart TD
    A[chat: Start interactive mode] --> B[Get user input]
    B --> C[Call run method]
    
    C --> D["context.append(user_input)"]
    D --> E["response = call_llm(context, tools)"]
    E --> F["context.append(response)"]
    F --> G["tool_call, text = parse(response)"]
    
    G --> H{Has tool calls?}
    
    H -->|Yes| I["tool_result = execute(tool_call)"]
    I --> J["context.append(tool_result)"]
    J -.-> E
    
    H -->|No| L[Show response.text]
    
    L --> P[Back to chat loop]
    P --> B
    
    style A fill:#e1f5fe
    style L fill:#c8e6c9
```

## Core Flow

- **chat()**: Interactive loop that gets user input and calls run()
- **run()**: Processes user input through model iterations with tool calling support
- **Tool Loop**: Continues iterating until no more tool calls or max iterations reached