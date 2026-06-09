# BTCTX 2026 Modernization Checklist

> **State file for /goal-driven work.** Each session: find the first unchecked task, complete it fully, check it off, commit.
> Rules: `[GATE]` tasks require the full pytest suite + listed checks green before checking off.
> `⏸ WAIT FOR USER` means STOP — present the requested material and end the goal run.
> All work stays on `feature/2026-modernization`. Never push to any remote without explicit user instruction.
> Approved plan reference: `~/.claude/plans/you-are-suppose-to-hazy-music.md`
>
> **Constraints (from user):** Conservative dependency updates (patch/minor + low-risk majors only; stay on React 18 / Vite 6; keep Python 3.9 compat). UI = polish existing dark theme, not redesign. Never break PDF generation. Respect `docs/STARTOS_COMPATIBILITY.md` — no database/path/env changes.

---

## Goal Run 1 — Phases 0–2

### Phase 0 — Baseline (no code changes)

- [ ] Run full pytest suite: `.venv/bin/pytest backend/tests/ -v --tb=short` from repo root — record pass count (expect 158)
- [ ] Run `./scripts/pre-commit.sh` — record result
- [ ] Generate baseline PDFs into `baseline-pdfs/` (gitignored): complete tax report 2024, IRS forms 2024, transaction history 2024 (CSV + PDF). Use TestClient or a temporarily started backend — do NOT touch the production database. Also save pypdf-extracted text of each PDF as `.txt` next to it for later diffing.
- [ ] [GATE] All tests green and baseline PDFs saved before ANY code change

### Phase 1 — Conservative dependency updates

- [ ] Read `docs/MAINTENANCE.md` in full before touching any dependency
- [ ] Audit `backend/requirements.txt`: for each package, current vs latest version, changelog highlights, security advisories (web search)
- [ ] Audit `desktop/requirements.txt` the same way
- [ ] Audit `frontend/package.json` the same way (React stays 18.x, Vite stays 6.x)
- [ ] Apply backend patch/minor bumps; pin exact versions; run full test suite
- [ ] Apply any low-risk backend major bumps ONE at a time, full test suite after each (skip any that risk Python 3.9 compat or PDF behavior)
- [ ] Apply frontend patch/minor bumps; `npm run build` + `npm run lint` must pass
- [ ] Apply desktop requirement bumps consistent with backend
- [ ] Update `docs/MAINTENANCE.md` with new versions and any new deprecation warnings
- [ ] [GATE] Full pytest suite + `./scripts/pre-commit.sh` + regenerate the three PDFs and diff extracted text vs `baseline-pdfs/` — must match (dates/timestamps excepted)
- [ ] Review-fix-reverify cycle: re-read full Phase 1 diff, run /simplify, fix all findings, re-run gate checks; repeat until a pass yields zero findings
- [ ] Commit Phase 1 work in logical groups (backend deps / frontend deps / docs)

### Phase 2 — Backend quality pass (behavior-preserving only)

- [ ] Read `docs/STARTOS_COMPATIBILITY.md` before starting
- [ ] Pass through `backend/routers/` file by file: dead code, inefficiencies, missing type hints, inconsistent error handling, modern idioms
- [ ] Pass through `backend/services/` (EXCEPT transaction.py and reports/) the same way
- [ ] Pass through `backend/models/` the same way
- [ ] High-risk: `backend/services/transaction.py` — smallest possible diffs, full test suite immediately after
- [ ] High-risk: `backend/services/reports/` (form_8949.py, pdftk_filler.py, pdf_utils.py) — smallest possible diffs, full test suite + PDF baseline diff immediately after
- [ ] [GATE] Full pytest suite + `./scripts/pre-commit.sh` + PDF baseline text diff — all green
- [ ] Review-fix-reverify cycle: re-read full Phase 2 diff, run /simplify, fix all findings, re-run gate checks; repeat until a pass yields zero findings
- [ ] Commit Phase 2 work
- [ ] Write a concise backend-changes summary for the user (what changed per file, why, risk notes)
- [ ] ⏸ WAIT FOR USER — present backend diff summary for review. END OF GOAL RUN 1.

