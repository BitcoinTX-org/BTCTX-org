# FILE: backend/routers/reports.py

from fastapi import APIRouter, Depends, Response, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

# Local imports
from backend.database import get_db
from backend.services.reports.reporting_core import generate_report_data
from backend.services.reports.complete_tax_report import generate_comprehensive_tax_report

# NEW IMPORT: use the actual transaction_history.py for PDF
from backend.services.reports.transaction_history import generate_transaction_history_report

reports_router = APIRouter()

# ---------------------------------------------------------
# 1) Complete Tax Report (PDF only)
# ---------------------------------------------------------
@reports_router.get("/complete_tax_report")
def get_complete_tax_report(
    year: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Generates the comprehensive/complete tax report in PDF for the given tax year.
    """
    # 1) Build aggregator data
    report_dict = generate_report_data(db, year)
    # 2) Generate PDF
    pdf_bytes = generate_comprehensive_tax_report(report_dict)
    # 3) Return as PDF download
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CompleteTaxReport_{year}.pdf"'}
    )


# ---------------------------------------------------------
# 2) IRS Reports (Form 8949, Schedule D, etc.) - PDF
# ---------------------------------------------------------
@reports_router.get("/irs_reports")
def get_irs_reports(
    year: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Generates or combines multiple IRS-specific PDFs (Form 8949, Schedule D, etc.)
    into a single PDF. This is just a placeholder example.
    """
    # 1) aggregator data
    report_dict = generate_report_data(db, year)
    # 2) Return placeholder PDF bytes
    pdf_placeholder = b"(Placeholder) IRS Reports PDF for 8949, Schedule D, etc."

    return Response(
        content=pdf_placeholder,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="IRSReports_{year}.pdf"'}
    )


# ---------------------------------------------------------
# 3) Transaction History (CSV or PDF, user-chosen)
# ---------------------------------------------------------
@reports_router.get("/transaction_history")
def get_transaction_history(
    year: int,
    format: str = Query("csv", regex="^(csv|pdf)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Returns the full history of transactions for the given year,
    in CSV or PDF format based on the `format` query param:
      - `?format=csv` (default) => CSV
      - `?format=pdf` => PDF

    Currently, the CSV uses aggregator data from `report_dict`.
    For PDF, we now call `generate_transaction_history_report(...)`
    from 'transaction_history.py'.
    """
    # 1) Generate aggregator data for CSV usage
    report_dict = generate_report_data(db, year)

    # We will collect capital gains and income transactions for CSV
    cg_txs = report_dict.get("capital_gains_transactions", [])
    inc_txs = report_dict.get("income_transactions", [])

    # -----------------------------
    # CASE A: CSV
    # -----------------------------
    if format == "csv":
        lines = ["date,type,asset,amount,cost,proceeds,gain_loss,description"]

        for tx in cg_txs:
            line = (
                f"{tx.get('date_sold','')},"        # date
                f"Sell/Withdrawal,"                 # type
                f"{tx.get('asset','')},"           # asset
                f"{tx.get('amount','')},"          # amount
                f"{tx.get('cost','')},"            # cost
                f"{tx.get('proceeds','')},"        # proceeds
                f"{tx.get('gain_loss','')},"       # gain_loss
                "CapitalGainsTransaction"           # description (placeholder)
            )
            lines.append(line)

        for tx in inc_txs:
            line = (
                f"{tx.get('date','')},"            # date
                f"{tx.get('type','')},"            # type (Income, Reward, etc.)
                f"{tx.get('asset','')},"           # asset (BTC, etc.)
                f"{tx.get('amount','')},"          # amount
                "N/A,"                             # cost
                "N/A,"                             # proceeds
                "N/A,"                             # gain_loss
                f"{tx.get('description','')}"      # description
            )
            lines.append(line)

        csv_data = "\n".join(lines)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="TransactionHistory_{year}.csv"'
            },
        )

    # -----------------------------
    # CASE B: PDF
    # -----------------------------
    else:
        # We now call the actual transaction_history.py for a PDF.
        # This replaces the old placeholder bytes.
        pdf_bytes = generate_transaction_history_report(db, year, output_format="PDF")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="TransactionHistory_{year}.pdf"'
            },
        )
