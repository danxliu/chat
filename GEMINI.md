# GEMINI.md

## Project Overview
This is a Python-based AI agent application named `agent`. It leverages the `LiteLLM` library for universal LLM interactions and tool calling. The project uses `pydantic-settings` for robust configuration management via environment variables.

### Main Technologies
- **Python**: Core programming language (>=3.11).
- **LiteLLM**: Framework for interacting with multiple LLM providers using a unified OpenAI-compatible API.
- **FastAPI**: Web framework for the API and WebSocket communication.
- **Redis**: For persistent session state and chat history storage.
- **Pydantic / Pydantic Settings**: Data validation and configuration management.
- **uv**: Fast Python package installer and resolver.
- **Frontend**:
    - **Vanilla JS/CSS/HTML**: Core frontend implementation.
    - **Marked.js**: Markdown rendering.
    - **KaTeX**: LaTeX math rendering.
    - **DOMPurify**: HTML sanitization.
    - **Material Symbols**: UI icons.

### Architecture
- `main.py`: The entry point that initializes the FastAPI app and handles WebSockets.
- `workflow.py`: Contains the `AgentExecutor` class, which manages the LLM chat loop. The agent is fully autonomous and will continue looping until it explicitly calls the `finish_task` tool. If the agent sends a message without calling any tools, it receives a hidden system reminder to either continue or finish.
- `agent.py`: Returns the list of available tool functions.
- `agent_factory.py`: Provides default completion arguments for LiteLLM.
- `storage.py`: Manages Redis-based storage for session context and titles using raw JSON.
- `config.py`: Defines the `Settings` model using Pydantic, loading configuration from a `.env` file.

## Building and Running

### Prerequisites
- [devenv](https://devenv.sh/getting-started/) installed on your system.
- A local OpenAI-compatible LLM server running (default expects `http://localhost:13305/v1`).

### Installation & Environment
Enter the development shell. This will automatically sync dependencies using `uv`.
```bash
devenv shell
```

### Configuration
Create a `.env` file in the root directory to override default settings:
```env
LLM_API_BASE=http://localhost:13305/v1
EMBED_API_BASE=http://localhost:8081/v1
API_KEY=your-api-key
MODEL=your-model-name
MAX_TOKENS=8192
TEMPERATURE=0.1
```

### Running the Agent
Inside the `devenv shell`:
```bash
uv run main.py
```

### Testing
- No explicit test suite (e.g., `pytest`) was found in the initial analysis.
- **TODO**: Implement unit tests for agent initialization and configuration loading.

## Development Conventions

### Coding Style
- Follows standard Python (PEP 8) conventions.
- Uses Type Hints for better code clarity and IDE support.
- Configuration is strictly managed through `pydantic-settings`.

### Environment Management
- Uses `uv.lock` for deterministic builds.
- Dependencies are defined in `pyproject.toml`.
