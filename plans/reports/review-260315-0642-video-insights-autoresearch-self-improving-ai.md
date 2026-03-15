# Video Review: "Claude Code + Autoresearch = SELF-IMPROVING AI"

**Video:** [Claude Code + Autoresearch = SELF-IMPROVING AI](https://youtu.be/4Cb_l2LJAW8) by Nick Saraev
**Date:** 2026-03-15
**Purpose:** Extract actionable insights for our Research Agent system

---

## What Is Autoresearch?

Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) pattern: an autonomous loop where an AI agent modifies code, runs experiments, evaluates results, keeps improvements, reverts failures, and repeats — without human intervention.

**Core loop:** `Review state → Pick change → Modify → Commit → Verify → Keep/Revert → Log → Repeat`

Nick Saraev's video explores combining Claude Code with this pattern to create self-improving AI systems.

---

## Key Concepts from the Autoresearch Pattern

### 1. The Autonomous Improvement Loop
- Agent makes ONE focused change per iteration
- Git commit before verification (enables clean revert)
- Mechanical metric determines keep/revert (no subjective judgment)
- Results logged in TSV for trend analysis
- ~12 experiments/hour, ~100 overnight

### 2. Three Configuration Pillars
| Pillar | Description | Example |
|--------|-------------|---------|
| **Scope** | Which files can be modified | `src/**/*.ts` |
| **Metric** | Measurable numerical outcome | `val_bpb`, test pass rate, score |
| **Verify** | Command that extracts metric | `pytest --tb=short \| grep passed` |

### 3. Knowledge Persistence (Not Just Memory)
- **AGENTS.md / CLAUDE.md**: Living handbook of discovered patterns
- **Git history**: Audit trail of what changed and why
- **Progress logs**: Chronological success/failure records
- **Task state files**: Prevent redundant work

### 4. Stateless Iteration (The "Ralph Wiggum" Technique)
Each iteration starts with a clean context slate. Knowledge persists through files, not conversation memory. Prevents hallucination compounding.

---

## Actionable Insights for Our Research Agent

### HIGH VALUE — Direct Application

#### A. Self-Improving Pipeline Quality
**What:** Apply autoresearch loop to our extraction/synthesis pipeline quality.

**How:**
- Define metric: extraction accuracy score, claim verification rate, or quality gate pass rate
- Scope: prompt templates in extraction/synthesis stages
- Loop: modify prompts → run test suite → measure quality score → keep/revert
- Our 960 tests already provide the mechanical verification layer

**Why it matters:** Our prompts are the most impactful lever. Iteratively improving them with measured outcomes > manual prompt engineering.

#### B. Document Quality Scoring
**What:** Add mechanical quality metrics to our output documents (Doc 0-4).

**How:**
- Provenance chain completeness (% of claims with valid source_ids)
- Quote accuracy rate (verified vs unverified)
- Confidence ceiling compliance rate
- Source coverage (% of sources represented in synthesis)
- Run these as post-pipeline validation gates with numerical scores

**Why it matters:** Currently we validate pass/fail. A numerical score enables optimization loops and trend tracking across jobs.

#### C. Cost-Metric Optimization Loop
**What:** Autoresearch pattern applied to API cost reduction.

**How:**
- Metric: quality_score / cost_per_job ratio
- Scope: model selection, prompt length, batch strategies
- Loop: adjust parameters → run pipeline → measure quality/cost → keep/revert

**Why it matters:** We track costs per job already. Formalizing the quality/cost ratio as a metric enables autonomous optimization.

### MEDIUM VALUE — Architectural Patterns to Adopt

#### D. Markdown-as-Interface Pattern
**What:** Karpathy's `program.md` = natural language spec that drives agent behavior.

**Relevance:** We already do this with CLAUDE.md + rules files. But we could formalize pipeline stage behavior as markdown specs that are:
- Human-readable instructions
- Machine-parseable constraints
- Self-documenting for future iterations

#### E. Circuit Breakers & Bounded Iterations
**What:** Stop after N consecutive failures. Cap total iterations.

**Relevance:** Our pipeline should have circuit breakers:
- Stop extraction retries after 3 consecutive LLM failures (not infinite retry)
- Cap total API calls per job based on budget
- Log failure patterns for analysis

#### F. Compound Learning via CLAUDE.md Updates
**What:** After each significant pipeline run, capture learned patterns.

**How:**
- Track which prompt modifications improved quality
- Document failure patterns (e.g., "GPT-4o-mini hallucinates speaker attribution in panel discussions")
- Auto-update operational knowledge after N runs

### LOWER VALUE — Worth Noting

#### G. Security Audit Loop
The [autoresearch skill](https://github.com/uditgoenka/autoresearch) includes a security variant using STRIDE + OWASP frameworks for autonomous security scanning. Could be applied to our API endpoints periodically.

#### H. Planner-Worker Hierarchy
For multi-source extraction, a planner agent could optimize source processing order (highest-ceiling sources first, parallel extraction of independent sources). We already do source isolation — this adds intelligent orchestration.

---

## What We Should NOT Do

- **Don't add autoresearch as a feature** — it's a development methodology, not a user-facing feature
- **Don't optimize subjective metrics** — Goodhart's Law applies; only optimize mechanical, well-defined scores
- **Don't remove human review checkpoints** — autonomous iteration works best with periodic human validation
- **Don't over-engineer the loop** — start with prompt optimization on existing test suite before building infrastructure

---

## Recommended Next Steps

1. **Define quality metrics** for extraction output (numerical, not pass/fail)
2. **Create a prompt optimization script** that runs pipeline tests and measures quality score
3. **Add quality/cost ratio tracking** to job completion data
4. **Document learned patterns** from pipeline runs in a structured format

---

## Sources

- [Karpathy's autoresearch repo](https://github.com/karpathy/autoresearch)
- [Claude Autoresearch Skill](https://github.com/uditgoenka/autoresearch)
- [Self-Improving Coding Agents — Addy Osmani](https://addyosmani.com/blog/self-improving-agents/)
- [How to Build an AI Research Agent — DEV.to](https://dev.to/max_quimby/how-to-build-an-ai-research-agent-that-works-while-you-sleep-karpathys-autoresearch-method-2nmd)
- [AINews: Autoresearch — Latent Space](https://www.latent.space/p/ainews-autoresearch-sparks-of-recursive)
- [Karpathy's 630-line script — The New Stack](https://thenewstack.io/karpathy-autonomous-experiment-loop/)
