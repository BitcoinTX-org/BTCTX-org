# Roadmap

## Current Status: v0.6.0 - 2026 Modernization ✅

Buy from Bank, native macOS desktop app, and the June 2026 modernization pass (deps, 2025 IRS forms, backend cleanup, UI polish). Test suite: 164 pytest tests + pre-commit static checks.

### v0.5.x Features
- **Buy from Bank**: Purchase BTC directly from Bank account (auto-buy/recurring)
- macOS desktop app (.app bundle with embedded backend)
- Mobile responsiveness overhaul (10 CSS files, touch-friendly)
- Comprehensive test suite (stress testing, edge cases, IRS form validation)
- Pre-commit test suite for CI/CD
- Desktop app download fixes (Settings + Reports pages)
- pdftk path resolution for bundled apps

### Previous Releases
- v0.5.0: Backend refactoring, Pydantic V2, dependency updates
- v0.4.0: CSV template import
- v0.3.2: Backup restore session fix
- v0.3.1: StartOS compatibility fixes
- v0.3.0: Multi-year IRS form support (2024/2025)

---

## v0.6.0 - 2026 Modernization Release (shipped 2026-06-10)

Minor bump required by Form 8949 field-mapping changes per CLAUDE.md convention:
- [x] CVE-driven dependency refresh (backend/frontend/desktop; React 18 + Vite 6 retained)
- [x] 2025 IRS form templates verified against final irs.gov releases; fixed
      2025 11-row page capacity + multi-page Part I/II handling
- [x] Behavior-preserving backend cleanup (dead code, duplication, N+1s)
- [x] Dark-theme UI polish (CSS-only; mobile breakpoints + touch targets preserved)
- [x] Test suite grown to 164 tests + PDF baseline regression gate

## Then: v1.0.0 - Production Release

Polish and stabilize for production release.

### v1.0.0 Goals
- [ ] Final QA pass on all features
- [x] ~~2025 IRS form template updates~~ (verified final + fixed, June 2026)
- [ ] Documentation review and updates
- [ ] Performance optimization if needed
- [ ] Test-suite housekeeping (with sign-off): convert `test_backdated_fifo.py`
      to TestClient, delete stale `test_requests.py`/`test_transactions.py`,
      re-enable the pre-commit API section

### Future (Post v1.0.0)
- [ ] CSV import merge with existing data (Phase 2)
- [ ] Column mapping UI for arbitrary exchange CSVs
- [ ] Saved mapping presets for different exchange formats

---

## Future Enhancements

### High Priority
- [ ] **CSV import merge**: Phase 2 - merge with existing data
- [ ] **Improved error handling**: Better user feedback for failed operations

### Medium Priority
- [ ] **Multi-year reports**: Generate reports spanning multiple tax years
- [ ] **Cost basis methods**: Support LIFO, specific identification (not just FIFO)
- [ ] **Transaction categories**: Tags/labels for transaction organization
- [ ] **Data validation**: Audit tool to verify ledger balance integrity

### Low Priority / Nice-to-Have
- [ ] **Multi-user support**: Separate portfolios for household members
- [ ] **Exchange API sync**: Optional automatic import from exchanges
- [x] ~~**Dark mode**: UI theme toggle~~ (theme system added, dark mode ready to implement)
- [x] ~~**Mobile responsive**: Better mobile layout~~ (completed Jan 2025)

---

## Completed

### January 2025
- [x] **macOS desktop app** - Native .app bundle with PyInstaller + pywebview
- [x] **Comprehensive test suite** - 131 pytest tests + 17 pre-commit checks
  - `test_stress_and_forms.py`: stress testing, edge cases, IRS form validation
  - All deposit sources and withdrawal purposes tested
  - Account-specific FIFO verification
- [x] **Mobile responsiveness overhaul** - 10 CSS files, touch-friendly UI, 44px touch targets
- [x] **Pre-commit test suite** - Docker/StartOS compat, FIFO integrity, report generation
- [x] **Desktop app download fixes** - Settings and Reports pages work in pywebview
- [x] **pdftk path resolution** - Centralized module for macOS desktop compatibility
- [x] **Frontend design system refactor** - Custom hooks, toast notifications, error boundaries, theme system
- [x] **v0.5.0: Backend refactoring** - Pydantic V2, dependency updates, code modernization
- [x] **v0.4.0: CSV template import** - Bulk import with preview and atomic commits
- [x] **v0.3.2: Backup restore fix** - Session clearing and login redirect
- [x] **v0.3.1: StartOS compatibility** - DATABASE_FILE env var, BackgroundTasks cleanup
- [x] **v0.3.0: 2025 IRS form support** - Multi-year form generation working
- [x] **2025 IRS form update planning** - Research and documentation complete
- [x] **StartOS packaging complete** - `.s9pk` tested and working
- [x] Multi-arch Docker image (amd64/arm64) on Docker Hub
- [x] Backdated transaction FIFO recalculation
- [x] Lost BTC capital loss tax treatment fix
- [x] Insufficient BTC validation
- [x] UI responsiveness improvements
- [x] IRS form generation documentation
- [x] Docker container working with PDF generation
- [x] All three report endpoints functional
- [x] Python 3.9 compatibility
- [x] Repository cleanup and branch strategy
- [x] Docker Hub publishing (`b1ackswan/btctx:latest`)
- [x] Documentation structure (`docs/` directory)

---

## Notes

- **Philosophy**: Get basic functionality working first, refine edge cases later
- **Git workflow**: `develop` branch for work, merge to `master` for releases
- **Testing**: Comprehensive automated test suite
  - 131 pytest tests covering transactions, FIFO, edge cases, IRS forms
  - 17 pre-commit checks for Docker/StartOS compatibility
  - Run: `pytest backend/tests/` or `./scripts/pre-commit.sh`
