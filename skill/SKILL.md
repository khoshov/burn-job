---
name: llm-code-optimizer
description: Autonomous LLM-based agent for analyzing Java/Spring performance audit reports, refactoring bottleneck code, and verifying fixes with Maven.
---

# 🤖 LLM Performance Optimization Agent Skill

An automated agent pipeline for detecting and fixing Java 21 & Spring Boot performance antipatterns based on taxonomy rules **T1–T9**.

---

## 📐 Architecture & Workflow

```mermaid
graph TD
    A["Performance Audit Findings Report (findings.json / Graph DB)"] --> B["LLM Agent Orchestrator (skill/scripts/llm_agent.py)"]
    B --> C["Context Builder & Prompt Generator"]
    C --> D{"LLM Provider / API Available?"}
    D -- Yes --> E["Call OpenAI / GigaChat / LiteLLM API"]
    D -- No / Offline --> F["Deterministic Taxonomy Refactoring Engine"]
    E --> G["Extract & Apply Code Edits"]
    F --> G
    G --> H["Maven Build Verification (mvn test-compile)"]
    H -- Pass --> I["Audit Log Update (runlog/agent_run.log)"]
    H -- Fail --> J["Reflect & Retry Code Fix"]
    J --> B
```

---

## 🛠️ Key Capabilities

1. **Taxonomy-Aware Refactoring (T1–T9):**
   - **T1/T6 (Batching):** Replaces single `save()` loops with JDBC `saveAll()`.
   - **T2/T6 (N+1 Queries):** Replaces sub-optimal lazy loops with `JOIN FETCH` JPQL queries.
   - **T3/T4 (Projections):** Replaces heavy full-entity fetches with Spring Data JPA interface projections.
   - **T8/T3 (In-Memory Bloat):** Pushes `WHERE` filtering and `Pageable` pagination to PostgreSQL/H2 database.
2. **Section 7 Non-Defect Rules Protection:**
   - Filters out non-issues (bounded LRU caches, HotSpot field ordering, request-bounded quadratic loops).
3. **Automated Maven Verification Loop:**
   - Verifies all applied patches against `mvn test-compile` to ensure compilation safety.
4. **Audit Log Persistence:**
   - Records step-by-step history to `runlog/agent_run.log`.

---

## 🔌 Qwen Code Integration

This skill is also available as a native [Qwen Code](https://qwenlm.github.io/qwen-code-docs/)
subagent — see `.qwen/agents/perf-findings-agent.md` (specs
[013](../plan/013-qwen-subagent-report.md) / [014](../plan/014-qwen-subagent-fix-mode.md)). By
default it produces a read-only report from `findings.json`; it only applies code fixes if
explicitly asked.
