#!/usr/bin/env python3

"""
stress_test.py

A large-scale script to test BitcoinTX with a "scorched earth" approach.
Enhanced with detailed logging, BTC availability checks, and state dumps for debugging.

Key fix: Convert trailing "Z" to "+00:00" so datetime.fromisoformat() won't fail.
"""

import requests
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from requests.exceptions import HTTPError
import logging

# Track last 5 transactions for minimal reproducible case
last_transactions = []

# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:8000"  # Adjust if your API runs elsewhere
DELETE_ALL_ENDPOINT = f"{BASE_URL}/api/transactions/delete_all"

# Account IDs
BANK_ID       = 1  # USD
WALLET_ID     = 2  # BTC
EXCHANGE_USD  = 3  # USD
EXCHANGE_BTC  = 4  # BTC
BTC_FEES      = 5
USD_FEES      = 6
EXTERNAL      = 99

# Test parameters
NUM_RANDOM_TRANSACTIONS = 200
NUM_EDITS = 20
NUM_DELETES = 10

# Date range: ~2 years from base_dt
base_dt = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
end_dt  = base_dt + timedelta(days=700)

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------
def _fix_iso_timestamp(ts_str: str) -> str:
    """Convert 'Z' to '+00:00' for datetime compatibility."""
    if ts_str.endswith('Z'):
        return ts_str[:-1] + "+00:00"
    return ts_str

def delete_all_transactions():
    """Delete all transactions via DELETE /api/transactions/delete_all."""
    logger.info("Deleting all existing transactions...")
    resp = requests.delete(DELETE_ALL_ENDPOINT)
    if resp.status_code in (200, 204):
        logger.info("All transactions cleared successfully.")
    else:
        logger.warning(f"Unexpected status when deleting transactions: {resp.status_code}, {resp.text}")

def get_account_txn_mapping() -> Dict[int, int]:
    """Fetch transactions and map created_txn_id to the relevant account_id (NEW)."""
    url = f"{BASE_URL}/api/transactions"
    resp = requests.get(url)
    if resp.status_code != 200:
        logger.warning(f"Failed to fetch transactions: {resp.status_code}, {resp.text}")
        return {}
    
    txn_map = {}
    for txn in resp.json():
        txn_id = txn["id"]
        tx_type = txn["type"]
        # For Deposits and Buys, the lot is created in to_account_id
        if tx_type in ["Deposit", "Buy"]:
            txn_map[txn_id] = txn["to_account_id"]
        # For Transfers and Withdrawals, the lot might be consumed from from_account_id
        # but we’re interested in where it was created, so we’ll rely on Deposits/Buys for now
    logger.debug(f"Transaction-to-account mapping: {txn_map}")
    return txn_map

def check_btc_availability(account_id: int) -> float:
    """Check available BTC in lots for a given account (MODIFIED)."""
    url = f"{BASE_URL}/api/debug/lots"
    resp = requests.get(url)
    if resp.status_code != 200:
        logger.warning(f"Failed to fetch lots for account {account_id}: {resp.status_code}, {resp.text}")
        return 0.0
    
    # Get transaction-to-account mapping
    txn_map = get_account_txn_mapping()
    if not txn_map:
        logger.warning("Empty transaction map; assuming no BTC available")
        return 0.0
    
    # Filter lots where the created transaction’s account matches account_id
    lots = resp.json()
    relevant_lots = [
        lot for lot in lots 
        if lot["created_txn_id"] in txn_map and txn_map[lot["created_txn_id"]] == account_id and float(lot["remaining_btc"]) > 0
    ]
    total_btc = sum(float(lot["remaining_btc"]) for lot in relevant_lots)
    logger.debug(f"Available BTC for account {account_id}: {total_btc} from lots {relevant_lots}")
    return total_btc

def create_transaction(tx_data: dict) -> dict:
    """Create a transaction via POST /api/transactions with BTC checks."""
    global last_transactions
    url = f"{BASE_URL}/api/transactions"
    
    # Check BTC availability for Withdrawals and Transfers with BTC fees
    if tx_data["type"] in ["Withdrawal", "Transfer"] and tx_data["fee_currency"] == "BTC":
        available_btc = check_btc_availability(tx_data["from_account_id"])
        total_outflow = float(tx_data["amount"]) + float(tx_data["fee_amount"])
        logger.debug(f"Checking TX {tx_data['type']} from {tx_data['from_account_id']}: Need {total_outflow}, Available {available_btc}")
        if total_outflow > available_btc:
            logger.warning(f"Insufficient BTC for TX: {tx_data}")
    
    # Log transaction attempt and add to last_transactions
    logger.debug(f"Creating transaction: {tx_data}")
    last_transactions.append(tx_data)
    if len(last_transactions) > 5:  # Keep last 5 for context
        last_transactions.pop(0)
    
    resp = requests.post(url, json=tx_data)
    try:
        resp.raise_for_status()
    except HTTPError as e:
        logger.error(f"Failed to create transaction: {tx_data}")
        logger.error(f"Status: {resp.status_code}, Response: {resp.text}")
        if "Not enough BTC" in resp.text:
            logger.error("Detected 'Not enough BTC' error!")
            logger.error(f"Last transactions: {last_transactions}")
            dump_all()
        raise
    result = resp.json()
    logger.debug(f"Created TX ID={result['id']} at {result['timestamp']}")
    return result

