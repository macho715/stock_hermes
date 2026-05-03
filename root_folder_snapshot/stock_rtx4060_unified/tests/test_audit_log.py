import json
from pathlib import Path

from stock_rtx4060.audit_log import AuditEvent, AuditLogger, mask_secret


def test_audit_log_writes_jsonl_and_masks_secrets(tmp_path):
    log_path = tmp_path / "audit_log.jsonl"
    logger = AuditLogger(log_path)
    fake_secret = "FAKE_TEST_SECRET_VALUE_123456"

    logger.write(
        AuditEvent(
            event_type="provider_attempt",
            status="FAIL",
            command="recommend",
            ticker="AAPL",
            provider_requested="openbb",
            provider_used="openbb",
            message=f"token={fake_secret}",
            metadata={"api_key": fake_secret, "nested": {"authorization": f"Bearer {fake_secret}"}},
        )
    )

    text = Path(log_path).read_text(encoding="utf-8")
    row = json.loads(text)
    assert row["event_type"] == "provider_attempt"
    assert row["status"] == "FAIL"
    assert fake_secret not in text
    assert row["metadata"]["api_key"] == "<masked>"


def test_mask_secret_handles_nested_values():
    masked = mask_secret({"provider": "openbb", "account_id": "ACC-123", "url": "https://x.test?api_key=secret123"})
    assert masked["provider"] == "openbb"
    assert masked["account_id"] == "<masked>"
    assert "secret123" not in masked["url"]
