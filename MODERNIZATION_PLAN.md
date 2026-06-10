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

- [x] Run full pytest suite — **158/158 passed** (2026-06-09). Actual invocation: `PYTHONPATH=$(pwd) desktop/.venv/bin/pytest backend/tests/ --ignore=backend/tests/test_requests.py --ignore=backend/tests/test_transactions.py` (venv lives at `desktop/.venv`, Python 3.11.14; the two ignored files are stale ad-hoc scripts that hit a live server at import time; the 7 `TestAuthEndpoints` tests in `test_password_migration.py` require a live backend on :8000 — started one with `DATABASE_FILE=/tmp/btctx-baseline/test_backend.db`, production DB untouched)
- [x] Run `./scripts/pre-commit.sh` — **10/10 static checks passed** (2026-06-09); API test section skipped due to a pre-existing bug: `check_backend_running()` in `pre_commit_tests.py` does an unauthenticated GET to `/api/accounts/` and requires `r.ok`, but all routers are auth-protected (401) so detection can never succeed. ~~Fix detection in Phase 2~~ — **investigated in Phase 2, deliberately NOT fixed**: enabling the API section would shell out to `test_backdated_fifo.py`, which sends `DELETE /api/transactions/delete_all` to whatever backend runs on :8000 — a production-wipe hazard (same bug class as the pre-Feb-2026 incident). Equivalent coverage lives in the isolated pytest suite. Recommend (future, with user sign-off): convert `test_backdated_fifo.py` to TestClient and delete stale `test_requests.py`/`test_transactions.py` scripts, then re-enable. Run with `PATH=desktop/.venv/bin:$PATH` so the script's `python3`/`uvicorn` resolve to the venv.
- [x] Generate baseline PDFs into `baseline-pdfs/` (gitignored) — done 2026-06-09. Contents: `complete_tax_report_2024.pdf` (4pp), `irs_reports_2024.pdf` (4pp, pdftk-filled), `transaction_history_2024.pdf` (1p), `transaction_history_2024.csv`, plus pypdf-extracted `.txt` for each PDF and `seed_template.csv` (frozen snapshot of the 18-tx import template). **Gate = `./baseline-pdfs/regen_and_diff.sh`** (the authoritative, self-contained recipe: temp DB on :8001, seeds from the frozen CSV, regenerates + text-diffs all three reports; exit 0 = match; verified deterministic 2026-06-09 pre-change; script + seed CSV are git-tracked, generated artifacts are not). Production DB never touched.
- [x] [GATE] All tests green and baseline PDFs saved before ANY code change — **PASSED 2026-06-09** (pytest 158/158, pre-commit static 10/10, baselines + extracted text + seed CSV saved)

### Phase 1 — Conservative dependency updates