def update_transaction(tx_id: int, updates: dict) -> dict:
    """Update a transaction via PUT /api/transactions/{tx_id}."""
    url = f"{BASE_URL}/api/transactions/{tx_id}"
    logger.debug(f"Updating TX #{tx_id} with: {updates}")
    resp = requests.put(url, json=updates)
    try:
        resp.raise_for_status()
    except HTTPError as e:
        logger.error(f"Failed to update TX #{tx_id} with: {updates}")
        logger.error(f"Status: {resp.status_code}, Response: {resp.text}")
        if "Not enough BTC" in resp.text:
            logger.error("Detected 'Not enough BTC' error - dumping state...")
            dump_all()
        raise
    result = resp.json()
    logger.debug(f"Updated TX #{tx_id} successfully")
    return result

def delete_transaction(tx_id: int) -> bool:
    """Delete a transaction via DELETE /api/transactions/{tx_id}."""
    url = f"{BASE_URL}/api/transactions/{tx_id}"
    logger.debug(f"Deleting TX #{tx_id}")
    resp = requests.delete(url)
    if resp.status_code in (200, 204):
        logger.debug(f"Deleted TX #{tx_id} successfully")
        return True
    else:
        logger.error(f"Failed to delete TX #{tx_id}")
        logger.error(f"Status: {resp.status_code}, Response: {resp.text}")
        return False

def dump_all():
    """
    Dump all debug endpoints:
    - /api/transactions
    - /api/debug/lots
    - /api/debug/disposals
    - /api/debug/ledger-entries
    - /api/calculations/accounts/balances
    - /api/calculations/average-cost-basis
    - /api/calculations/gains-and-losses
    """
    endpoints = [
        "/api/transactions",
        "/api/debug/lots",
        "/api/debug/disposals",
        "/api/debug/ledger-entries",
        "/api/calculations/accounts/balances",
        "/api/calculations/average-cost-basis",
        "/api/calculations/gains-and-losses",
    ]
    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        logger.info(f"Dumping endpoint: {ep}")
        resp = requests.get(url)
        if resp.status_code == 200:
            logger.info(f"{ep} response: {resp.json()}")
        else:
            logger.warning(f"{ep} failed - Status: {resp.status_code}, Response: {resp.text}")

def dump_account_balances():
    """Dump account balances specifically for quick checks."""
    url = f"{BASE_URL}/api/calculations/accounts/balances"
    resp = requests.get(url)
    if resp.status_code == 200:
        logger.info(f"Account balances: {resp.json()}")
    else:
        logger.warning(f"Failed to dump balances - Status: {resp.status_code}, Response: {resp.text}")

