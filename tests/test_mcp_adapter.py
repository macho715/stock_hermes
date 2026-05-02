from stock_rtx4060.mcp_adapter import (
    FORBIDDEN_MCP_CAPABILITIES,
    PHASE1_MCP_MODE,
    assert_phase1_mcp_boundary,
    get_phase1_mcp_contracts,
)


def test_phase1_mcp_contract_is_read_report_only():
    assert PHASE1_MCP_MODE == "adapter_contract_only"
    assert_phase1_mcp_boundary()
    contracts = get_phase1_mcp_contracts()
    assert {contract.command for contract in contracts} == {"recommend", "ops-v1"}
    assert all(contract.access == "read_report_only" for contract in contracts)
    assert not any(contract.starts_server for contract in contracts)
    assert "broker_order" in FORBIDDEN_MCP_CAPABILITIES
