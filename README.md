# Codebase Analyzer

An **agentic AI** that understands, reasons about, and explains any software repository. Point it at a codebase and it will autonomously explore the structure, read key files, parse code, inspect Git history, and produce a clear, developer-friendly explanation of how the system works.

Supports **OpenAI**, **Azure OpenAI**, and **HuggingFace** as LLM providers.

## How It Works

The analyzer uses an LLM (GPT-4o by default) in an **agent loop** with access to a suite of tools:

```
┌─────────────┐
│   Developer  │
│   (CLI)      │
└──────┬───────┘
       │ question / "analyze"
       ▼
┌─────────────────────────────────────────┐
│              Agent Loop                  │
│                                          │
│  1. LLM decides which tools to call      │
│  2. Tools execute (filesystem, AST,      │
│     git, search)                         │
│  3. Results feed back to LLM             │
│  4. Repeat until LLM has enough info     │
│  5. LLM produces final answer            │
└─────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│              Tool Suite                   │
│                                           │
│  📁 Filesystem    │  🔍 Code Search       │
│  - directory tree │  - regex grep         │
│  - read files     │  - find symbols       │
│  - find files     │  - find references    │
│  - file summary   │                       │
│                   │                       │
│  🧩 AST Parser    │  📜 Git Metadata      │
│  - Python (ast)   │  - commit history     │
│  - JS/TS (regex)  │  - branches           │
│  - Java (regex)   │  - contributors       │
│  - Go (regex)     │  - file hotspots      │
│  - Rust (regex)   │  - file history       │
└──────────────────────────────────────────┘
```

### Agentic Behaviour

The LLM autonomously decides:

- Which files and folders to inspect first (prioritises high-signal files)
- When to dig deeper vs. when it has enough information
- Which tools to use based on the question being asked
- When to stop exploring and produce the final answer

## Installation

```bash
# Clone and install
cd "Codebase analyzer"
pip install -e .

# Or install dependencies directly
pip install -e ".[dev]"
```

## Configuration

```bash
# Copy the example and fill in the values for your chosen provider
cp .env.example .env
```

### Choosing a Provider

Set `LLM_PROVIDER` (or pass `--provider` on the CLI) to one of:

| Provider     | Value         |
| ------------ | ------------- |
| OpenAI       | `openai`      |
| Azure OpenAI | `azure`       |
| HuggingFace  | `huggingface` |

### Environment Variables

**Shared (all providers)**

| Variable               | Default  | Description                    |
| ---------------------- | -------- | ------------------------------ |
| `LLM_PROVIDER`         | `openai` | Active provider                |
| `MAX_TOKENS`           | `4096`   | Max tokens per LLM response    |
| `MAX_AGENT_ITERATIONS` | `25`     | Max tool-call rounds per query |

**OpenAI** (`LLM_PROVIDER=openai`)

| Variable         | Default      | Description    |
| ---------------- | ------------ | -------------- |
| `OPENAI_API_KEY` | _(required)_ | OpenAI API key |
| `OPENAI_MODEL`   | `gpt-4o`     | Model to use   |

**Azure OpenAI** (`LLM_PROVIDER=azure`)

| Variable                   | Default      | Description                            |
| -------------------------- | ------------ | -------------------------------------- |
| `AZURE_OPENAI_API_KEY`     | _(required)_ | Azure OpenAI API key                   |
| `AZURE_OPENAI_ENDPOINT`    | _(required)_ | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT`  | _(required)_ | Deployment name (used as model)        |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | API version                            |

**HuggingFace** (`LLM_PROVIDER=huggingface`)

| Variable      | Default                                   | Description                                         |
| ------------- | ----------------------------------------- | --------------------------------------------------- |
| `HF_TOKEN`    | _(required)_                              | HuggingFace API token                               |
| `HF_MODEL`    | _(required)_                              | Model ID, e.g. `mistralai/Mistral-7B-Instruct-v0.3` |
| `HF_BASE_URL` | `https://api-inference.huggingface.co/v1` | Override for custom endpoints                       |

> **Note:** HuggingFace tool/function-calling requires a model that supports it (e.g. Mistral-7B-Instruct, Llama-3.1).

## Usage

### Full Repository Analysis

```bash
codebase-analyzer analyze /path/to/repo
```

This will autonomously explore the repository and produce a comprehensive report covering:

- Project overview and tech stack
- Architecture and patterns
- Entry points and key components
- Data flow
- Potential issues and improvement suggestions

### Ask a Specific Question

```bash
codebase-analyzer ask /path/to/repo "Where is authentication handled?"
codebase-analyzer ask /path/to/repo "How does data flow from API to database?"
codebase-analyzer ask /path/to/repo "What are the main entry points?"
```

### Interactive Chat Session

```bash
codebase-analyzer chat /path/to/repo
```

Starts with an initial analysis, then lets you ask follow-up questions interactively.

### Options

```bash
# Choose a provider
codebase-analyzer analyze /path/to/repo --provider azure
codebase-analyzer analyze /path/to/repo --provider huggingface

# Use a specific model / deployment
codebase-analyzer analyze /path/to/repo --model gpt-4o-mini
codebase-analyzer analyze /path/to/repo --provider azure --model my-gpt4o-deployment

# Specify a custom .env file
codebase-analyzer analyze /path/to/repo --env-file /path/to/.env
```

## Project Structure

```
src/analyzer/
├── main.py              # CLI entry point (click)
├── agent.py             # Core agent loop & tool dispatcher
├── config.py            # Configuration from environment
├── tools/
│   ├── filesystem.py    # Directory listing, file reading, glob search
│   ├── ast_parser.py    # Python AST + regex parsers for JS/TS/Java/Go/Rust
│   ├── git_tools.py     # Git metadata extraction
│   └── search.py        # Regex search, symbol finder
├── llm/
│   ├── client.py        # LLM client (OpenAI / Azure OpenAI / HuggingFace)
│   └── prompts.py       # System and task prompts
├── models/
│   └── repository.py    # Data classes for repo profile
└── output/
    └── formatter.py     # Rich terminal output
```

## Supported Languages

| Language              | AST / Structural Analysis                              | Search          |
| --------------------- | ------------------------------------------------------ | --------------- |
| Python                | Full AST (classes, functions, imports, globals)        | ✅              |
| JavaScript/TypeScript | Regex (classes, functions, imports, interfaces, types) | ✅              |
| Java                  | Regex (classes, interfaces, methods, imports)          | ✅              |
| Go                    | Regex (functions, methods, structs, interfaces)        | ✅              |
| Rust                  | Regex (functions, structs, enums, traits, impls)       | ✅              |
| Others                | —                                                      | ✅ (grep-based) |

## Example Output

```
╭──────────────── Analysis Report ────────────────╮
│                                                  │
│  ## Project Overview                             │
│  A Django-based REST API for task management...  │
│                                                  │
│  ## Tech Stack                                   │
│  - Python 3.12, Django 5.0, DRF 3.15            │
│  - PostgreSQL, Redis, Celery                     │
│                                                  │
│  ## Architecture                                 │
│  Layered architecture (MVC via Django):          │
│  - `api/views.py` → HTTP layer                   │
│  - `api/serializers.py` → validation             │
│  - `core/services.py` → business logic           │
│  - `core/models.py` → data layer                 │
│                                                  │
│  ## Entry Points                                 │
│  - `manage.py` → Django CLI                      │
│  - `api/urls.py` → API routes                    │
│  ...                                             │
╰──────────────────────────────────────────────────╯
```

## License

MIT
