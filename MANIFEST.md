# MANIFEST.md — Hackathon Submission Declaration

- **Target Level:** `hard`
- **Artifact Name:** `llm-code-optimizer`
- **Artifact Component:** `skill/SKILL.md`, `skill/scripts/llm_agent.py`

---

## 🛠️ Artifact Summary & Capabilities

The artifact is an LLM-based autonomous agent (`skill/scripts/llm_agent.py`) capable of:
1. Ingesting machine-readable performance audit reports (`findings.json` or KùzuDB graph anomalies).
2. Generating context-aware refactoring prompts tailored to taxonomy categories **T1–T9**.
3. Refactoring Java 21 & Spring Boot 3 source code to eliminate bottlenecks (N+1 SQL queries, in-memory stream bloat, unbatched loop saves, full entity LOB fetches).
4. Verifying compilation using `mvn test-compile` and unit tests via `mvn test`.
5. Maintaining audit execution logs in `runlog/agent_run.log`.

---

## ✋ Manual Work Declaration

- **Manual vs Agent Modifications:**
  - All source code refactorings in `src/main/java/com/example/badhibernate/service/` can be executed autonomously by `skill/scripts/llm_agent.py`.
  - Profiling graph data structure and KùzuDB analyzers in `skill/scripts/analyzers/` were constructed as part of the analysis framework.

---

## ⚙️ Configuration & Environment Changes

- `spring.jpa.open-in-view` is strictly maintained as `false`.
- No changes made to API response schemas or public contract definitions.
- External dependencies: None required beyond Python standard library and JDK 21 / Maven. Optional `kuzu` package for graph analysis.
