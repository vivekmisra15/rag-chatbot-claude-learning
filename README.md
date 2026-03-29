## 🙏 Acknowledgements

This project is based on the original codebase created by
[DeepLearning.AI](https://www.deeplearning.ai/) as part of their RAG chatbot
learning curriculum.

- **Original Repository:** [starting-ragchatbot-codebase](https://github.com/https-deeplearning-ai/starting-ragchatbot-codebase)
- **Original Author:** [DeepLearning.AI](https://github.com/https-deeplearning-ai)
- **Stars:** 307 | **Forks:** 1.8k

The original codebase provides a full-stack Retrieval-Augmented Generation (RAG)
system using ChromaDB for vector storage, Anthropic's Claude for AI-powered
responses, and a Python/FastAPI backend. It served as the foundation and
learning framework for this project.

### What I Built On Top

This fork has been detached from the original repository and extended as an
independent learning project.

All credit for the original architecture, system design, and course materials
goes to the DeepLearning.AI team. If you're learning about RAG systems, I
highly recommend checking out their original repository and courses at
[deeplearning.ai](https://www.deeplearning.ai/).

---

# OBJECTIVE
This project serves as a training codebase for learning Claude Code fundamentals, including understanding an existing codebase, modifying functionality, adding features, and experimenting with testing and development workflows.

# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

