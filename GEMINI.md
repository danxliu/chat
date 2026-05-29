# GEMINI.md

## Project Overview
This is a Python-based AI agent application named `agent`. It leverages the `llama-index` framework to create a functional agent capable of interacting with an OpenAI-compatible local LLM endpoint. The project uses `pydantic-settings` for robust configuration management via environment variables.

### Main Technologies
- **Python**: Core programming language (>=3.11).
- **LlamaIndex**: Framework for building LLM applications (agent orchestration, LLM integration).
- **Pydantic / Pydantic Settings**: Data validation and configuration management.
- **uv**: Fast Python package installer and resolver.

### Architecture
- `main.py`: The entry point that initializes and executes the agent.
- `agent.py`: Contains the logic for setting up the LLM (`OpenAILike`) and creating the `AgentRunner` with a `FunctionCallingAgentWorker`.
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
API_BASE=http://localhost:13305/v1
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
