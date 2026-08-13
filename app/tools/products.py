"""
售前商品工具（模拟商品系统）
============================
真实项目里这些函数会查询商品中心 / 搜索引擎 / 库存系统。
这里从 products.json 加载模拟数据，供售前咨询、推荐、库存查询使用。
"""
import json
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"


def _load_products() -> list[dict[str, Any]]:
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def search_products(keyword: str = "", category: str = "") -> dict[str, Any]:
    """按关键词或分类搜索商品，返回匹配的商品列表（精简信息）。

    售前场景：用户问"有什么耳机""推荐个礼物""数码类有哪些"时调用。
    """
    products = _load_products()
    kw = (keyword or "").strip().lower()
    cat = (category or "").strip()

    results = []
    for p in products:
        # 分类过滤
        if cat and cat not in p["category"]:
            continue
        # 关键词匹配：名称 / 标签 / 描述 / 规格
        if kw:
            haystack = " ".join(
                [p["name"], p["category"], p["description"], p["specs"]]
                + p.get("tags", [])
            ).lower()
            if kw not in haystack:
                continue
        results.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "category": p["category"],
            "price": p["price"],
            "stock": p["stock"],
        })

    if not results:
        return {"success": False, "message": f"未找到匹配「{keyword or category}」的商品。"}
    return {"success": True, "data": {"count": len(results), "products": results}}


def get_product_detail(product_id: str) -> dict[str, Any]:
    """根据商品ID查询商品完整详情（名称、价格、规格、描述、库存）。

    售前场景：用户对某商品感兴趣想了解详情时调用。
    """
    products = _load_products()
    for p in products:
        if p["product_id"] == product_id:
            return {"success": True, "data": p}
    return {"success": False, "message": f"未找到商品 {product_id}。"}


def check_stock(product_id: str) -> dict[str, Any]:
    """查询某商品的库存情况（是否有货、剩余数量）。

    售前场景：用户问"XX有货吗""还能买吗"时调用。
    """
    products = _load_products()
    for p in products:
        if p["product_id"] == product_id:
            stock = p["stock"]
            return {
                "success": True,
                "data": {
                    "product_id": p["product_id"],
                    "name": p["name"],
                    "stock": stock,
                    "available": stock > 0,
                    "status": "暂时缺货" if stock == 0 else ("仅剩少量" if stock <= 50 else "有货"),
                },
            }
    return {"success": False, "message": f"未找到商品 {product_id}。"}
