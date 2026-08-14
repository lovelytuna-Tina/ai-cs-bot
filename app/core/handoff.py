"""
人工转接检测
============
第 6 步：判断何时该把用户转给人工客服。

触发条件（满足任一即转接）：
    1. 用户明确要求人工（"转人工"、"找人工"等）
    2. 检测到强烈负面情绪词（"骗子"、"气死"、"垃圾"等）
    3. 感叹号密集，情绪激动
    4. 对话轮次较多，疑似问题始终未解决

真实模式下可进一步用大模型做情绪/意图分类，这里先用规则保证可跑通。
"""
from app.config import HANDOFF_KEYWORDS

# 强负面情绪词（出现即视为情绪激烈）
_NEGATIVE_WORDS = [
    "气死", "骗子", "垃圾", "恶心", "无语", "失望", "坑人",
    "差评", "投诉", "骗", "退款没用", "烦死",
    "没人理", "什么态度", "到底", "怎么还不", "等了好久",
    "解决不了", "没用", "急死", "受不了", "再也不",
]


def _is_similar(text1: str, text2: str) -> bool:
    """判断两段文本是否相似（字符二元组Jaccard相似度>0.5）。"""
    if not text1 or not text2 or len(text1) < 2 or len(text2) < 2:
        return False
    s1 = {text1[i:i+2] for i in range(len(text1) - 1)}
    s2 = {text2[i:i+2] for i in range(len(text2) - 1)}
    if not s1 or not s2:
        return False
    return len(s1 & s2) / len(s1 | s2) > 0.5


def detect(message: str, history: list[dict] | None = None) -> dict:
    """检测当前消息是否需要转人工。

    返回: {"should_handoff": bool, "reasons": [str], "urgency": "高"|"中"|"低"}
    """
    history = history or []
    reasons: list[str] = []

    # 1) 显式请求人工
    explicit = [k for k in HANDOFF_KEYWORDS if k in message]
    if explicit:
        reasons.append(f"用户请求人工（命中：{explicit[0]}）")

    # 2) 负面情绪词
    neg_hits = [w for w in _NEGATIVE_WORDS if w in message]
    if neg_hits:
        reasons.append(f"检测到负面情绪：{'、'.join(neg_hits[:3])}")

    # 3) 感叹号密集（>=3 个视为激动）
    excl = message.count("！") + message.count("!")
    if excl >= 3:
        reasons.append(f"感叹号密集（{excl} 个），情绪较激动")

    # 4) 多轮未解决（历史超过 4 轮 = 8 条消息，从6轮降低到4轮）
    if len(history) >= 8:
        reasons.append("对话轮次较多，疑似问题未解决")

    # 5) 重复提问检测（用户连续2次问相似问题，说明AI没解决）
    user_msgs = [m.get("content", "") for m in history if m.get("role") == "user"]
    user_msgs.append(message)
    if len(user_msgs) >= 3:
        # 检查最近2次用户消息是否与当前相似
        for prev in user_msgs[-3:-1]:
            if _is_similar(prev, message):
                reasons.append("用户重复提问，疑似问题未解决")
                break

    # 6) 困惑检测（连续2条消息都包含多个问号）
    qmark = message.count("?") + message.count("？")
    if qmark >= 2 and len(user_msgs) >= 2:
        prev_qmark = user_msgs[-2].count("?") + user_msgs[-2].count("？") if len(user_msgs) >= 2 else 0
        if prev_qmark >= 2:
            reasons.append("用户连续多次提问，疑似困惑")

    should = len(reasons) > 0
    # 紧急程度：有负面情绪或感叹号密集为"高"，仅显式请求为"中"
    if neg_hits or excl >= 3:
        urgency = "高"
    elif reasons:
        urgency = "中"
    else:
        urgency = "低"

    return {"should_handoff": should, "reasons": reasons, "urgency": urgency}


def build_handoff_reply(handoff: dict, history: list[dict] | None) -> str:
    """生成转接提示语（含原因、紧急程度、对话摘要）。"""
    history = history or []
    rounds = len(history) // 2
    return (
        "👨‍💼 已为您转接人工客服\n"
        "我理解您的情况，为确保问题得到妥善解决，马上为您安排人工客服。\n\n"
        f"• 转接原因：{'；'.join(handoff['reasons'])}\n"
        f"• 紧急程度：{handoff['urgency']}\n"
        f"• 对话摘要：本次会话共 {rounds} 轮，完整记录已同步给人工客服\n\n"
        "请稍候，人工客服会很快接入。"
    )
