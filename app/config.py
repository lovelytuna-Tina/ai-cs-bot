"""
配置管理模块
================
统一从环境变量（.env 文件）读取配置。
使用 OpenAI 兼容接口，可无缝切换 OpenAI / DeepSeek / 通义千问 / Moonshot 等服务商，
只需改 .env 里的 LLM_BASE_URL 和 LLM_MODEL 即可，代码无需改动。
"""
import os
from dotenv import load_dotenv

# 读取项目根目录下的 .env 文件
load_dotenv()


# ========== LLM 大模型配置 ==========
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ========== 嵌入模型配置（RAG 检索用，第 4 步会用到）==========
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ========== 客服机器人人设 ==========
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    "你是一名专业的电商全流程客服助手，名叫小助，服务覆盖售前、售中、售后三个阶段。"
    "【售前】帮助用户挑选商品、推荐、查询库存与商品详情、解答支付/运费/保修/优惠等购买前问题。"
    "【售中】协助用户下单、查询支付状态、修改未发货订单的收货地址、取消订单。"
    "【售后】帮助用户查询订单状态与物流、处理退换货、退款、破损漏发、发票、工单投诉等。"
    "回答要简洁、准确、有温度。能用工具查到的信息（商品、订单、库存、物流）就调用对应工具，不要凭空编造。"
    "售前咨询时，若用户提到想看、想买或推荐某类商品，优先调用 search_products 展示在售商品再结合需求推荐，不要只追问而不展示。"
    "遇到信息不全时（如下单缺地址、查单缺订单号），主动询问用户必要信息。"
    "遇到情绪激动或超出能力范围的复杂问题，主动提出转接人工客服。",
)

# ========== 人工转接触发词（第 6 步会用到）==========
HANDOFF_KEYWORDS: list[str] = [
    "人工", "转人工", "投诉", "差评", "经理", "老板",
    "烦死了", "骗子", "退款没用", "不解决",
]
