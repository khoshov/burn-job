# 🚀 RUN.md — Instuctions for Running the LLM Code Refactoring Agent

This document explains how to set up, configure, and run the LLM Code Refactoring Agent (`skill/scripts/llm_agent.py`).

---

## 📋 Prerequisites

- **Python 3.10+** (standard library only for core agent; optional `kuzu` for graph queries).
- **JDK 21** & **Apache Maven** installed.

---

## ⚙️ Environment Configuration

### Option A: DeepSeek API Mode

Run directly using CLI parameters:
```bash
python3 skill/scripts/llm_agent.py \
  --api-key "sk-..." \
  --base-url "https://api.deepseek.com" \
  --model "deepseek-chat" \
  --report reports/sandbox/findings.json
```

Or set environment variables:
```bash
export DEEPSEEK_API_KEY="sk-..."
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export LLM_MODEL="deepseek-chat"
```

### Option B: Generic OpenAI-Compatible API Mode (GigaChat / LiteLLM / Ollama)
```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o"
```

### Option C: Offline / Judge Sandbox Mode
No environment variables or API keys required! The agent automatically falls back to its deterministic taxonomy pattern refactoring engine when no API key is set or when `--offline` flag is passed.

---

## 🏃 Execution Commands

### 1. Run LLM Agent with Default Findings Report:
```bash
python3 skill/scripts/llm_agent.py --report reports/sandbox/findings.json
```

### 2. Run LLM Agent in Offline Mode (Judge Sandbox):
```bash
python3 skill/scripts/llm_agent.py --report reports/sandbox/findings.json --offline
```

### 3. Dry-Run (Preview changes without modifying source files):
```bash
python3 skill/scripts/llm_agent.py --report reports/sandbox/findings.json --dry-run
```

### 4. Skip Maven Verification:
```bash
python3 skill/scripts/llm_agent.py --report reports/sandbox/findings.json --no-verify
```

---

## 📊 Viewing Audit Logs

All agent actions, LLM requests, diffs, and Maven compilation results are saved to:
```bash
cat runlog/agent_run.log
```
