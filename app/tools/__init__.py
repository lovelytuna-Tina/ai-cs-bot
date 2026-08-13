"""
工具注册表
==========
集中管理所有可被 Agent 调用的业务工具：
    - TOOL_FUNCTIONS: 工具名 -> 可调用函数（执行用）
    - TOOL_DEFINITIONS: OpenAI function-calling 格式的工具描述（供大模型决策用）
新增工具时，在这里注册即可，Agent 会自动识别。

工具按服务阶段分组：
    售前：search_products / get_product_detail / check_stock
    售中：place_order / check_payment / modify_order_address
    售后：query_order / query_logistics / create_ticket / apply_refund
"""
from app.tools.products import search_products, get_product_detail, check_stock
from app.tools.orders import (
    place_order, check_payment, modify_order_address,
    query_order, query_logistics,
)
from app.tools.tickets import create_ticket, apply_refund

# 工具名 -> 函数
TOOL_FUNCTIONS = {
    # 售前
    "search_products": search_products,
    "get_product_detail": get_product_detail,
    "check_stock": check_stock,
    # 售中
    "place_order": place_order,
    "check_payment": check_payment,
    "modify_order_address": modify_order_address,
    # 售后
    "query_order": query_order,
    "query_logistics": query_logistics,
    "create_ticket": create_ticket,
    "apply_refund": apply_refund,
}

# OpenAI function-calling 格式的工具描述（真实模式下交给大模型）
TOOL_DEFINITIONS = [
    # ===== 售前 =====
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "按关键词或分类搜索/推荐商品。用户想看商品、找推荐、问有什么XX时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如 耳机、运动、礼物"},
                    "category": {"type": "string", "description": "商品分类，如 数码电子、家居生活、运动户外、箱包配饰"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_detail",
            "description": "根据商品ID查询商品完整详情（名称、价格、规格、描述、库存）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "商品ID，如 P1001"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "查询某商品是否有货、剩余库存数量。用户问XX有货吗时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "商品ID"},
                },
                "required": ["product_id"],
            },
        },
    },
    # ===== 售中 =====
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "为用户创建一笔新订单。用户决定购买、要下单时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "要购买的商品ID"},
                    "quantity": {"type": "integer", "description": "购买数量，默认1"},
                    "address": {"type": "string", "description": "收货地址，用户未提供则留空"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_payment",
            "description": "查询订单的支付状态（待支付/已支付/已退款）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_order_address",
            "description": "修改未发货订单的收货地址。已发货订单无法修改。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"},
                    "new_address": {"type": "string", "description": "新的收货地址"},
                },
                "required": ["order_id", "new_address"],
            },
        },
    },
    # ===== 售后 =====
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单状态、商品名称、金额等基本信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号，如 20250812001"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "根据订单号查询物流公司、运单号、当前位置、预计送达时间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "为用户创建一个售后工单，用于上报问题、投诉、维修等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "相关订单号，没有则填未知"},
                    "issue_type": {
                        "type": "string",
                        "description": "问题类型，如 售后/投诉/维修/咨询",
                    },
                    "description": {"type": "string", "description": "问题描述"},
                },
                "required": ["order_id", "issue_type", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_refund",
            "description": "为用户提交退款申请。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "相关订单号，没有则填未知"},
                    "reason": {"type": "string", "description": "退款原因"},
                },
                "required": ["order_id", "reason"],
            },
        },
    },
]
