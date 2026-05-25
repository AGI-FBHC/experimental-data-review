"""
Configuration for model selection and API keys.
Users can choose 1 or 2 models for review.
"""
import os

# ============================================================
# Available Models
# ============================================================

AVAILABLE_MODELS = {
    "kimi-coding": {
        "name": "Kimi Coding",
        "provider": "kimi",
        "api_base": "https://api.kimi.com/coding",
        "api_key_env": "KIMI_API_KEY",
        "model_id": "kimi-coding",
        "description": "Kimi 编程/分析模型，适合代码和结构化数据分析"
    },
    "deepseek-v4-flash": {
        "name": "DeepSeek V4 Flash",
        "provider": "deepseek",
        "api_base": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model_id": "deepseek-chat",
        "description": "DeepSeek 快速模型，响应快，适合初步筛查"
    },
    "deepseek-v4-pro": {
        "name": "DeepSeek V4 Pro",
        "provider": "deepseek",
        "api_base": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model_id": "deepseek-reasoner",
        "description": "DeepSeek 推理模型，深度分析，适合复杂审查"
    }
}

# ============================================================
# API Keys (from environment)
# ============================================================

KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-c7deabdae91e485da316f27128908d70")

# ============================================================
# Default Selection
# ============================================================

# Default: single model (Kimi)
DEFAULT_MODEL_A = os.getenv("DEFAULT_MODEL_A", "kimi-coding")
DEFAULT_MODEL_B = os.getenv("DEFAULT_MODEL_B", "")

# Consensus threshold (percentage)
CONSENSUS_THRESHOLD = float(os.getenv("CONSENSUS_THRESHOLD", "80"))

# Auto-escalate on disagreement
AUTO_ESCALATE = os.getenv("AUTO_ESCALATE", "true").lower() == "true"

# Domain presets
DOMAIN_PRESETS = {
    "general": "通用统计审查",
    "llm_agent": "LLM/Agent 研究",
    "bioinformatics": "生物信息学/ML"
}

# ============================================================
# Validation
# ============================================================

def validate_model_selection(model_a: str, model_b: str) -> tuple[bool, str]:
    """
    Validate user model selection.
    
    Rules:
    - model_a is required
    - model_b is optional (empty string = single model)
    - Both models must exist in AVAILABLE_MODELS
    - Not recommended to use both DeepSeek models simultaneously
    """
    if not model_a:
        return False, "请至少选择一个模型"
    
    if model_a not in AVAILABLE_MODELS:
        return False, f"模型 A '{model_a}' 不可用"
    
    if model_b:
        if model_b not in AVAILABLE_MODELS:
            return False, f"模型 B '{model_b}' 不可用"
        
        # Warning: both DeepSeek
        if "deepseek" in model_a and "deepseek" in model_b:
            return True, "warning:同时使用两个 DeepSeek 模型可能降低审查多样性，建议搭配 Kimi"
    
    return True, "ok"


def get_model_config(model_key: str) -> dict:
    """Get full config for a model."""
    return AVAILABLE_MODELS.get(model_key, {})


def get_api_key(provider: str) -> str:
    """Get API key for provider."""
    if provider == "kimi":
        return KIMI_API_KEY
    elif provider == "deepseek":
        return DEEPSEEK_API_KEY
    return ""