- [x] Read `docs/MAINTENANCE.md` in full before touching any dependency (done 2026-06-09 — exact pinning policy, fastapi/pydantic/starlette coupled, reportlab+pypdf are PDF-risk packages, bcrypt 72-byte handling already mitigated)
- [x] Audit `backend/requirements.txt` (2026-06-09, web-verified + local pip-audit cross-check). Targets: fastapi 0.121.3 (smallest line admitting starlette <0.50; 0.118 yield-exit timing change is benign here), explicit starlette==0.49.3 (fixes CVE-2025-62727 HIGH Range-header DoS in StaticFiles + CVE-2025-54121 upload DoS; CVE-2026-48710 needs starlette 1.x — deferred, app doesn't do path checks in middleware), pydantic HOLD 2.12.5 (2.13 serializer rework still shaking out w/ fastapi#15466), uvicorn 0.49.0, sqlalchemy 2.0.50, requests ==2.34.2 (exact-pin per policy; CVE-2026-25645), python-multipart 0.0.32 (CVE-2026-42561 HIGH + 2 more; app has upload endpoints), python-dotenv 1.2.2 (CVE-2026-28684), python-dateutil 2.9.0.post0, pytest 8.4.2 (last 8.x; CVE-2025-71176 fixed only in 9.0.3 — dev-only, acceptable residual, 9.x is follow-up), reportlab 4.4.10 NOT 4.5.x (4.4.8/4.4.10 ship un-CVE'd security fixes; 4.5.x changes acroform/color behavior = PDF drift risk), **majors:** cryptography 46.0.7 (CVE-2026-26007 HIGH EC subgroup + stale bundled OpenSSL; AES/PBKDF2 backup code untouched by removals), pypdf 6.13.1 (~20 DoS CVEs fixed only in 6.x; 6.0 breakage = Py3.8 drop + pre-5.x deprecations only; app uses only PdfReader/PdfWriter/add_page). bcrypt/httpx/itsdangerous already latest. NOTE: several targets require Python ≥3.10 runtime — already true of current pin uvicorn 0.40.0; Docker + venv run 3.11; Py3.9 constraint is source-syntax only (pre-commit checks it).
- [x] Audit `desktop/requirements.txt` (2026-06-09): pyinstaller 6.20.0 (routine maintenance; no advisories), pywebview 6.2.1 (6.2.1 fix is Windows-only; no advisories; verify save_file bridge at next .app build). Bump floors to tested versions.
- [x] Audit `frontend/package.json` (2026-06-09, web-verified). Decisions: react/react-dom stay 18.3.1 (final 18.x, no advisories); **vite ^6.4.3** (6.2.5 has 4 dev-server CVEs incl. GHSA-p9ff-h696-f583, fixed 6.4.2; 6.4 is the v6 security-backport branch); **axios ^1.17.0** (CVE-2026-25639 proto-pollution DoS on ≤1.13.4; verify lockfile never resolves pulled-malicious 1.14.1); **react-router-dom ^7.17.0** (SPA open-redirect/XSS fixed in 7.12.0); react-hook-form ^7.78.0; typescript ~5.9.3 (final 5.x; TS 6 is breaking — skip); typescript-eslint ^8.61.0; eslint + @eslint/js ^9.39.4 (ESLint 10 deferred); @vitejs/plugin-react ^4.7.0 (last 4.x, supports Vite 6); eslint-plugin-react-refresh ^0.4.26; @types/node ^22.19.20, @types/react ^18.3.31, @types/react-dom ^18.3.7; **remove @types/react-router-dom** (v5-only, RR7 ships own types); keep eslint-plugin-react-hooks ^5.2.0 and globals ^15.15.0 (v6/v7 and v16/v17 reshape configs for no benefit).
- [x] Apply backend patch/minor bumps (2026-06-09): fastapi 0.121.3, starlette==0.49.3 (new explicit pin), uvicorn 0.49.0, sqlalchemy 2.0.50, requests==2.34.2, python-multipart 0.0.32, python-dotenv 1.2.2, python-dateutil 2.9.0.post0, reportlab 4.4.10, pytest 8.4.2; pydantic held at 2.12.5. Full suite **158/158** + PDF gate **PASS**.
- [x] Apply backend major bumps one at a time (2026-06-09): cryptography 46.0.7 (158/158 + encrypted backup/restore roundtrip verified, 19 tx intact) committed `a84a83e`; pypdf 6.13.1 (158/158 + PDF gate PASS) committed separately. Deferred majors recorded in MAINTENANCE.md: pytest 9, ESLint 10, starlette 1.x, TS 6, cryptography 47/48, reportlab 4.5.x.
- [x] Apply frontend patch/minor bumps (2026-06-09): all audit targets applied incl. vite 6.4.3, axios 1.17.0, react-router-dom 7.17.0, TS 5.9.3; removed obsolete @types/react-router-dom; `npm audit fix` cleared 3 transitive advisories (flatted/postcss/rollup) → 0 vulnerabilities. `npm run lint` ✅ (0 errors; 2 pre-existing app-source warnings: exhaustive-deps in TransactionForm.tsx:267, only-export-components in ToastContext.tsx:107). `npm run build` ✅ (tsc -b + vite build, 129 modules).
- [x] Apply desktop requirement bumps (2026-06-09): pyinstaller >=6.20.0, pywebview >=6.2.1 (floors raised to tested versions; installed in venv). Note: .app rebuild + save_file bridge smoke test deferred to next desktop build per docs/MACOS_DESKTOP_APP.md.
- [x] Update `docs/MAINTENANCE.md` (2026-06-09): all version tables refreshed, new "Deferred Updates" section (pytest 9, starlette 1.x, pydantic 2.13, cryptography 47/48, reportlab 4.5.x, TS 6, ESLint 10, React 19/Vite 7+ with unblock conditions), fastapi coupling notes updated to 0.121.x.
- [x] [GATE] Phase 1 gate **PASSED 2026-06-09**: pytest 158/158, pre-commit static 10/10, PDF baseline gate PASS (all three reports + CSV text-identical).
- [x] Review-fix-reverify cycle (2026-06-09): 3 passes. Pass 1 (/simplify, 4 agents): applied — gate script committed via gitignore negation + frozen-snapshot comments, compare() function dedup, single NAMES list, parallel curl -Z, scoped+anchored timestamp filter, removed dead constructs, MAINTENANCE.md version-agnostic pin example + reportlab rationale dedup, plan recipe dedup; skipped (noted) — rewrite-as-pytest/TestClient (pipeline must stay identical to baseline generation; effort-temporary tool). Pass 2: caught `grep -vE '^$'` blank-line stripping that could mask page-boundary drift → never-match filter. Pass 3: caught BSD-grep `$^` matching blank lines → `x^` (verified under BSD grep + ugrep); all else ZERO FINDINGS — converged. Gate re-run PASS + 158/158 after each pass.
- [x] Commit Phase 1 work in logical groups: frontend deps `ad7a57a`, backend patch/minor `bafa083`, cryptography `a84a83e`, pypdf `1f6bf60`, docs/desktop/gate-tooling (final commit of this group).

