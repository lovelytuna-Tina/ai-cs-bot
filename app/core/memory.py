"""
对话记忆管理
================
第 3 步：基于会话 ID 的多轮对话记忆。
用内存字典存储每个会话的消息历史（生产环境建议换 Redis 等持久化方案）。

核心思路：
    用户每次带 session_id 来 -> 取出该会话历史 -> 连同新消息一起发给大模型
    -> 把这一问一答追加回历史 -> 超过上限则裁剪最旧的消息
"""
from collections import defaultdict

# 每个会话最多保留的"轮数"，1 轮 = 1 问 + 1 答 = 2 条消息
MAX_HISTORY_ROUNDS = 10

# 会话历史表：{session_id: [{"role": "user"|"assistant", "content": "..."}, ...]}
_sessions: dict[str, list[dict]] = defaultdict(list)


def get_history(session_id: str) -> list[dict]:
    """获取指定会话的对话历史（不含系统提示，系统提示在 llm.chat 里单独加）。"""
    return list(_sessions.get(session_id, []))


def add_message(session_id: str, role: str, content: str) -> None:
    """向会话追加一条消息，并按上限裁剪最旧的消息，避免上下文无限增长。"""
    history = _sessions[session_id]
    history.append({"role": role, "content": content})

    max_messages = MAX_HISTORY_ROUNDS * 2
    if len(history) > max_messages:
        # 删除多出来的最旧消息
        del history[: len(history) - max_messages]


def clear_session(session_id: str) -> None:
    """清空指定会话的历史（用于用户主动重置对话）。"""
    _sessions.pop(session_id, None)
