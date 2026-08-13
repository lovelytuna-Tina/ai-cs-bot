"""
订单 / 物流 / 售中工具（模拟业务系统）
======================================
真实项目里这些函数会查数据库 / ERP / 第三方物流 API。
这里用内存模拟数据，覆盖售中（下单、支付、改址）与售后（查单、查物流）。

工具分组：
    售中：place_order / check_payment / modify_order_address
    售后：query_order / query_logistics
"""
import json
import time
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"


def _load_products() -> list[dict[str, Any]]:
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_product(product_id: str) -> dict[str, Any] | None:
    for p in _load_products():
        if p["product_id"] == product_id:
            return p
    return None


# ---- 模拟订单数据库 ----
_MOCK_ORDERS: dict[str, dict[str, Any]] = {
    "20250812001": {
        "order_id": "20250812001",
        "status": "已发货",
        "product": "无线蓝牙耳机 Pro",
        "product_id": "P1001",
        "quantity": 1,
        "amount": 299.00,
        "payment_status": "已支付",
        "address": "广东省深圳市南山区科技园 1 栋",
        "logistics_company": "顺丰速运",
        "tracking_no": "SF1234567890",
        "logistics_status": "运输中",
        "current_location": "深圳转运中心",
        "estimated_delivery": "预计明天（8月13日）下午送达",
    },
    "20250812002": {
        "order_id": "20250812002",
        "status": "待发货",
        "product": "智能手表运动版",
        "product_id": "P1002",
        "quantity": 1,
        "amount": 599.00,
        "payment_status": "已支付",
        "address": "北京市海淀区中关村大街 2 号",
        "logistics_company": "",
        "tracking_no": "",
        "logistics_status": "尚未揽收",
        "current_location": "仓库备货中",
        "estimated_delivery": "预计8月14日发货",
    },
    "20250812003": {
        "order_id": "20250812003",
        "status": "已完成",
        "product": "便携充电宝 20000mAh",
        "product_id": "P1003",
        "quantity": 2,
        "amount": 258.00,
        "payment_status": "已支付",
        "address": "上海市浦东新区张江路 100 号",
        "logistics_company": "中通快递",
        "tracking_no": "ZT9876543210",
        "logistics_status": "已签收",
        "current_location": "已送达",
        "estimated_delivery": "已于8月10日签收",
    },
}


# ==================== 售中工具 ====================
def place_order(product_id: str, quantity: int = 1, address: str = "") -> dict[str, Any]:
    """为用户创建一笔新订单（售中下单）。

    会校验商品是否存在、库存是否充足，生成订单号，初始状态为「待支付」。
    """
    product = _find_product(product_id)
    if not product:
        return {"success": False, "message": f"商品 {product_id} 不存在，无法下单。"}

    qty = max(1, int(quantity))
    if product["stock"] < qty:
        return {
            "success": False,
            "message": f"库存不足：{product['name']} 当前库存 {product['stock']} 件，无法下单 {qty} 件。",
        }

    order_id = f"2025081{int(time.time()) % 100000:05d}"
    amount = round(product["price"] * qty, 2)
    order = {
        "order_id": order_id,
        "status": "待支付",
        "product": product["name"],
        "product_id": product["product_id"],
        "quantity": qty,
        "amount": amount,
        "payment_status": "待支付",
        "address": address or "（待填写收货地址）",
        "logistics_company": "",
        "tracking_no": "",
        "logistics_status": "未发货",
        "current_location": "—",
        "estimated_delivery": "支付后48小时内发货",
    }
    _MOCK_ORDERS[order_id] = order
    return {
        "success": True,
        "data": {
            "order_id": order_id,
            "product": order["product"],
            "quantity": qty,
            "amount": amount,
            "status": order["status"],
            "address": order["address"],
        },
    }


def check_payment(order_id: str) -> dict[str, Any]:
    """查询订单的支付状态（待支付 / 已支付 / 已退款）。"""
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "message": f"未找到订单 {order_id}，无法查询支付状态。"}
    return {
        "success": True,
        "data": {
            "order_id": order["order_id"],
            "product": order["product"],
            "amount": order["amount"],
            "payment_status": order["payment_status"],
            "order_status": order["status"],
        },
    }


def modify_order_address(order_id: str, new_address: str) -> dict[str, Any]:
    """修改订单的收货地址（仅未发货订单可改）。"""
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "message": f"未找到订单 {order_id}。"}
    if order["status"] in ("已发货", "已完成"):
        return {
            "success": False,
            "message": f"订单 {order_id} 已发货，无法修改地址。建议联系快递公司改派或联系人工客服拦截。",
        }
    old = order["address"]
    order["address"] = new_address
    return {
        "success": True,
        "data": {
            "order_id": order["order_id"],
            "old_address": old,
            "new_address": new_address,
            "status": order["status"],
        },
    }


# ==================== 售后工具 ====================
def query_order(order_id: str) -> dict[str, Any]:
    """根据订单号查询订单基本信息（状态、商品、金额）。"""
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "message": f"未找到订单 {order_id}，请确认订单号是否正确。"}
    return {
        "success": True,
        "data": {
            "order_id": order["order_id"],
            "status": order["status"],
            "product": order["product"],
            "quantity": order.get("quantity", 1),
            "amount": order["amount"],
            "payment_status": order["payment_status"],
        },
    }


def query_logistics(order_id: str) -> dict[str, Any]:
    """根据订单号查询物流进度。"""
    order = _MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "message": f"未找到订单 {order_id}，无法查询物流。"}
    return {
        "success": True,
        "data": {
            "order_id": order["order_id"],
            "logistics_company": order["logistics_company"] or "待分配",
            "tracking_no": order["tracking_no"] or "暂无",
            "logistics_status": order["logistics_status"],
            "current_location": order["current_location"],
            "estimated_delivery": order["estimated_delivery"],
        },
    }
