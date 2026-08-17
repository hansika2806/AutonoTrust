"""
contract_client.py — web3.py wrapper for VadaChainEscrow.
Exact required functions (from spec):
  - lock_payment(task_id, executor_address, auditor_address, amount_wei, deadline_unix) -> str (tx hash)
  - submit_verdict(task_id, passed) -> str  [MUST use Auditor wallet ONLY]
  - reclaim_after_timeout(task_id) -> str (tx hash)
  - get_success_rate(executor_address) -> int  [read-only, no gas]
"""
import json
import os
import logging
from pathlib import Path

from web3 import Web3
from backend.chain.wallets import (
    get_web3,
    get_client_account,
    get_auditor_account,
)
from backend.config import CONTRACT_ADDRESS

logger = logging.getLogger(__name__)

_ABI_PATH = Path(__file__).parent / "abi" / "VadaChainEscrow.json"
_DEPLOYED_ADDR_PATH = Path(__file__).parent / "deployed_address.txt"


def _load_abi() -> list:
    """Load compiled ABI from abi/VadaChainEscrow.json."""
    if not _ABI_PATH.exists():
        raise FileNotFoundError(
            f"ABI not found at {_ABI_PATH}. "
            "Run `cd contracts && npm run compile` and copy artifacts/VadaChainEscrow.json here."
        )
    with open(_ABI_PATH) as f:
        data = json.load(f)
    # Handle both raw ABI list and Hardhat artifact format
    if isinstance(data, list):
        return data
    return data.get("abi", data)


def _get_contract_address() -> str:
    """Get deployed contract address from env or deployed_address.txt."""
    if CONTRACT_ADDRESS:
        return CONTRACT_ADDRESS
    if _DEPLOYED_ADDR_PATH.exists():
        addr = _DEPLOYED_ADDR_PATH.read_text().strip()
        if addr:
            return addr
    raise ValueError(
        "CONTRACT_ADDRESS not set. Deploy the contract first (Phase 2) and set "
        "CONTRACT_ADDRESS in .env or ensure deployed_address.txt exists."
    )


def _get_contract(w3: Web3):
    """Return a web3 Contract instance."""
    abi = _load_abi()
    address = _get_contract_address()
    return w3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=abi,
    )


def _send_transaction(w3: Web3, account, tx) -> str:
    """Sign and send a transaction, return tx hash string."""
    tx["nonce"] = w3.eth.get_transaction_count(account.address)
    tx["chainId"] = w3.eth.chain_id
    if "gas" not in tx:
        tx["gas"] = w3.eth.estimate_gas(tx)

    signed = account.sign_transaction(tx)
    # web3.py v6 uses rawTransaction (camelCase); v5 used raw_transaction
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None)
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    logger.info(f"TX confirmed: {tx_hash.hex()}, block={receipt.blockNumber}")
    return tx_hash.hex()


def lock_payment(
    task_id: int,
    executor_address: str,
    auditor_address: str,
    amount_wei: int,
    deadline_unix: int,
) -> str:
    """
    Lock payment in escrow. Signs and sends with Client wallet. Returns tx hash.
    """
    w3 = get_web3()
    client = get_client_account(w3)
    contract = _get_contract(w3)

    tx = contract.functions.lockPayment(
        task_id,
        Web3.to_checksum_address(executor_address),
        Web3.to_checksum_address(auditor_address),
        deadline_unix,
    ).build_transaction({
        "from": client.address,
        "value": amount_wei,
        "gasPrice": w3.eth.gas_price,
    })

    logger.info(f"lock_payment: task_id={task_id}, amount={amount_wei} wei")
    return _send_transaction(w3, client, tx)


def submit_verdict(task_id: int, passed: bool) -> str:
    """
    Submit audit verdict. MUST use the Auditor wallet — NEVER the Client's
    or a generic backend key. This is the core trust guarantee.
    Returns tx hash.
    """
    w3 = get_web3()
    auditor = get_auditor_account(w3)  # ONLY auditor wallet used here
    contract = _get_contract(w3)

    tx = contract.functions.submitVerdict(
        task_id, passed
    ).build_transaction({
        "from": auditor.address,
        "gasPrice": w3.eth.gas_price,
    })

    logger.info(f"submit_verdict: task_id={task_id}, passed={passed}, signer={auditor.address}")
    return _send_transaction(w3, auditor, tx)


def reclaim_after_timeout(task_id: int) -> str:
    """
    Reclaim escrowed funds after deadline. Signs with Client wallet. Returns tx hash.
    """
    w3 = get_web3()
    client = get_client_account(w3)
    contract = _get_contract(w3)

    tx = contract.functions.reclaimAfterTimeout(
        task_id
    ).build_transaction({
        "from": client.address,
        "gasPrice": w3.eth.gas_price,
    })

    logger.info(f"reclaim_after_timeout: task_id={task_id}")
    return _send_transaction(w3, client, tx)


def get_success_rate(executor_address: str) -> int:
    """
    Read-only call — no gas. Returns success rate as integer (e.g. 85 = 85%).
    """
    w3 = get_web3()
    contract = _get_contract(w3)
    rate = contract.functions.getSuccessRate(
        Web3.to_checksum_address(executor_address)
    ).call()
    logger.info(f"get_success_rate({executor_address}) = {rate}")
    return rate
