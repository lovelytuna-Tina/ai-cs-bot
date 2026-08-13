"""
Agent：工具调用编排
====================
第 5 步：让客服"能办事"——根据用户意图调用业务工具。

主流程：
    1. RAG 检索知识库（拿到背景 FAQ）
    2. 决策需要调用哪些工具（模拟模式=规则；真实模式=大模型 function calling）
    3. 执行工具，拿到业务结果
    4. 生成最终回复（模拟模式=模板拼装；真实模式=把工具结果喂回大模型润色）

对外只暴露 run()，供路由层调用。
"""
import re
from typing import Any

from app.core import llm, rag, handoff
from app.tools import TOOL_FUNCTIONS, TOOL_DEFINITIONS

# 订单号识别：8 位以上数字，或"订单号/单号/订单"后跟的数字
_ORDER_RE = re.compile(r"(?:订单号|单号|订单)[:：\s]*?(\d{6,})|(?<!\d)(\d{10,})(?!\d)")


def _extract_order_id(message: str) -> str | None:
    """从用户消息里提取订单号。"""
    m = _ORDER_RE.search(message)
    if m:
        return m.group(1) or m.group(2)
    return None


def _find_order_id_in_history(history: list[dict] | None) -> str | None:
    """从对话历史里找最近一次出现过的订单号（用于"这个订单"等指代场景）。"""
    if not history:
        return None
    for msg in reversed(history):
        if msg.get("role") == "user":
            oid = _extract_order_id(msg.get("content", ""))
            if oid:
                return oid
    return None


# 指代"上文订单"的表述
_ORDER_REFERENCE = ["这个订单", "那个订单", "该订单", "这单", "那单", "这个", "那个"]

# 商品关键词 -> 商品ID（模拟模式下用于识别用户想看/想买的商品）
_PRODUCT_KEYWORDS: dict[str, str] = {
    "耳机": "P1001", "手表": "P1002", "充电宝": "P1003", "音箱": "P1004",
    "加湿器": "P2001", "台灯": "P2002", "瑜伽垫": "P3001", "跑步机": "P3002",
    "双肩包": "P4001", "背包": "P4001", "保温杯": "P4002", "水杯": "P4002",
}
# 售前浏览意图 / 下单意图
_PRESALE_BROWSE = ["推荐", "有什么", "买什么", "看看", "有哪些", "想买个", "想买", "有什么好"]
_PRESALE_ORDER = ["下单", "买一个", "要一个", "来一个", "帮我买", "要买", "买吧", "下单吧", "帮我下单"]


# ------------------------------------------------------------------
# 工具决策
# ------------------------------------------------------------------
def _mock_decide(message: str, order_id: str | None) -> list[dict[str, Any]]:
    """模拟模式：用关键词规则判断该调用哪些工具。"""
    calls: list[dict[str, Any]] = []
    has_order = order_id is not None

    # --- 售后：查物流 / 查订单 ---
    if has_order and any(k in message for k in ["物流", "快递", "到哪", "什么时候到", "送到"]):
        calls.append({"tool": "query_logistics", "args": {"order_id": order_id}})
    elif has_order and any(k in message for k in ["订单", "状态", "查询", "查一下", "怎么样了"]):
        calls.append({"tool": "query_order", "args": {"order_id": order_id}})

    # --- 售中：支付查询 / 改地址 / 下单 ---
    if has_order and any(k in message for k in ["支付", "付款", "付了吗", "付了没", "支付状态"]):
        calls.append({"tool": "check_payment", "args": {"order_id": order_id}})
    if has_order and any(k in message for k in ["改地址", "修改地址", "换地址", "改收货"]):
        addr = message.split("改成")[-1].strip() if "改成" in message else "用户新地址"
        calls.append({"tool": "modify_order_address", "args": {"order_id": order_id, "new_address": addr[:50]}})
    if any(k in message for k in _PRESALE_ORDER):
        pid = next((v for k, v in _PRODUCT_KEYWORDS.items() if k in message), None)
        if pid:
            calls.append({"tool": "place_order", "args": {"product_id": pid, "quantity": 1}})

    # --- 售前：搜索商品 / 查库存 ---
    if not has_order and any(k in message for k in _PRESALE_BROWSE):
        kw = next((k for k in _PRODUCT_KEYWORDS if k in message), "")
        calls.append({"tool": "search_products", "args": {"keyword": kw}})
    if any(k in message for k in ["有货吗", "还有货", "库存", "能买吗", "有没有货"]):
        pid = next((v for k, v in _PRODUCT_KEYWORDS.items() if k in message), None)
        if pid:
            calls.append({"tool": "check_stock", "args": {"product_id": pid}})

    # --- 售后：退款 / 工单 ---
    if any(k in message for k in ["我要退款", "申请退款", "帮我退款", "给我退款", "退掉", "不要了", "退钱", "退款吧"]):
        calls.append({
            "tool": "apply_refund",
            "args": {"order_id": order_id or "未知", "reason": "用户主动申请退款"},
        })
    if any(k in message for k in ["工单", "投诉", "维修", "上报", "解决不了"]):
        calls.append({
            "tool": "create_ticket",
            "args": {"order_id": order_id or "未知", "issue_type": "售后", "description": message},
        })
    return calls