### Phase 2 — Backend quality pass (behavior-preserving only)

- [x] Read `docs/STARTOS_COMPATIBILITY.md` (2026-06-09): DATABASE_FILE env var is sacred, no hardcoded paths, persistent data only under /data, temp files via tempfile OK, coordinate wrapper repo on any port/path/env change (none planned).
- [x] Pass through `backend/routers/` (2026-06-09): user.py — removed duplicate local `get_db` (now imports backend.database.get_db), removed 3 debug prints, hoisted inline User import; bitcoin.py — removed unused imports, absolute import style; calculation.py — removed unused HTTPException; debug.py — removed unused Transaction import, extracted `_ledger_entry_dict` (was copy-pasted twice); transaction.py — list comprehension, removed misleading body-return on 204 delete_all; csv_import.py — extracted `_read_validated_csv` (extension/size/empty checks were copy-pasted in preview+execute, identical messages/order preserved); reports.py — removed unused Dict import + dead `user_id` query params; account.py — added `db: Session` type hints. Verified: 158/158 + PDF gate PASS.
- [x] Pass through `backend/services/` except transaction.py + reports/ (2026-06-09): calculation.py — replaced root-logger `logging.basicConfig` with module logger, deduplicated 4 copy-pasted deposit-source blocks into one data-driven block (identical semantics incl. per-source warning text), fixed N+1 in `get_all_account_balances` (one grouped sum query instead of per-account queries), hoisted repeated `tx.type.lower()`; backup.py — prints → module logger, removed unused InvalidKey import; account.py — bare `except:` → `except Exception:`; csv_import.py — `raise e` → `raise` (preserves traceback); user.py + bitcoin.py services — clean, no changes (bitcoin.py's explicit per-provider fallback chains left intentionally verbose). Verified: 158/158 + PDF gate PASS.
- [x] Pass through `backend/models/` (2026-06-09, schema untouched — dead code only): transaction.py — removed unused `enum`/`datetime` imports + commented-out TransactionType enum block; account.py — removed legacy `AccountType` enum (only reference was the `__init__.py` re-export; frontend's AccountType is an unrelated TS type); `__init__.py` re-export updated; user.py clean. Verified: 158/158.
- [x] High-risk: `backend/services/transaction.py` (2026-06-09, minimal diffs): removed 3 unused imports (requests, Optional, TransactionCreate) and the no-op `new_tx.group_id = new_tx.id` (group_id is not a model column and is read nowhere). FIFO/ledger logic untouched. `remove_lot_usage_for_tx` kept (docstring marks it intentionally retained). Verified: 158/158 immediately after.
- [x] High-risk: `backend/services/reports/` (2026-06-09, minimal diffs): form_8949.py — removed root-logger basicConfig, unused `io` import, and two functions with ZERO callers (`fill_8949_multi_page` 110 lines, dead since the router took over page-chunking; kept `map_schedule_d_fields` and wired routers/reports.py to call it instead of its inline 13-line duplicate — one source of truth for year-specific SD field mapping); pdf_utils.py — removed commented-out Ghostscript block; complete_tax_report.py + transaction_history.py — removed basicConfig, demoted one per-row INFO log to debug; pdftk_filler.py, pdftk_path.py, reporting_core.py — clean, untouched. Verified: 158/158 + PDF gate PASS immediately after. ALSO: investigated pre-commit API-section detection bug — see Phase 0 note (left disabled on purpose; destructive-test hazard).
- [x] [GATE] Phase 2 gate **PASSED 2026-06-09**: pytest 158/158, pre-commit static 10/10, PDF gate PASS. **Gate hardening during this phase:** discovered the IRS-report baseline has an inherent live dependency — Transfer-BTC-fee disposals are valued via `get_btc_price()` (CoinGecko → Kraken fallback), and when CoinGecko's history endpoint 401s (rate limit) the Kraken price differs by ~3¢, shifting 4 fee-disposal rows + 2 Schedule D totals. Verified the variant is deterministic (two runs byte-identical) and code-independent (same code had passed minutes earlier). Captured it as `baseline-pdfs/irs_reports_2024.alt.txt` (git-tracked); gate now accepts exactly the two verified provider variants, nothing else.
- [x] Review-fix-reverify cycle (2026-06-09): Pass 1 = /simplify with 4 agents (reuse/simplification/efficiency/altitude). Applied: transaction_history.py N+1 fix (was 4 Account queries per row in the report loop — accounts now prefetched once into a dict); calculation.py parallel `deposit_usd`/`deposit_btc` dicts (no magic indices), removed no-op `.lower()` on fee parse, `sums.get(id, Decimal)` default, YTD gain now a scalar SUM query (was hydrating all YTD disposal objects); debug.py dedup completed (`_lot_dict`/`_disposal_dict` + selectinload, response shapes preserved incl. no lot_id in get_one_lot disposals); `_require_auth` intent docstrings (altitude reviewer established these are deliberately session-only on backup/import — NOT duplicates of the dual-mode router auth; consolidation would widen API-key access); form_8949.py trailing newline; stale-doc annotation in docs/2025_FORM_UPDATE_PLAN.md. Pass 2 = convergence (inline after a subagent session-limit): verified all fixes complete, swept every changed file for unused imports → one finding (unused ACCOUNT_WALLET import in csv_import.py), fixed; re-sweep clean. Gates re-run green after each pass.
- [x] Commit Phase 2 work (single commit, 2026-06-09)
- [x] Write a concise backend-changes summary for the user — presented in chat at end of Goal Run 1
- [x] ⏸ WAIT FOR USER — backend diff summary presented. END OF GOAL RUN 1 (2026-06-09). User reviews before Run 2.

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
| 2026-06-09 | Goal Run 1 complete: Phases 0-2 done. pytest 158/158, pre-commit static 10/10, PDF gate PASS (incl. new alt baseline for price-provider variance). Awaiting user review of backend summary. |
