"""
test_contract_client.py — Unit tests for the contract_client module.
Tests are mocked — no live blockchain calls.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_submit_verdict_uses_auditor_wallet():
    """
    Critical test: verify submit_verdict ONLY uses the auditor wallet, never any other.
    The auditor address used to sign must match AUDITOR_ADDRESS from config.
    """
    with patch("backend.chain.contract_client.get_web3") as mock_w3_fn, \
         patch("backend.chain.contract_client.get_auditor_account") as mock_auditor, \
         patch("backend.chain.contract_client.get_client_account") as mock_client, \
         patch("backend.chain.contract_client._get_contract") as mock_contract, \
         patch("backend.chain.contract_client._send_transaction") as mock_send:

        mock_send.return_value = "0xmocktxhash"
        mock_w3 = MagicMock()
        mock_w3_fn.return_value = mock_w3

        mock_auditor_account = MagicMock()
        mock_auditor_account.address = "0xAuditorAddress"
        mock_auditor.return_value = mock_auditor_account

        mock_contract_instance = MagicMock()
        mock_contract.return_value = mock_contract_instance
        mock_contract_instance.functions.submitVerdict.return_value.build_transaction.return_value = {"from": "0xAuditorAddress"}

        from backend.chain.contract_client import submit_verdict
        result = submit_verdict(task_id=1, passed=True)

        # Verify auditor account was retrieved (not client)
        mock_auditor.assert_called_once()
        mock_client.assert_not_called()

        # Verify transaction was sent with auditor account
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][1] == mock_auditor_account

        assert result == "0xmocktxhash"


def test_lock_payment_uses_client_wallet():
    """Verify lock_payment uses client wallet, not auditor."""
    with patch("backend.chain.contract_client.get_web3") as mock_w3_fn, \
         patch("backend.chain.contract_client.get_client_account") as mock_client, \
         patch("backend.chain.contract_client.get_auditor_account") as mock_auditor, \
         patch("backend.chain.contract_client._get_contract") as mock_contract, \
         patch("backend.chain.contract_client._send_transaction") as mock_send:

        mock_send.return_value = "0xlocktxhash"
        mock_w3 = MagicMock()
        mock_w3_fn.return_value = mock_w3

        mock_client_account = MagicMock()
        mock_client_account.address = "0xClientAddress"
        mock_client.return_value = mock_client_account

        mock_contract_instance = MagicMock()
        mock_contract.return_value = mock_contract_instance
        mock_contract_instance.functions.lockPayment.return_value.build_transaction.return_value = {
            "from": "0xClientAddress", "value": 1000
        }

        from backend.chain.contract_client import lock_payment
        result = lock_payment(
            task_id=1,
            executor_address="0x" + "1" * 40,
            auditor_address="0x" + "2" * 40,
            amount_wei=1000,
            deadline_unix=9999999999,
        )

        mock_client.assert_called_once()
        mock_auditor.assert_not_called()
        assert result == "0xlocktxhash"
