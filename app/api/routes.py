"""
API 路由
========
第 2~5 步：聊天接口（记忆 + RAG + Agent 工具调用）
后续步骤会在此基础上扩展（人工转接、流式）。
"""
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.llm import IS_MOCK
from app.core import memory, agent

router = APIRouter(prefix="/api")


# ---- 请求 / 响应数据模型 ----
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # 不传则新建会话


class ToolCallInfo(BaseModel):
    tool: str
    args: dict
    result: dict


class HandoffInfo(BaseModel):
    should_handoff: bool
    reasons: list[str]
    urgency: str  # 高 / 中 / 低


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    mock: bool  # 是否为模拟模式
    rag_mode: str  # RAG 检索模式：vector / tfidf
    rag_hits: list[dict]  # RAG 命中的知识库条目
    tool_calls: list[ToolCallInfo]  # 本次调用的工具及结果
    handoff: HandoffInfo  # 人工转接检测结果


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """智能客服聊天接口：Agent 统一编排 RAG + 工具调用 + 记忆。"""
    session_id = req.session_id or str(uuid.uuid4())

    # 1) 取出会话历史
    history = memory.get_history(session_id)

    # 2) Agent 主流程（检索知识库 -> 决策并执行工具 -> 生成回复）
    try:
        result = agent.run(req.message, history=history)
    except Exception as e:
        return ChatResponse(
            reply=f"抱歉，服务暂时遇到问题，请稍后重试。\n（错误：{type(e).__name__}）",
            session_id=session_id,
            mock=IS_MOCK,
            rag_mode="none",
            rag_hits=[],
            tool_calls=[],
            handoff=HandoffInfo(should_handoff=False, reasons=[], urgency="低"),
        )

    # 3) 记忆本轮对话
    memory.add_message(session_id, "user", req.message)
    memory.add_message(session_id, "assistant", result["reply"])

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        mock=IS_MOCK,
        rag_mode=result["rag_mode"],
        rag_hits=result["rag_hits"],
        tool_calls=[ToolCallInfo(**tc) for tc in result["tool_calls"]],
        handoff=HandoffInfo(**result["handoff"]),
    )


@router.post("/chat/reset")
async def reset_session(session_id: str):
    """清空指定会话的记忆，重新开始对话。"""
    memory.clear_session(session_id)
    return {"status": "ok", "session_id": session_id, "message": "会话已重置"}


@router.get("/chat/history")
async def get_history_endpoint(session_id: str):
    """调试用：查看某会话当前的记忆内容。"""
    return {"session_id": session_id, "history": memory.get_history(session_id)}
