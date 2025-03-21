## backend/services/reports/transaction_history.py

from io import BytesIO
from datetime import datetime, date, timezone
from typing import List, Union
import csv

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

from sqlalchemy.orm import Session

# Import your Transaction ORM model and any needed relationships
from backend.models.transaction import Transaction
from backend.models.account import Account

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_transaction_history_report(
    db: Session,
    year: int,
    output_format: str = "PDF"
) -> Union[bytes, str]:
    """
    Generate a transaction history report for the given year, including:
      - Deposits, Withdrawals, Transfers, Buys, Sells
      - If 'year' is the current year, generate up through today's date
      - Otherwise, generate for the entire calendar year (Jan 1 through Dec 31)
    The report can be exported as PDF or CSV.

    Args:
        db (Session): A SQLAlchemy database session
        year (int): The target year for filtering transactions
        output_format (str): "PDF" or "CSV"

    Returns:
        Union[bytes, str]: PDF bytes if output_format="PDF", or CSV string if output_format="CSV"
    """

    # -------------------------------------------------
    # 1) Determine the date range
    # -------------------------------------------------
    #   If year == current year => from Jan 1 of this year to today's date
    #   Else => from Jan 1 year to Dec 31 year
    # -------------------------------------------------
    today = date.today()
    start_date = datetime(year, 1, 1, tzinfo=timezone.utc)

    if year == today.year:
        end_date = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # -------------------------------------------------
    # 2) Query all relevant transactions
    # -------------------------------------------------
    #   We only want "Deposit", "Withdrawal", "Transfer", "Buy", "Sell".
    # -------------------------------------------------
    valid_types = ("Deposit", "Withdrawal", "Transfer", "Buy", "Sell")
    txns: List[Transaction] = (
        db.query(Transaction)
        .filter(Transaction.type.in_(valid_types))
        .filter(Transaction.timestamp >= start_date)
        .filter(Transaction.timestamp <= end_date)
        .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
        .all()
    )

    # -------------------------------------------------
    # 3) Build a structured list of transaction rows
    # -------------------------------------------------
    #   For PDF/CSV, we’ll show:
    #   Date, Type, FromAccount, ToAccount, Amount, Fee, FeeCurrency,
    #   CostBasisUSD, ProceedsUSD, Purpose
    # -------------------------------------------------
    tx_data_rows = []
    for tx in txns:
        # Look up the from/to account names
        from_acct_name = _get_account_name(db, tx.from_account_id)
        to_acct_name = _get_account_name(db, tx.to_account_id)

        # Convert timestamp to a friendly string
        if tx.timestamp:
            # Convert to ISO-like with 'Z' suffix if it’s UTC
            iso_str = tx.timestamp.isoformat()
            if iso_str.endswith("+00:00"):
                iso_str = iso_str[:-6] + "Z"
            date_str = iso_str
        else:
            date_str = ""

        row = {
            "Date": date_str,
            "Type": tx.type,
            "FromAccount": from_acct_name,
            "ToAccount": to_acct_name,
            "Amount": f"{tx.amount:.8f}" if tx.amount else "0.00000000",
            "Fee": f"{tx.fee_amount:.8f}" if tx.fee_amount else "0.00000000",
            "FeeCurrency": tx.fee_currency if tx.fee_currency else "",
            "CostBasisUSD": f"{tx.cost_basis_usd:.2f}" if tx.cost_basis_usd else "0.00",
            "ProceedsUSD": f"{tx.proceeds_usd:.2f}" if tx.proceeds_usd else "0.00",
            "Purpose": tx.purpose or ""
        }
        tx_data_rows.append(row)

    # -------------------------------------------------
    # 4) Return either PDF bytes or CSV string
    # -------------------------------------------------
    if output_format.upper() == "PDF":
        logger.info("Generating PDF transaction history report...")
        return _build_pdf_report(tx_data_rows, year)
    else:
        logger.info("Generating CSV transaction history report...")
        return _build_csv_report(tx_data_rows, year)


# -------------------------------------------------
# Internal Helpers
# -------------------------------------------------

def _get_account_name(db: Session, account_id: int) -> str:
    """
    Look up the account name by ID. Returns "External" if account_id=99,
    or an empty string if no account is found.
    """
    if not account_id:
        return ""
    if account_id == 99:
        return "External"
    acct = db.query(Account).filter(Account.id == account_id).first()
    return acct.name if acct else f"Account {account_id}"