def _llm_decide(message: str, history: list[dict] | None) -> list[dict[str, Any]]:
    """真实模式：让大模型决定调用哪些工具（function calling）。"""
    from app.config import SYSTEM_PROMPT, LLM_MODEL

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        response = llm._client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
        )
        msg = response.choices[0].message
        calls: list[dict[str, Any]] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                import json
                args = json.loads(tc.function.arguments or "{}")
                calls.append({"tool": tc.function.name, "args": args})
        return calls
    except Exception:
        # function calling 失败，降级为规则引擎决策
        order_id = _extract_order_id(message)
        return _mock_decide(message, order_id)


# ------------------------------------------------------------------
# 回复生成
# ------------------------------------------------------------------
def _format_tool_result_for_user(tc: dict[str, Any]) -> str:
    """把单个工具的执行结果格式化成给用户看的文字（模拟模式用）。"""
    tool = tc["tool"]
    res = tc["result"]
    if not res.get("success"):
        return f"⚠️ {res.get('message', '操作失败')}"

    data = res["data"]
    if tool == "query_order":
        return (
            f"📦 订单 {data['order_id']} 信息：\n"
            f"  商品：{data['product']}\n"
            f"  金额：￥{data['amount']}\n"
            f"  状态：{data['status']}"
        )
    if tool == "query_logistics":
        return (
            f"🚚 订单 {data['order_id']} 物流：\n"
            f"  承运：{data['logistics_company']}（运单号 {data['tracking_no']}）\n"
            f"  当前：{data['logistics_status']} - {data['current_location']}\n"
            f"  预计：{data['estimated_delivery']}"
        )
    if tool == "create_ticket":
        return (
            f"🎫 已为您创建工单：\n"
            f"  工单号：{data['ticket_id']}\n"
            f"  类型：{data['issue_type']}\n"
            f"  状态：{data['status']}\n"
            f"  我们的客服会尽快跟进，请留意通知。"
        )
    if tool == "apply_refund":
        return (
            f"💰 退款申请已提交：\n"
            f"  退款单号：{data['refund_id']}\n"
            f"  订单：{data['order_id']}\n"
            f"  状态：{data['status']}"
        )
    if tool == "search_products":
        prods = data.get("products", [])
        lines = [f"🔍 找到 {data.get('count', len(prods))} 个相关商品："]
        for p in prods:
            stock_info = f"库存{p['stock']}" if "stock" in p else p.get("stock_status", "")
            lines.append(f"  · {p['product_id']} {p['name']}（{p['category']}）￥{p['price']} {stock_info}")
        return "\n".join(lines)
    if tool == "get_product_detail":
        stock_info = f"库存：{data.get('stock', '—')}" if "stock" in data else f"库存：{data.get('stock_status', '—')}"
        return (
            f"📦 商品详情：\n"
            f"  名称：{data['name']}\n"
            f"  价格：￥{data['price']}\n"
            f"  规格：{data.get('specs', '—')}\n"
            f"  {stock_info}\n"
            f"  描述：{data.get('description', '—')}"
        )
    if tool == "check_stock":
        if "stock" in data:
            return f"📦 {data['name']} 库存：{data['stock']} 件（{data['status']}）"
        else:
            return f"📦 {data['name']} 状态：{data['status']}"
    if tool == "place_order":
        return (
            f"✅ 下单成功：\n"
            f"  订单号：{data['order_id']}\n"
            f"  商品：{data['product']} × {data['quantity']}\n"
            f"  金额：￥{data['amount']}\n"
            f"  状态：{data['status']}"
        )
    if tool == "check_payment":
        return (
            f"💳 订单 {data['order_id']} 支付状态：\n"
            f"  商品：{data['product']}\n"
            f"  金额：￥{data['amount']}\n"
            f"  支付：{data['payment_status']}\n"
            f"  订单：{data['order_status']}"
        )
    if tool == "modify_order_address":
        return (
            f"✏️ 地址已修改：\n"
            f"  订单：{data['order_id']}\n"
            f"  原地址：{data['old_address']}\n"
            f"  新地址：{data['new_address']}"
        )
    return f"操作完成：{data}"


