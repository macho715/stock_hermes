"""Read/report-only MCP adapter contract for Phase 1.

This module intentionally does not start an MCP server.  It only records which
existing CLI workflows may be exposed by a future MCP layer after separate
approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PHASE1_MCP_MODE = "adapter_contract_only"
FORBIDDEN_MCP_CAPABILITIES = {
    "broker_order",
    "account_write",
    "auto_buy",
    "auto_sell",
    "margin",
    "options",
    "destructive_filesystem",
    "external_write_back",
}


@dataclass(frozen=True)
class McpWorkflowContract:
    name: str
    command: Literal["recommend", "ops-v1"]
    access: Literal["read_report_only"]
    starts_server: bool = False
    broker_order_execution: bool = False
    account_write: bool = False


ALLOWED_MCP_WORKFLOWS: tuple[McpWorkflowContract, ...] = (
    McpWorkflowContract(name="screen_recommendations", command="recommend", access="read_report_only"),
    McpWorkflowContract(name="ops_v1_review_packet", command="ops-v1", access="read_report_only"),
)


def get_phase1_mcp_contracts() -> tuple[McpWorkflowContract, ...]:
    return ALLOWED_MCP_WORKFLOWS


def assert_phase1_mcp_boundary() -> None:
    for contract in ALLOWED_MCP_WORKFLOWS:
        if contract.starts_server or contract.broker_order_execution or contract.account_write:
            raise AssertionError(f"unsafe MCP contract: {contract.name}")
        if contract.access != "read_report_only":
            raise AssertionError(f"unsupported MCP access mode: {contract.name}")
