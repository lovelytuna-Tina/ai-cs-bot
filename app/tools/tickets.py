"""
工单与退款工具（模拟业务系统）
====================================
模拟"创建售后工单"和"申请退款"两个写操作。
真实项目里会写入工单系统 / 退款审批流。
"""
import time
from typing import Any

# 内存中的工单/退款记录（演示用）
_tickets: list[dict[str, Any]] = []
_refunds: list[dict[str, Any]] = []


def create_ticket(
    order_id: str, issue_type: str, description: str
) -> dict[str, Any]:
    """创建一个售后工单。"""
    ticket_id = f"T{int(time.time()) % 1000000:06d}"
    ticket = {
        "ticket_id": ticket_id,
        "order_id": order_id,
        "issue_type": issue_type,
        "description": description,
        "status": "已创建，待客服跟进",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _tickets.append(ticket)
    return {"success": True, "data": ticket}


def apply_refund(order_id: str, reason: str) -> dict[str, Any]:
    """提交退款申请。"""
    refund_id = f"R{int(time.time()) % 1000000:06d}"
    refund = {
        "refund_id": refund_id,
        "order_id": order_id,
        "reason": reason,
        "status": "审核中（预计1-3个工作日出结果）",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _refunds.append(refund)
    return {"success": True, "data": refund}
