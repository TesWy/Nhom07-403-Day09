"""
mcp_server_advanced.py — Real MCP Server dùng FastMCP library
Sprint 3 Advanced: Bonus +2 points

Chạy độc lập:
    python mcp_server_advanced.py

Hoặc được gọi bởi mcp_client_advanced.py qua stdio transport.
"""

import os
import json
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Day09-Advanced-MCP")

TICKETS_FILE = os.path.join(os.path.dirname(__file__), "data", "tickets.json")

def _load_tickets() -> dict:
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def _load_access_rules() -> dict:
    return {
        1: {
            "required_approvers": ["Line Manager"],
            "emergency_can_bypass": False,
            "note": "Standard user access",
        },
        2: {
            "required_approvers": ["Line Manager", "IT Admin"],
            "emergency_can_bypass": True,
            "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
            "note": "Elevated access",
        },
        3: {
            "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
            "emergency_can_bypass": False,
            "note": "Admin access — không có emergency bypass",
        },
    }


@mcp.tool()
def search_kb(query: str, top_k: int = 3) -> dict:
    """Tìm kiếm Knowledge Base nội bộ bằng semantic search. Trả về top-k chunks liên quan nhất."""
    try:
        from workers.retrieval import retrieve_dense
        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    except Exception as e:
        return {
            "chunks": [{"text": f"[ADVANCED-MCP FALLBACK] {e}", "source": "fallback", "score": 0.0}],
            "sources": ["fallback"],
            "total_found": 0,
        }


@mcp.tool()
def get_ticket_info(ticket_id: str) -> dict:
    """Tra cứu thông tin ticket từ data/tickets.json."""
    tickets = _load_tickets()
    ticket = tickets.get(ticket_id.upper()) or tickets.get(ticket_id)
    if ticket:
        return ticket
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy.",
        "available_ids": list(tickets.keys()),
    }


@mcp.tool()
def check_access_permission(
    access_level: int,
    requester_role: str,
    is_emergency: bool = False,
) -> dict:
    """Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP."""
    rules = _load_access_rules()
    rule = rules.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    notes = []
    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "access_level": access_level,
        "can_grant": True,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


@mcp.tool()
def create_ticket(priority: str, title: str, description: str = "") -> dict:
    """Tạo ticket mới (MOCK — không tạo thật trong lab)."""
    from datetime import datetime
    mock_id = f"IT-{9900 + hash(title) % 99}"
    return {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }


if __name__ == "__main__":
    mcp.run()