# --------------------------------------------------------------------
# RANDOM TRANSACTION GENERATOR
# --------------------------------------------------------------------
def random_datetime_in_range(start: datetime, end: datetime) -> datetime:
    """Generate a random datetime between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

def pick_random_type() -> str:
    """Pick a random transaction type."""
    return random.choice(["Deposit", "Withdrawal", "Transfer", "Buy", "Sell"])

def generate_random_tx_data() -> dict:
    """Generate random transaction data respecting account rules."""
    tx_type = pick_random_type()
    dt_obj = random_datetime_in_range(base_dt, end_dt)
    timestamp = dt_obj.isoformat()
    
    if tx_type == "Deposit":
        to_acct = random.choice([1, 2, 3, 4])
        if to_acct in [2, 4]:
            amount_btc = round(random.uniform(0.001, 2.0), 8)
            cost_basis_usd = round(random.uniform(30000, 80000), 2)
            return {
                "type": "Deposit", "timestamp": timestamp, "from_account_id": EXTERNAL,
                "to_account_id": to_acct, "amount": str(amount_btc), "fee_amount": "0",
                "fee_currency": "BTC", "source": random.choice(["Income", "Reward", "Gift", "Interest", "N/A"]),
                "cost_basis_usd": str(cost_basis_usd)
            }
        else:
            amount_usd = round(random.uniform(5000, 50000), 2)
            return {
                "type": "Deposit", "timestamp": timestamp, "from_account_id": EXTERNAL,
                "to_account_id": to_acct, "amount": str(amount_usd), "fee_amount": "0",
                "fee_currency": "USD", "source": "N/A"
            }
    elif tx_type == "Withdrawal":
        from_acct = random.choice([1, 2, 3, 4])
        if from_acct in [2, 4]:
            amount_btc = round(random.uniform(0.001, 0.1), 8)
            fee_btc = round(random.uniform(0, 0.0005), 8)
            return {
                "type": "Withdrawal", "timestamp": timestamp, "from_account_id": from_acct,
                "to_account_id": EXTERNAL, "amount": str(amount_btc), "fee_amount": str(fee_btc),
                "fee_currency": "BTC", "purpose": random.choice(["Spent", "Gift", "Donation", "Lost"])
            }
        else:
            amount_usd = round(random.uniform(100, 2000), 2)
            fee_usd = round(random.uniform(0, 10), 2)
            return {
                "type": "Withdrawal", "timestamp": timestamp, "from_account_id": from_acct,
                "to_account_id": EXTERNAL, "amount": str(amount_usd), "fee_amount": str(fee_usd),
                "fee_currency": "USD", "purpose": "N/A"
            }
    elif tx_type == "Transfer":
        possible_pairs = [(2, 4), (4, 2), (1, 3), (3, 1)]
        from_acct, to_acct = random.choice(possible_pairs)
        if from_acct in [2, 4]:
            amount_btc = round(random.uniform(0.001, 0.1), 8)
            fee_btc = round(random.uniform(0, 0.0003), 8)
            return {
                "type": "Transfer", "timestamp": timestamp, "from_account_id": from_acct,
                "to_account_id": to_acct, "amount": str(amount_btc), "fee_amount": str(fee_btc),
                "fee_currency": "BTC"
            }
        else:
            amount_usd = round(random.uniform(100, 3000), 2)
            fee_usd = round(random.uniform(0, 10), 2)
            return {
                "type": "Transfer", "timestamp": timestamp, "from_account_id": from_acct,
                "to_account_id": to_acct, "amount": str(amount_usd), "fee_amount": str(fee_usd),
                "fee_currency": "USD"
            }
    elif tx_type == "Buy":
        amount_btc = round(random.uniform(0.01, 1.0), 8)
        fee_usd = round(random.uniform(0, 20), 2)
        cost_basis = round(random.uniform(10000, 40000), 2)
        return {
            "type": "Buy", "timestamp": timestamp, "from_account_id": EXCHANGE_USD,
            "to_account_id": EXCHANGE_BTC, "amount": str(amount_btc), "fee_amount": str(fee_usd),
            "fee_currency": "USD", "cost_basis_usd": str(cost_basis)
        }
    else:  # Sell
        amount_btc = round(random.uniform(0.01, 0.5), 8)
        fee_usd = round(random.uniform(0, 20), 2)
        proceeds_usd = round(random.uniform(15000, 60000), 2)
        return {
            "type": "Sell", "timestamp": timestamp, "from_account_id": EXCHANGE_BTC,
            "to_account_id": EXCHANGE_USD, "amount": str(amount_btc), "fee_amount": str(fee_usd),
            "fee_currency": "USD", "proceeds_usd": str(proceeds_usd)
        }

# --------------------------------------------------------------------
# MAIN SCRIPT
# --------------------------------------------------------------------
def main():
    # Step 1: Delete All
    delete_all_transactions()
    logger.info("Initial state after deletion:")
    dump_account_balances()

    # Step 2: Create 10 base transactions
    logger.info("Posting original 10 base transactions...")
    all_created = []

    dt1 = base_dt
    tx_data_list = [
        {"type": "Deposit", "timestamp": dt1.isoformat(), "from_account_id": EXTERNAL, "to_account_id": WALLET_ID,
         "amount": "1.0", "fee_amount": "0", "fee_currency": "BTC", "source": "Income", "cost_basis_usd": "35000"},
        {"type": "Deposit", "timestamp": (dt1 + timedelta(days=1)).isoformat(), "from_account_id": EXTERNAL,
         "to_account_id": EXCHANGE_USD, "amount": "100000", "fee_amount": "0", "fee_currency": "USD", "source": "N/A"},
        {"type": "Transfer", "timestamp": (dt1 + timedelta(days=2, hours=2)).isoformat(), "from_account_id": WALLET_ID,
         "to_account_id": EXCHANGE_BTC, "amount": "0.5", "fee_amount": "0.0001", "fee_currency": "BTC"},
        {"type": "Buy", "timestamp": (dt1 + timedelta(days=15)).isoformat(), "from_account_id": EXCHANGE_USD,
         "to_account_id": EXCHANGE_BTC, "amount": "0.2", "fee_amount": "10", "fee_currency": "USD", "cost_basis_usd": "15000"},
        {"type": "Deposit", "timestamp": (dt1 + timedelta(days=30)).isoformat(), "from_account_id": EXTERNAL,
         "to_account_id": WALLET_ID, "amount": "1.5", "fee_amount": "0", "fee_currency": "BTC", "source": "Reward",
         "cost_basis_usd": "55000"},
        {"type": "Sell", "timestamp": (dt1 + timedelta(days=60)).isoformat(), "from_account_id": EXCHANGE_BTC,
         "to_account_id": EXCHANGE_USD, "amount": "0.3", "fee_amount": "15", "fee_currency": "USD", "proceeds_usd": "25000"},
        {"type": "Withdrawal", "timestamp": (dt1 + timedelta(days=365)).isoformat(), "from_account_id": WALLET_ID,
         "to_account_id": EXTERNAL, "amount": "0.5", "fee_amount": "0.0002", "fee_currency": "BTC", "purpose": "Spent"},
        {"type": "Deposit", "timestamp": (dt1 + timedelta(days=366)).isoformat(), "from_account_id": EXTERNAL,
         "to_account_id": EXCHANGE_USD, "amount": "150000", "fee_amount": "0", "fee_currency": "USD"},
        {"type": "Buy", "timestamp": (dt1 + timedelta(days=367)).isoformat(), "from_account_id": EXCHANGE_USD,
         "to_account_id": EXCHANGE_BTC, "amount": "0.8", "fee_amount": "20", "fee_currency": "USD", "cost_basis_usd": "35000"},
        {"type": "Deposit", "timestamp": (dt1 + timedelta(days=375)).isoformat(), "from_account_id": EXTERNAL,
         "to_account_id": WALLET_ID, "amount": "0.1", "fee_amount": "0", "fee_currency": "BTC", "source": "Interest",
         "cost_basis_usd": "8000"}
    ]

    for i, tx_data in enumerate(tx_data_list, 1):
        try:
            tx = create_transaction(tx_data)
            logger.info(f"{i}) Created {tx['type']} TX ID={tx['id']} at {tx['timestamp']}")
            all_created.append(tx)
        except HTTPError as e:
            logger.error(f"Failed to create base transaction {i}: {tx_data}")
            raise

    logger.info("All base transactions created successfully.")
    dump_account_balances()

    # Step 3: Generate random transactions
    logger.info(f"Generating {NUM_RANDOM_TRANSACTIONS} random transactions...")
    for i in range(NUM_RANDOM_TRANSACTIONS):
        tx_data = generate_random_tx_data()
        try:
            new_tx = create_transaction(tx_data)
            all_created.append(new_tx)
            if (i + 1) % 25 == 0:
                logger.info(f"Created {i + 1} random transactions so far...")
                dump_account_balances()  # Periodic balance check
        except HTTPError:
            logger.warning(f"Skipping failed random transaction {i + 1}: {tx_data}")
            dump_all()  # Full dump on failure

    logger.info("All random transactions created successfully.")
    dump_account_balances()

    # Step 4: Random updates
    logger.info(f"Performing {NUM_EDITS} random updates...")
    random_updates = random.sample(all_created, min(NUM_EDITS, len(all_created)))
    for idx, tx in enumerate(random_updates, 1):
        updates = {}
        if random.choice([True, False]):
            ts_str = _fix_iso_timestamp(tx["timestamp"])
            try:
                old_ts = datetime.fromisoformat(ts_str)
                new_ts = old_ts - timedelta(days=random.randint(1, 10))
                updates["timestamp"] = new_ts.isoformat()
            except ValueError:
                logger.warning(f"{idx}) Can't parse timestamp {ts_str}, skipping update on TX #{tx['id']}")
                continue
        else:
            old_basis = float(tx.get("cost_basis_usd", "0") or "0")
            delta = old_basis * random.uniform(-0.1, 0.2)
            new_val = max(0, old_basis + delta)
            updates["cost_basis_usd"] = str(round(new_val, 2))

        try:
            updated = update_transaction(tx["id"], updates)
            logger.info(f"{idx}) Updated TX #{tx['id']} with {updates}")
        except HTTPError:
            logger.warning(f"{idx}) Failed to update TX #{tx['id']} with {updates} - skipping")
            dump_all()  # Full dump on failure

    # Step 5: Random deletes
    logger.info(f"Performing {NUM_DELETES} random deletes...")
    random_deletions = random.sample(all_created, min(NUM_DELETES, len(all_created)))
    for idx, tx in enumerate(random_deletions, 1):
        if delete_transaction(tx["id"]):
            logger.info(f"{idx}) Deleted TX #{tx['id']}")
        else:
            logger.warning(f"{idx}) Failed to delete TX #{tx['id']}")
            dump_all()  # Full dump on failure

    # Step 6: Final dump
    logger.info("Dumping all debug endpoints to verify final state...")
    dump_all()

    logger.info("Stress test completed! Check logs for details.")

if __name__ == "__main__":
    main()