def _format_tool_results_for_llm(tool_calls: list[dict[str, Any]]) -> str:
    """把工具结果整理成大模型可读的背景信息（真实模式用）。"""
    lines = ["以下是已执行的业务工具及其返回结果，请据此回答用户："]
    for tc in tool_calls:
        lines.append(f"- 工具 {tc['tool']}（参数 {tc['args']}）返回：{tc['result']}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 对外入口
# ------------------------------------------------------------------
def run(message: str, history: list[dict] | None = None, cs_mode: bool = False) -> dict[str, Any]:
    """Agent 主流程：转接检测 -> 检索 -> 决策工具 -> 执行 -> 生成回复。

    参数:
        cs_mode: 客服模式。True 时返回完整库存信息，False 时对普通用户隐藏库存数量。

    返回: {"reply": str, "rag_hits": list, "tool_calls": list, "handoff": dict}
    """
    # 0) 人工转接检测（优先级最高：该转接就直接转，不再执行业务工具）
    hf = handoff.detect(message, history)

    # 1) RAG 检索知识库（转接场景下也检索，便于人工客服参考）
    context, hits = rag.build_rag_context(message)

    if hf["should_handoff"]:
        return {
            "reply": handoff.build_handoff_reply(hf, history),
            "rag_hits": hits,
            "rag_mode": rag.kb.mode,
            "tool_calls": [],
            "handoff": hf,
        }

    # 2) 决策需要哪些工具
    order_id = _extract_order_id(message)
    if not order_id and any(k in message for k in _ORDER_REFERENCE):
        # 用户说"这个订单"但没带号，从历史里找回上次提到的订单号
        order_id = _find_order_id_in_history(history)
    if llm.IS_MOCK:
        planned = _mock_decide(message, order_id)
    else:
        planned = _llm_decide(message, history)

    # 3) 执行工具
    executed: list[dict[str, Any]] = []
    for call in planned:
        fn = TOOL_FUNCTIONS.get(call["tool"])
        if fn:
            result = fn(**call["args"])
            executed.append({"tool": call["tool"], "args": call["args"], "result": result})

    # 4) 生成回复
    if llm.IS_MOCK:
        reply = _mock_reply(message, history, context, executed, cs_mode)
    else:
        # 真实模式：把 RAG 背景 + 工具结果一起喂给大模型润色
        extra = ""
        if context:
            extra += context
        if executed:
            # 非客服模式下，过滤工具结果中的库存数量
            filtered_executed = executed if cs_mode else _strip_stock_from_tool_calls(executed)
            extra += "\n" + _format_tool_results_for_llm(filtered_executed)
            if not cs_mode:
                extra += "\n【重要规则】当前为普通用户模式，回复中不要提及具体库存数量，只需说「有货」或「缺货」即可。"
        reply = llm.chat(message, history=history, context=extra or None)

    return {"reply": reply, "rag_hits": hits, "rag_mode": rag.kb.mode, "tool_calls": executed, "handoff": hf}


def _strip_stock_from_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """非客服模式下，从工具结果中移除具体库存数量，只保留有货/缺货状态。"""
    import copy
    filtered = copy.deepcopy(tool_calls)
    for tc in filtered:
        res = tc.get("result", {})
        if not res.get("success"):
            continue
        data = res.get("data", {})
        tool = tc["tool"]
        # search_products: data.products 列表中每个商品移除 stock
        if tool == "search_products" and "products" in data:
            for p in data["products"]:
                stock = p.pop("stock", None)
                p["stock_status"] = "有货" if stock and stock > 0 else "缺货"
        # get_product_detail: 移除 stock，添加 stock_status
        elif tool == "get_product_detail" and "stock" in data:
            stock = data.pop("stock")
            data["stock_status"] = "有货" if stock > 0 else "缺货"
        # check_stock: 移除 stock 数字，保留 status
        elif tool == "check_stock" and "stock" in data:
            data.pop("stock")
            # available 和 status 字段已足够表达有货/缺货
    return filtered


def _mock_reply(
    message: str,
    history: list[dict] | None,
    context: str | None,
    tool_calls: list[dict[str, Any]],
    cs_mode: bool = False,
) -> str:
    """模拟模式下的回复：有工具结果就展示结果，否则走普通 mock chat。"""
    if tool_calls:
        # 非客服模式下过滤库存数量
        display_calls = tool_calls if cs_mode else _strip_stock_from_tool_calls(tool_calls)
        parts = ["【模拟模式·已执行业务工具】以下为工具返回结果（接入真实大模型后会用自然语言润色）："]
        for tc in display_calls:
            parts.append(_format_tool_result_for_user(tc))
        return "\n\n".join(parts)
    # 没有工具调用，走普通对话（含 RAG 提示）
    return llm.chat(message, history=history, context=context)
