"""
LLM 客户端封装
================
使用 OpenAI 兼容接口，可对接 OpenAI / DeepSeek / 通义千问 / Moonshot 等。
未配置 API Key 时自动进入"模拟模式"，返回提示文案，方便无 Key 时也能跑通流程。
"""
from openai import OpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, SYSTEM_PROMPT, EMBEDDING_MODEL, LLM_VISION_MODEL

# LLM 请求超时（秒）
LLM_TIMEOUT = 30


def _build_client() -> OpenAI | None:
    """创建 OpenAI 客户端；没有 Key 时返回 None（进入模拟模式）。"""
    if not LLM_API_KEY:
        return None
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)


_client = _build_client()
# 是否处于模拟模式（供接口返回，前端可据此提示用户）
IS_MOCK: bool = _client is None


def chat(
    user_message: str,
    history: list[dict] | None = None,
    context: str | None = None,
) -> str:
    """与大模型对话。

    参数:
        user_message: 用户本轮说的话
        history: 之前的对话历史（第 3 步接入记忆后传入），格式如
                 [{"role": "user", "content": "..."},
                  {"role": "assistant", "content": "..."}]
        context: RAG 检索到的背景知识（第 4 步接入），会作为系统消息注入
    返回:
        模型回复的文本
    """
    # ---- 模拟模式：没有 Key 时的兜底，保证链路可跑通 ----
    if IS_MOCK:
        ctx_note = "\n\n[已注入 RAG 知识库参考]" if context else ""
        return (
            "【模拟模式】当前未配置 LLM_API_KEY，无法连接真实大模型。\n"
            "请在 .env 文件中填入你的 API Key（可参考 .env.example），"
            "重启服务后即可获得真实回复。\n\n"
            f"你刚才说的是：{user_message}{ctx_note}"
        )

    # ---- 真实模式：组装消息列表，调用大模型 ----
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        # 把检索到的知识作为补充系统消息注入，让回答有据可依
        messages.append({"role": "system", "content": context})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.7,  # 0.7 适合客服：既稳定又有一定灵活度
        )
        return response.choices[0].message.content
    except Exception as e:
        # LLM 调用失败（超时/网络错误/限流），返回友好提示而非崩溃
        return f"抱歉，AI 服务暂时不可用，请稍后重试。\n（错误信息：{type(e).__name__}）"




def chat_with_vision(
    user_message: str,
    images: list[str],
    history: list[dict] | None = None,
    context: str | None = None,
) -> str:
    """多模态对话：把图片和文字一起发给视觉模型分析。

    参数:
        user_message: 用户文字描述
        images: base64编码的图片列表（不含data:前缀）
        history: 对话历史
        context: RAG背景知识
    返回:
        视觉模型对图片的分析结果（文本）
    """
    if IS_MOCK:
        return f"[模拟模式] 收到 {len(images)} 张图片，但未配置API Key，无法进行视觉分析。用户描述：{user_message}"

    # 构建多模态消息内容
    content: list[dict] = []
    if user_message:
        content.append({"type": "text", "text": user_message})
    for img_b64 in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
        })

    # 添加分析指令
    content.append({
        "type": "text",
        "text": "\n\n请作为电商客服视觉助手分析以上图片。重点关注：1)商品类型和外观 2)是否有破损/污渍/变形 3)商品与包装是否匹配 4)其他可见问题。用简洁中文描述分析结果。"
    })

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": content})

    try:
        response = _client.chat.completions.create(
            model=LLM_VISION_MODEL,
            messages=messages,
            temperature=0.3,  # 视觉分析需要较低温度，保证稳定
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"视觉分析暂时不可用：{type(e).__name__}。请尝试用文字描述问题。"

def embed_texts(texts: list[str], chunk_size: int = 10) -> list[list[float]] | None:
    """调用嵌入模型，把文本转向量。

    用于 RAG 向量检索。分批请求（兼容单次输入数量上限），
    某批失败时自动降级为逐条调用。模拟模式或全部失败时返回 None。
    """
    if IS_MOCK:
        return None
    all_embs: list[list[float]] = []
    for i in range(0, len(texts), chunk_size):
        batch = texts[i : i + chunk_size]
        try:
            resp = _client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            data = sorted(resp.data, key=lambda d: d.index)
            all_embs.extend(d.embedding for d in data)
        except Exception:
            # 该批失败，降级为逐条调用
            for t in batch:
                try:
                    resp = _client.embeddings.create(model=EMBEDDING_MODEL, input=[t])
                    all_embs.append(resp.data[0].embedding)
                except Exception:
                    return None
    return all_embs if len(all_embs) == len(texts) else None
