"""
Chat Service for Conversational Review
Supports interactive Q&A about manuscript review results.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ChatMessage:
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class Conversation:
    id: str
    task_id: Optional[str]
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ChatService:
    """
    Conversational review service.
    
    Provides context-aware Q&A about:
    - Review results interpretation
    - Statistical concept explanations
    - Fix suggestions
    - Domain-specific guidance
    """
    
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
        self.system_prompt = """你是 XClaw 实验数据审查助手，专门帮助研究人员理解和解决手稿中的统计一致性问题。

你的职责：
1. 解释审查结果中的问题（GRIM、交叉一致性、领域特定）
2. 提供具体的修改建议
3. 解释统计概念（p值、效应量、置信区间等）
4. 帮助作者判断哪些问题必须修改，哪些可以保留

回答风格：
- 专业但易懂，避免过度技术化
- 给出具体例子说明如何修改
- 区分 "必须修改" 和 "建议修改"
- 保持客观，不直接指控学术不端

当前审查上下文："""
    
    def create_conversation(self, task_id: Optional[str] = None) -> str:
        """Create a new conversation."""
        conv_id = str(uuid.uuid4())
        self.conversations[conv_id] = Conversation(
            id=conv_id,
            task_id=task_id
        )
        return conv_id
    
    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.conversations.get(conv_id)
    
    def add_message(self, conv_id: str, role: str, content: str, context: Optional[Dict] = None) -> ChatMessage:
        """Add a message to conversation."""
        conv = self.conversations.get(conv_id)
        if not conv:
            raise ValueError(f"Conversation {conv_id} not found")
        
        msg = ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            context=context
        )
        conv.messages.append(msg)
        conv.updated_at = datetime.now().isoformat()
        return msg
    
    def generate_response(self, conv_id: str, user_message: str, review_context: Optional[Dict] = None) -> str:
        """
        Generate assistant response based on user message and review context.
        
        In production, this would call an LLM API.
        For now, returns rule-based responses.
        """
        conv = self.conversations.get(conv_id)
        if not conv:
            return "对话未找到，请刷新页面重试。"
        
        # Add user message
        self.add_message(conv_id, 'user', user_message)
        
        # Generate response based on intent
        response = self._generate_rule_based_response(user_message, review_context)
        
        # Add assistant message
        self.add_message(conv_id, 'assistant', response, review_context)
        
        return response
    
    def _generate_rule_based_response(self, message: str, context: Optional[Dict]) -> str:
        """Generate rule-based response for common questions."""
        msg_lower = message.lower()
        
        # Greeting
        if any(w in msg_lower for w in ['你好', 'hello', 'hi', '帮助', 'help']):
            return """你好！我是 XClaw 实验数据审查助手。

我可以帮你：
- 解释审查结果中的问题
- 说明统计概念（p值、效应量等）
- 提供具体的修改建议
- 判断问题严重程度

请描述你遇到的问题，或粘贴审查结果中的具体条目。"""
        
        # GRIM test explanation
        if 'grim' in msg_lower or '均值' in msg_lower or 'mean' in msg_lower:
            return """GRIM 测试（Granularity-Related Inconsistency of Means）检查报告的均值在数学上是否可能。

原理：
- 对于整数量表（如 Likert 1-5），均值必须是 1/n 的倍数
- 例如 n=30，均值只能是 1.00, 1.033, 1.067... 等

常见原因：
1. 四舍五入导致（如报告 3.45 但实际是 3.4503）
2. 计算错误
3. 样本量报告错误

修改建议：
- 检查原始数据重新计算
- 如果确实是四舍五入，保留更多小数位
- 确认样本量 n 是否正确"""
        
        # P-value explanation
        if 'p值' in msg_lower or 'p-value' in msg_lower or '显著' in msg_lower:
            return """p值相关问题：

决策翻转（Decision Flip）：
- 报告 p < 0.05，但重算得到 p = 0.051
- 这是 必须修改 的问题

修改建议：
1. 使用精确的统计软件重新计算
2. 检查自由度是否正确
3. 如果确实不显著，修改结论表述
4. 考虑报告效应量（Cohen's d）而非仅依赖 p值

注意：p值在 0.045-0.055 之间时最容易出现翻转，建议报告精确值而非 < 0.05。"""
        
        # Cross-reference issues
        if '交叉' in msg_lower or '一致' in msg_lower or 'cross' in msg_lower:
            return """交叉位置不一致指同一统计量在不同位置报告不同值。

常见场景：
- 摘要写 N=120，方法部分写 N=118
- 表格均值 3.2，正文写 3.3
- 图注 p<0.01，正文 p=0.02

修改建议：
1. 以原始数据计算为准
2. 全文统一使用同一数值
3. 如果涉及四舍五入，明确标注

严重程度：
- HIGH：影响核心结论的数值
- MEDIUM：次要统计量
- LOW：明显笔误（如 3.20 vs 3.21）"""
        
        # Fix suggestions
        if '怎么改' in msg_lower or '如何修改' in msg_lower or 'fix' in msg_lower or '修改' in msg_lower:
            return """通用修改流程：

1. 定位问题
   - 找到审查报告中的行号
   - 确认原始数据

2. 判断类型
   - 计算错误 -> 重新计算
   - 四舍五入 -> 保留更多小数位
   - 笔误 -> 统一数值
   - 方法问题 -> 补充说明

3. 修改并验证
   - 修改后重新运行审查
   - 确认问题已解决

4. 记录变更
   - 在回复审稿人时说明修改
   - 提供修改后的统计量

需要我针对具体问题给出更详细的建议吗？"""
        
        # Severity assessment
        if '严重' in msg_lower or 'severity' in msg_lower or '必须' in msg_lower:
            return """问题严重程度判断：

HIGH（必须修改）：
- p值决策翻转（报告显著但实际不显著）
- GRIM 测试失败（均值不可能）
- 核心结论的统计量不一致

MEDIUM（建议修改）：
- 次要统计量的四舍五入问题
- 样本量描述不一致
- 效应量报告不完整

LOW（可选修改）：
- 格式问题
- 非核心数值的轻微差异
- 表述不清但不影响结论

原则：
- 涉及统计显著性的 -> 必须修改
- 仅影响精确度的 -> 建议修改
- 不影响结论的 -> 可选修改"""
        
        # Default response
        return """我理解你的问题。为了给出更准确的回答，能否提供：

1. 审查报告中的具体条目（可复制粘贴）
2. 你使用的统计方法
3. 原始数据的关键信息（样本量、量表类型等）

或者你可以问：
- "GRIM 测试失败是什么意思？"
- "p值翻转怎么修改？"
- "这个问题严重吗？"
- "怎么修改交叉不一致？"""
    
    def get_conversation_history(self, conv_id: str) -> List[Dict[str, Any]]:
        """Get conversation history as list of dicts."""
        conv = self.conversations.get(conv_id)
        if not conv:
            return []
        
        return [
            {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp
            }
            for msg in conv.messages
        ]


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create singleton chat service."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
