#!/bin/bash
# PDF baseline gate check for the 2026 modernization effort.
# Starts a throwaway backend on :8001 with a fresh temp DB, seeds it with the
# frozen seed_template.csv, regenerates the three 2024 reports, extracts text
# with pypdf, and diffs against the Phase 0 baseline (generation timestamp
# excluded). Production database is never touched.
#
# seed_template.csv is a frozen snapshot of GET /api/import/template taken
# 2026-06-09 — do not regenerate it, or the baselines stop being comparable.
# The pypdf extraction below (page texts joined with "=== PAGE BREAK ===") is
# likewise frozen: it must match the format the Phase 0 baseline .txt files
# were created with.
#
# Usage: ./baseline-pdfs/regen_and_diff.sh
# Exit 0 = PDFs match baseline; non-zero = drift detected (or setup failure).

set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="$REPO/baseline-pdfs"
WORK="$(mktemp -d /tmp/btctx-pdfgate.XXXXXX)"
PORT=8001
API="http://127.0.0.1:$PORT/api"
PY="$REPO/desktop/.venv/bin/python"
UVICORN="$REPO/desktop/.venv/bin/uvicorn"
NAMES=(complete_tax_report_2024 irs_reports_2024 transaction_history_2024)

trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

DATABASE_FILE="$WORK/gate.db" PYTHONPATH="$REPO" "$UVICORN" backend.main:app --port $PORT > "$WORK/uvicorn.log" 2>&1 &
BACKEND_PID=$!

curl -s --retry 60 --retry-delay 1 --retry-connrefused -o /dev/null "$API/protected"

curl -sf -c "$WORK/cookies.txt" -X POST "$API/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"password"}' > /dev/null

IMPORT_RESULT=$(curl -sf -b "$WORK/cookies.txt" -X POST "$API/import/execute" \
    -F "file=@$BASE/seed_template.csv;type=text/csv")
echo "Seed import: $IMPORT_RESULT"

# -Z: the four downloads are independent; fetch them in parallel.
curl -sfZ -b "$WORK/cookies.txt" \
    "$API/reports/complete_tax_report?year=2024" -o "$WORK/complete_tax_report_2024.pdf" \
    "$API/reports/irs_reports?year=2024" -o "$WORK/irs_reports_2024.pdf" \
    "$API/reports/simple_transaction_history?year=2024&format=pdf" -o "$WORK/transaction_history_2024.pdf" \
    "$API/reports/simple_transaction_history?year=2024&format=csv" -o "$WORK/transaction_history_2024.csv"

"$PY" - "$WORK" "${NAMES[@]}" <<'EOF'
import sys
from pypdf import PdfReader
work = sys.argv[1]
for name in sys.argv[2:]:
    r = PdfReader(f'{work}/{name}.pdf')
    text = '\n\n=== PAGE BREAK ===\n\n'.join(p.extract_text() for p in r.pages)
    with open(f'{work}/{name}.txt', 'w') as f:
        f.write(text)
EOF

FAIL=0
compare() {  # compare <relative filename> <volatile-line regex or empty>
    local file=$1 filter=${2:-'x^'}  # 'x^' never matches (BSD grep's '$^' matches blank lines): unfiltered files diff verbatim
    if diff <(grep -vE "$filter" "$BASE/$file") \
            <(grep -vE "$filter" "$WORK/$file") > "$WORK/$file.diff"; then
        echo "MATCH  $file"
        return
    fi
    # Transfer-fee disposals are valued via a LIVE historical BTC price fetch
    # (CoinGecko, falling back to Kraken — the two differ by a few cents).
    # A .alt.txt baseline, captured from verified-identical code under the
    # fallback provider, is the only other accepted output.
    local alt="$BASE/${file%.txt}.alt.txt"
    if [ -f "$alt" ] && diff <(grep -vE "$filter" "$alt") \
                             <(grep -vE "$filter" "$WORK/$file") > "$WORK/$file.diff"; then
        echo "MATCH  $file (alt baseline: fallback price provider)"
        return
    fi
    echo "DRIFT  $file — see $WORK/$file.diff"
    FAIL=1
}

# Only the complete tax report embeds its generation timestamp.
compare complete_tax_report_2024.txt '^Date: 20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
compare irs_reports_2024.txt
compare transaction_history_2024.txt
compare transaction_history_2024.csv

if [ $FAIL -eq 0 ]; then
    echo "PDF BASELINE GATE: PASS"
    rm -rf "$WORK"
else
    echo "PDF BASELINE GATE: FAIL (artifacts kept in $WORK)"
fi
exit $FAIL
