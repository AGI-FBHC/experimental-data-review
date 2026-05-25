"""
Configuration for dual-model validation.
"""
import os

# Model Configuration
VALIDATOR_A_MODEL = os.getenv('VALIDATOR_A_MODEL', 'claude-sonnet-4')
VALIDATOR_A_PROVIDER = os.getenv('VALIDATOR_A_PROVIDER', 'anthropic')

VALIDATOR_B_MODEL = os.getenv('VALIDATOR_B_MODEL', 'gemini-2.5-pro')
VALIDATOR_B_PROVIDER = os.getenv('VALIDATOR_B_PROVIDER', 'google')

# Consensus threshold (percentage)
CONSENSUS_THRESHOLD = float(os.getenv('CONSENSUS_THRESHOLD', '80'))

# Auto-escalate on disagreement
AUTO_ESCALATE = os.getenv('AUTO_ESCALATE', 'true').lower() == 'true'

# API Keys (should be set via environment variables)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

# Domain presets
DOMAIN_PRESETS = {
    'general': '通用统计审查',
    'llm_agent': 'LLM/Agent 研究',
    'bioinformatics': '生物信息学/ML'
}
