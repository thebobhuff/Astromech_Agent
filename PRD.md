# Astromech

## Overview
Astromech is a personal AI assistant platform inspired by [OpenClaw](https://github.com/openclaw/openclaw). It aims to provide a unified gateway for AI agents to interact with the user across multiple channels (messaging apps, local devices, web).

## Inspiration
- **Base Project**: OpenClaw (TypeScript/Node.js)
- **Core Concept**: A transparent, channel-agnostic AI agent runner.

## Goals
- Build a "better" version of OpenClaw using Python.
- Focus on Security, Token Efficiency, and Local Capabilities.

## Tech Stack
- **Language**: Python
- **Core**: LangChain, FastAPI
- **LLM Support**: Cloud (Google Gemini) + Local (Ollama/LlamaCPP)

## Key Features (Refined)
1.  **Logical Memory File System**: Memories are stored as human-readable Markdown files in a structured directory (e.g., `data/memories/`), indexed locally by ChromaDB for RAG.
2.  **Visual Dashboard**: API support for a GUI workflow builder.
3.  **Full Local Control**: The agent runs directly on the host machine with full file system and terminal access (No Sandboxing).
4.  **Token Optimization**: Smarter prompting strategies.
5.  **Local-First**: Support for running fully offline models.

The agent has multiple files
SOUL.md - This defines the agents personality as defined by the user.
