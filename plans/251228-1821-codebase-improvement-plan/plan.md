---
title: "Codebase Improvement Plan"
description: "Address critical fixes, modularization, frontend improvements, and testing gaps from comprehensive code review"
status: pending
priority: P1
effort: 32h
branch: feature/vision-alignment-v1
tags: [refactor, backend, frontend, testing, tech-debt]
created: 2025-12-28
---

# Codebase Improvement Plan

## Overview

Plan addressing findings from comprehensive codebase audit (2025-12-28). Current state: **production-ready** but with maintainability concerns. Focus: file size violations, DRY compliance, testing gaps.

## Key Findings

### Backend
- 3 files exceed 200 LOC limit: `stages.py` (898), `extraction.py` (811), `quality_gate.py` (645)
- 2 integration files large: `perplexity_client.py` (546), `google_drive_docs.py` (519)
- Missing type hints on 20+ functions
- Inconsistent rate limiting across integration clients

### Frontend
- API_URL defined in multiple files (DRY violation)
- Missing fetch timeouts (critical)
- No error state in admin/jobs stores
- Limited test coverage (2 test files)

### Security
- **Zero critical vulnerabilities** (all audits passed)

## Phases

| # | Phase | Priority | Status | Effort | Link |
|---|-------|----------|--------|--------|------|
| 1 | Critical Fixes | P1 | Pending | 4h | [phase-01-critical-fixes.md](./phase-01-critical-fixes.md) |
| 2 | Backend Modularization | P1 | Pending | 12h | [phase-02-backend-modularization.md](./phase-02-backend-modularization.md) |
| 3 | Frontend Improvements | P2 | Pending | 8h | [phase-03-frontend-improvements.md](./phase-03-frontend-improvements.md) |
| 4 | Testing | P2 | Pending | 8h | [phase-04-testing.md](./phase-04-testing.md) |

## Dependencies

- Phase 1 must complete before other phases
- Phases 2-4 can proceed in parallel after Phase 1
- Backend tests (Phase 4) should follow modularization (Phase 2)

## Success Criteria

- [ ] All files under 200 lines
- [ ] Frontend build + lint pass
- [ ] Backend pytest pass
- [ ] No critical findings in re-audit

## Reports Referenced

- `plans/reports/code-reviewer-251228-1459-comprehensive-quality-audit.md`
- `plans/reports/code-reviewer-251228-1819-pipeline-modularization-audit.md`
- `plans/reports/code-reviewer-251228-1819-integration-clients-audit.md`
- `plans/reports/code-reviewer-251228-1819-frontend-comprehensive-review.md`
- `plans/reports/tester-251228-1516-frontend-stores-audit.md`
