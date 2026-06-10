# File: backend/routers/debug.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models.transaction import BitcoinLot, LotDisposal, LedgerEntry

router = APIRouter()


def _ledger_entry_dict(e: LedgerEntry) -> dict:
    return {
        "id": e.id,
        "transaction_id": e.transaction_id,
        "account_id": e.account_id,
        "amount": str(e.amount),
        "currency": e.currency,
        "entry_type": e.entry_type
    }


def _lot_dict(lot: BitcoinLot) -> dict:
    return {
        "id": lot.id,
        "created_txn_id": lot.created_txn_id,
        "acquired_date": lot.acquired_date,
        "total_btc": str(lot.total_btc),
        "remaining_btc": str(lot.remaining_btc),
        "cost_basis_usd": str(lot.cost_basis_usd),
    }


def _disposal_dict(d: LotDisposal, include_lot_id: bool = True) -> dict:
    result = {
        "id": d.id,
        "lot_id": d.lot_id,
        "transaction_id": d.transaction_id,
        "disposed_btc": str(d.disposed_btc),
        "disposal_basis_usd": str(d.disposal_basis_usd),
        "proceeds_usd_for_that_portion": str(d.proceeds_usd_for_that_portion),
        "realized_gain_usd": str(d.realized_gain_usd),
        "holding_period": d.holding_period
    }
    if not include_lot_id:
        del result["lot_id"]
    return result


@router.get("/lots", tags=["Debug"])
def list_all_lots(db: Session = Depends(get_db)):
    """
    Returns all BitcoinLot records with relevant fields.
    Good for debugging FIFO or cost basis totals.
    """
    lots = db.query(BitcoinLot).options(selectinload(BitcoinLot.lot_disposals)).all()
    return [
        {**_lot_dict(lot), "lot_disposals": [disp.id for disp in lot.lot_disposals]}
        for lot in lots
    ]

@router.get("/lots/{lot_id}", tags=["Debug"])
def get_one_lot(lot_id: int, db: Session = Depends(get_db)):
    """
    Returns a single BitcoinLot with its disposal info.
    """
    lot = db.get(BitcoinLot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found.")

    return {
        **_lot_dict(lot),
        "disposals": [_disposal_dict(disp, include_lot_id=False) for disp in lot.lot_disposals],
    }

@router.get("/disposals", tags=["Debug"])
def list_all_disposals(db: Session = Depends(get_db)):
    """
    Returns all LotDisposal records. Helps debug partial-lot usage.
    """
    disposals = db.query(LotDisposal).all()
    return [_disposal_dict(d) for d in disposals]

@router.get("/ledger-entries", tags=["Debug"])
def list_all_ledger_entries(db: Session = Depends(get_db)):
    """
    Returns all LedgerEntry records for double-entry debugging.
    """
    entries = db.query(LedgerEntry).all()
    return [_ledger_entry_dict(e) for e in entries]

@router.get("/transactions/{tx_id}/ledger-entries", tags=["Debug"])
def transaction_ledger_entries(tx_id: int, db: Session = Depends(get_db)):
    """
    Returns all ledger entries for a given transaction ID.
    """
    entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == tx_id).all()
    if not entries:
        raise HTTPException(status_code=404, detail="No ledger entries found for that TX")
    return [_ledger_entry_dict(e) for e in entries]
