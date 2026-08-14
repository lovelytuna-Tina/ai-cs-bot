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

# ========== 视觉模型配置（多模态，Phase 3）==========
LLM_VISION_MODEL: str = os.getenv("LLM_VISION_MODEL", "qwen-vl-plus")

# ========== 客服机器人人设 ==========
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    "你是一名专业的电商全流程客服助手，名叫小助，服务覆盖售前、售中、售后三个阶段。\n"
    "【售前】帮助用户挑选商品、推荐、查询库存与商品详情、解答支付/运费/保修/优惠等购买前问题。\n"
    "【售中】协助用户下单、查询支付状态、修改未发货订单的收货地址、取消订单。\n"
    "【售后】帮助用户查询订单状态与物流、处理退换货、退款、破损漏发、发票、工单投诉等。\n"
    "\n"
    "【工具使用规则——非常重要】\n"
    "1. 当用户提到「订单、物流、快递、到货、送达、发货」时，优先调用 query_logistics 或 query_order 查询实时信息，不要只凭FAQ文字回答。\n"
    "2. 当用户提到「退款、退货、退钱、退掉」时，调用 apply_refund 发起退款流程。\n"
    "3. 当用户提到「支付、付款、付了吗」时，调用 check_payment 查询支付状态。\n"
    "4. 当用户提到「投诉、维修、工单、解决不了」时，调用 create_ticket 创建工单。\n"
    "5. 当用户提到「推荐、有什么、看看、想买」时，调用 search_products 展示商品。\n"
    "6. 当用户提到「有货吗、库存、能买吗」时，调用 check_stock 查询库存。\n"
    "7. 如果用户没提供订单号，先尝试从对话历史中提取；如果确实没有，先用一句话询问，不要长篇大论。\n"
    "8. 能用工具查到的信息（商品、订单、库存、物流）必须调用对应工具，不要凭空编造。\n"
    "\n"
    "【库存话术】对顾客回复时禁止说出具体库存件数。只可用「现货充足 / 有货 / 库存紧张 / 暂时缺货」等状态描述。\n"
    "\n"
    "遇到信息不全时，主动询问用户必要信息，但每次只问1-2个关键信息，不要一次问太多。\n"
    "遇到情绪激动或超出能力范围的复杂问题，主动提出转接人工客服。",
)

# ========== 人工转接触发词（第 6 步会用到）==========
HANDOFF_KEYWORDS: list[str] = [
    "人工", "转人工", "投诉", "差评", "经理", "老板",
    "烦死了", "骗子", "退款没用", "不解决",
    "没人理", "什么态度", "到底能不能", "怎么还不",
    "等了好久", "解决不了", "没用", "能不能快点",
    "急死", "等不及", "说好的",
]