def _build_pdf_report(tx_data_rows: List[dict], year: int) -> bytes:
    """
    Build a PDF file containing the transaction history for the given year.
    Returns the PDF as bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = styles["Title"]
    normal_style = styles["Normal"]
    heading_style = ParagraphStyle(
        name="Heading1Left",
        parent=styles["Heading1"],
        alignment=0,
        spaceBefore=12,
        spaceAfter=8,
    )
    table_header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        alignment=1,  # center
        fontSize=9,
        leading=11,
        textColor=colors.black,
        spaceAfter=4,
    )
    table_data_style = ParagraphStyle(
        name="TableData",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )

    # Prepare the flowable story
    story = []

    # Cover page or heading
    story.append(Paragraph(f"BitcoinTX - Transaction History for {year}", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Add disclaimers/best-practices note
    disclaimers = (
        "This report provides your transaction history for the specified year, including "
        "all Deposits, Withdrawals, Transfers, Buys, and Sells. All amounts are shown in BTC "
        "(with fees also in BTC or USD as applicable), and cost/proceeds in USD. For IRS "
        "reporting, ensure accuracy and consult a tax professional if needed. This software "
        "follows double-entry accounting principles to track cost basis and disposition events."
    )
    story.append(Paragraph(disclaimers, normal_style))
    story.append(Spacer(1, 0.2 * inch))

    if not tx_data_rows:
        story.append(Paragraph("No transactions found for this period.", normal_style))
        doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    # Table headers
    col_headers = [
        "Date", "Type", "From Account", "To Account",
        "Amount (BTC)", "Fee", "Fee Currency", 
        "Cost Basis (USD)", "Proceeds (USD)", "Purpose"
    ]

    # Build table data
    table_data = [col_headers]  # first row is header
    for row in tx_data_rows:
        table_data.append([
            Paragraph(row["Date"], table_data_style),
            Paragraph(row["Type"], table_data_style),
            Paragraph(row["FromAccount"], table_data_style),
            Paragraph(row["ToAccount"], table_data_style),
            Paragraph(row["Amount"], table_data_style),
            Paragraph(row["Fee"], table_data_style),
            Paragraph(row["FeeCurrency"], table_data_style),
            Paragraph(row["CostBasisUSD"], table_data_style),
            Paragraph(row["ProceedsUSD"], table_data_style),
            Paragraph(row["Purpose"], table_data_style),
        ])

    # Create table object
    col_widths = [
        1.3 * inch, 0.8 * inch, 1.0 * inch, 1.0 * inch,
        0.9 * inch, 0.7 * inch, 0.9 * inch,
        1.0 * inch, 1.0 * inch, 1.0 * inch
    ]
    pdf_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    pdf_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    story.append(pdf_table)
    story.append(Spacer(1, 0.2 * inch))

    # Build the PDF
    doc.build(story, onFirstPage=_on_first_page, onLaterPages=_on_later_pages)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _build_csv_report(tx_data_rows: List[dict], year: int) -> str:
    """
    Build a CSV string for the transaction history.
    """
    output = []
    header = [
        "Date", "Type", "FromAccount", "ToAccount",
        "Amount(BTC)", "Fee", "FeeCurrency",
        "CostBasisUSD", "ProceedsUSD", "Purpose"
    ]
    output.append(header)

    for row in tx_data_rows:
        output.append([
            row["Date"],
            row["Type"],
            row["FromAccount"],
            row["ToAccount"],
            row["Amount"],
            row["Fee"],
            row["FeeCurrency"],
            row["CostBasisUSD"],
            row["ProceedsUSD"],
            row["Purpose"]
        ])

    # Convert list-of-lists to a CSV string
    csv_buffer = BytesIO()
    writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
    for line in output:
        writer.writerow(line)

    csv_str = csv_buffer.getvalue().decode("utf-8", errors="replace")
    csv_buffer.close()
    return csv_str


def _on_first_page(canvas: Canvas, doc):
    """
    Handler for the first page if you want
    to set a title, or skip page numbering.
    """
    pass


def _on_later_pages(canvas: Canvas, doc):
    """
    Handler for subsequent pages to show page numbers.
    """
    page_num = doc.page - 1  # skip numbering on cover
    canvas.setFont("Helvetica", 9)
    canvas.drawString(0.5 * inch, 0.5 * inch, "Generated by BitcoinTX")
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f"{page_num}")
