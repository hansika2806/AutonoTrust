"""
wallets.py — Wallet loading (Client, Auditor, Executor N wallets) from env.
Loads all 5 wallets from .env into web3.Account objects.
"""
from web3 import Web3
from backend.config import (
    CLIENT_PRIVATE_KEY, CLIENT_ADDRESS,
    AUDITOR_PRIVATE_KEY, AUDITOR_ADDRESS,
    EXECUTOR_1_PRIVATE_KEY, EXECUTOR_1_ADDRESS,
    EXECUTOR_2_PRIVATE_KEY, EXECUTOR_2_ADDRESS,
    DEPLOYER_PRIVATE_KEY,
    POLYGON_AMOY_RPC_URL,
)


def get_web3() -> Web3:
    """Returns a connected Web3 instance for Polygon Amoy."""
    w3 = Web3(Web3.HTTPProvider(POLYGON_AMOY_RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(
            f"Cannot connect to Polygon Amoy RPC: {POLYGON_AMOY_RPC_URL}"
        )
    return w3


def get_client_account(w3: Web3):
    """Load Client wallet from env."""
    if not CLIENT_PRIVATE_KEY:
        raise ValueError("CLIENT_PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(CLIENT_PRIVATE_KEY)


def get_auditor_account(w3: Web3):
    """
    Load Auditor wallet from env.
    CRITICAL: This is the ONLY wallet that can call submitVerdict.
    """
    if not AUDITOR_PRIVATE_KEY:
        raise ValueError("AUDITOR_PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(AUDITOR_PRIVATE_KEY)


def get_executor_1_account(w3: Web3):
    """Load Executor 1 wallet from env."""
    if not EXECUTOR_1_PRIVATE_KEY:
        raise ValueError("EXECUTOR_1_PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(EXECUTOR_1_PRIVATE_KEY)


def get_executor_2_account(w3: Web3):
    """Load Executor 2 wallet from env."""
    if not EXECUTOR_2_PRIVATE_KEY:
        raise ValueError("EXECUTOR_2_PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(EXECUTOR_2_PRIVATE_KEY)


def get_deployer_account(w3: Web3):
    """Load deployer wallet — only needed for contract deployment."""
    if not DEPLOYER_PRIVATE_KEY:
        raise ValueError("DEPLOYER_PRIVATE_KEY not set in .env")
    return w3.eth.account.from_key(DEPLOYER_PRIVATE_KEY)
