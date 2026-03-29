# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot for answering questions about course materials. Users ask natural-language questions; Claude decides whether to search the vector database or answer from general knowledge, then returns grounded answers with source citations.

This codebase is a learning project — a fork of DeepLearning.AI's RAG curriculum, extended for hands-on experimentation with Claude Code.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the application:**
```bash
./run.sh
# OR
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Access:**
- Web UI: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

**Environment setup** (required before first run):
```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env
```

There are no configured test or lint commands.

## Architecture

The backend is a clean layered system where each module has a single responsibility:

```
Frontend (index.html / script.js)
    │ POST /api/query
    ▼
app.py  ──  FastAPI entry point; loads courses from docs/ at startup; serves frontend
    │
    ▼
rag_system.py  ──  Main orchestrator; wires all components; handles deduplication on re-index
    │
    ├── session_manager.py  ──  In-memory conversation history (last 2 exchanges per session)
    │
    └── ai_generator.py  ──  Claude API wrapper; two-call pattern (tool invocation → final answer)
            │
            └── search_tools.py  ──  Defines search_course_content tool; ToolManager registry
                    │
                    └── vector_store.py  ──  ChromaDB wrapper; two collections: course_catalog + course_content
```

**document_processor.py** handles the offline ingestion path: parses `.txt` files from `docs/`, splits by `Lesson N:` markers, chunks at 800 chars with 100-char overlap, and stores embeddings (local `all-MiniLM-L6-v2` model — no API calls).

### Query lifecycle

1. User question → session lookup → `RAGSystem.query()`
2. Prompt + conversation history sent to Claude with `search_course_content` tool definition
3. Claude either returns a direct answer OR calls the tool with search terms
4. If tool called: vector search in ChromaDB → top-5 chunks returned to Claude
5. Claude writes final answer grounded in retrieved chunks
6. Response + source citations returned to frontend; session history updated

### Document format

Course files in `docs/*.txt` must follow this exact structure (parser is strict):

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[content...]

Lesson 1: [Lesson Title]
...
```

### Key config defaults (`backend/config.py`)

| Setting | Value |
|---|---|
| Model | `claude-sonnet-4-20250514` |
| Embedding model | `all-MiniLM-L6-v2` (local) |
| Chunk size | 800 chars |
| Chunk overlap | 100 chars |
| Max search results | 5 |
| Max conversation history | 2 exchanges |
| Vector DB path | `backend/chroma_db/` |