---

## Goal Run 2 — Phase 3 (2025 IRS forms verification)

- [ ] Download current FINAL 2025 Form 8949 and Schedule D (f1040sd) PDFs from irs.gov; confirm they are final (not draft)
- [ ] Compare against bundled `backend/assets/irs_templates/2025/*.pdf`: file content and `pdftk dump_data_fields` field names
- [ ] If bundled templates differ from final IRS releases: replace them; if identical: record that and keep
- [ ] Verify field mappings in `backend/services/reports/` work for 2025 templates (compare 2024 vs 2025 field names); update mappings only if field names changed
- [ ] Add/extend 2025 tax-year tests following `backend/tests/test_pdf_content.py` pattern (form generation + content verification)
- [ ] [GATE] Full pytest suite green including new 2025 tests
- [ ] Review-fix-reverify cycle: re-read Phase 3 diff, run /simplify, fix all findings, re-run gates; repeat until zero findings
- [ ] Generate filled sample 2025 Form 8949 + Schedule D with realistic test data; save paths for user
- [ ] If field mappings changed: note that a minor version bump is required at release (per CLAUDE.md)
- [ ] ⏸ WAIT FOR USER — present filled 2025 PDFs for visual inspection BEFORE committing template/mapping changes. END OF GOAL RUN 2.
- [ ] (After user approval) Commit Phase 3 work

---

## Goal Run 3 — Phases 4–5

### Phase 4 — UI polish (existing theme, not redesign)

- [ ] Use the frontend-design skill. Refine `frontend/src/styles/theme.css` first: typography scale, spacing rhythm, color consistency
- [ ] Polish per-page CSS (app, dashboard, transactions, transactionForm, transactionPanel, reports, settings, login, converter): hover/focus/active states, visual hierarchy, micro-interactions
- [ ] MUST PRESERVE: layout structure, all routes, hooks (`useAccounts`, `useApiCall`, `useBtcPrice`), Toast system, mobile breakpoints (800/768/480px), 44px touch targets, `desktopDownload.ts` pywebview integration
- [ ] Start dev server; browser-verify EVERY page at desktop width: login, dashboard, transactions (incl. create + edit panel), reports (generate a real PDF), settings, sats converter
- [ ] Browser-verify the same pages at mobile widths (800/768/480px)
- [ ] [GATE] `npm run build` + `npm run lint` green; all pages verified working in browser
- [ ] Review-fix-reverify cycle: re-read Phase 4 diff, run /simplify, fix all findings, re-verify in browser; repeat until zero findings
- [ ] Commit Phase 4 work

### Phase 5 — Final QA + docs

- [ ] Full pytest suite + `./scripts/pre-commit.sh`
- [ ] Regenerate all three PDFs and diff extracted text vs `baseline-pdfs/`
- [ ] `npm run build` clean
- [ ] Local Docker build smoke test: `docker build -t btctx-modernization-test .` succeeds (skip push)
- [ ] Update `CLAUDE.md` Recent Changes section
- [ ] Update `docs/CHANGELOG.md`
- [ ] Update `docs/ROADMAP.md` if goals changed
- [ ] [GATE] Everything above green
- [ ] Final review-fix-reverify cycle across the WHOLE branch diff vs develop; repeat until zero findings
- [ ] Remove this file (MODERNIZATION_PLAN.md) in the final commit
- [ ] Commit Phase 5 work
- [ ] ⏸ WAIT FOR USER — present full summary; user reviews UI in browser and decides on merge to develop. Do NOT merge or push. END OF GOAL RUN 3.

---

## Status log

| Date | Session note |
|------|-------------|
| 2026-06-09 | Plan approved; branch + checklist created. Baseline pass counts: pytest TBD, pre-commit TBD. |
