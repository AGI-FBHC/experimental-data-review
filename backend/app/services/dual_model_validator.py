"""
Dual-Model Validation Service
Coordinates two independent LLM validators and resolves disagreements.
Supports user-selected models: Kimi, DeepSeek-v4-flash, DeepSeek-v4-pro.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .llm_client import LLMClient


class ConsensusStatus(Enum):
    AGREE_PASS = "agree_pass"
    AGREE_FAIL = "agree_fail"
    DISAGREE = "disagree"
    SINGLE_MODEL = "single_model"


@dataclass
class ValidationResult:
    model_name: str
    passed: bool
    issues: List[Dict[str, Any]]
    confidence: float
    raw_response: str


@dataclass
class ConsensusResult:
    status: ConsensusStatus
    validator_a: ValidationResult
    validator_b: Optional[ValidationResult]
    merged_issues: List[Dict[str, Any]]
    disagreement_areas: List[str]
    recommendation: str


class DualModelValidator:
    """
    Dual-model validation coordinator.
    Supports single or dual model validation.
    """
    
    def __init__(
        self,
        model_a: str = "kimi-coding",
        model_b: Optional[str] = None,
        consensus_threshold: float = 0.8
    ):
        self.model_a = model_a
        self.model_b = model_b
        self.consensus_threshold = consensus_threshold
        self.history: List[ConsensusResult] = []
    
    def validate(
        self,
        manuscript_text: str,
        domain: str = "general",
        extracted_stats: Optional[List[Dict]] = None
    ) -> ConsensusResult:
        """
        Run validation with selected model(s).
        
        If model_b is None/empty, runs single-model validation.
        """
        # Run deterministic pre-checks
        from .manuscript_extractor import extract_statistics
        from .grim_tests import run_grim_tests
        from .cross_reference_audit import run_cross_reference_audit
        from .domain_audit import run_domain_audit
        
        if extracted_stats is None:
            stats = extract_statistics(manuscript_text)
        else:
            stats = extracted_stats
        
        grim_results = run_grim_tests(stats)
        cross_results = run_cross_reference_audit(stats)
        domain_results = run_domain_audit(stats, domain)
        
        # Build prompt for LLM review
        prompt = self._build_review_prompt(
            stats, grim_results, cross_results, domain_results, domain
        )
        
        # Run Model A (always)
        validator_a = self._call_llm_validator(self.model_a, prompt, stats, grim_results, cross_results, domain_results)
        
        # Run Model B (if selected)
        validator_b = None
        if self.model_b:
            validator_b = self._call_llm_validator(self.model_b, prompt, stats, grim_results, cross_results, domain_results)
        
        # Compute consensus
        consensus = self._compute_consensus(validator_a, validator_b)
        
        # Store history
        self.history.append(consensus)
        
        return consensus
    
    def _build_review_prompt(
        self,
        stats: List[Dict],
        grim: List[Dict],
        cross: List[Dict],
        domain: List[Dict],
        domain_type: str
    ) -> str:
        """Build prompt for LLM review."""
        prompt = f"""你是一位专业的学术统计审查员。请审查以下手稿的统计一致性。

## 领域: {domain_type}

## 提取的统计量 ({len(stats)} 个):
"""
        for s in stats[:20]:  # Limit to 20 for prompt
            prompt += f"- {s['type']}: {s.get('raw', '')} (行 {s.get('line', 'N/A')})\n"
        
        prompt += f"\n## GRIM/GRIMMER/DEBIT 检查结果 ({len(grim)} 个):\n"
        for g in grim:
            status = "❌ 错误" if g.get('is_error') else "✅ 通过"
            prompt += f"- [{status}] {g.get('test', '')}: {g.get('message', '')}\n"
        
        prompt += f"\n## 交叉一致性检查 ({len(cross)} 个):\n"
        for c in cross:
            status = "❌ 错误" if c.get('is_error') else "✅ 通过"
            prompt += f"- [{status}] {c.get('type', '')}: {c.get('message', '')}\n"
        
        prompt += """
## 审查要求:
1. 判断每个问题是否真实存在（排除误报）
2. 评估问题的严重程度（HIGH/MEDIUM/LOW）
3. 给出具体的修改建议
4. 最终判断是否建议接受稿件

请以 JSON 格式输出:
{
  "passed": true/false,
  "confidence": 0.0-1.0,
  "issues": [
    {
      "severity": "HIGH|MEDIUM|LOW",
      "category": "deterministic|consistency|domain",
      "message": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "summary": "总体评价"
}
"""
        return prompt
    
    def _call_llm_validator(
        self,
        model_key: str,
        prompt: str,
        stats: List[Dict],
        grim: List[Dict],
        cross: List[Dict],
        domain: List[Dict]
    ) -> ValidationResult:
        """Call LLM for validation."""
        client = LLMClient(model_key)
        
        messages = [
            {"role": "system", "content": "你是一位专业的学术统计审查员，擅长发现手稿中的统计不一致问题。"},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat(messages, max_tokens=4096, temperature=0.3)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                result = {}
        except json.JSONDecodeError:
            result = {}
        
        issues = result.get('issues', [])
        passed = result.get('passed', len(issues) == 0)
        confidence = result.get('confidence', 0.8)
        
        # Fallback: if LLM fails, use deterministic results
        if not issues:
            for g in grim:
                if g.get('is_error'):
                    issues.append({
                        'severity': 'HIGH',
                        'category': 'deterministic',
                        'message': g.get('message', ''),
                        'suggestion': '请检查原始数据并重新计算'
                    })
            for c in cross:
                if c.get('is_error'):
                    issues.append({
                        'severity': 'HIGH',
                        'category': 'consistency',
                        'message': c.get('message', ''),
                        'suggestion': '请统一全文数值'
                    })
        
        return ValidationResult(
            model_name=model_key,
            passed=passed and len([i for i in issues if i.get('severity') == 'HIGH']) == 0,
            issues=issues,
            confidence=confidence,
            raw_response=response[:500]  # Truncate for storage
        )
    
    def _compute_consensus(
        self,
        a: ValidationResult,
        b: Optional[ValidationResult]
    ) -> ConsensusResult:
        """Compute consensus between validators."""
        
        # Single model mode
        if b is None:
            status = ConsensusStatus.SINGLE_MODEL
            merged_issues = a.issues
            disagreement_areas = []
            recommendation = "✅ 单模型审查完成" if a.passed else "❌ 发现问题，建议修改"
        else:
            # Dual model mode
            if a.passed and b.passed:
                status = ConsensusStatus.AGREE_PASS
            elif not a.passed and not b.passed:
                status = ConsensusStatus.AGREE_FAIL
            else:
                status = ConsensusStatus.DISAGREE
            
            # Merge issues (union)
            all_issues = a.issues + b.issues
            seen = set()
            merged_issues = []
            for issue in all_issues:
                key = issue.get('message', '')
                if key not in seen:
                    seen.add(key)
                    merged_issues.append(issue)
            
            # Find disagreement areas
            disagreement_areas = []
            if status == ConsensusStatus.DISAGREE:
                if a.passed and not b.passed:
                    disagreement_areas.append(f"{a.model_name} 通过但 {b.model_name} 发现问题")
                elif b.passed and not a.passed:
                    disagreement_areas.append(f"{b.model_name} 通过但 {a.model_name} 发现问题")
            
            # Generate recommendation
            if status == ConsensusStatus.AGREE_PASS:
                recommendation = "✅ 双模型一致通过：稿件通过自动审查"
            elif status == ConsensusStatus.AGREE_FAIL:
                recommendation = "❌ 双模型一致报错：建议修改后重新提交"
            else:
                recommendation = "⚠️ 模型分歧：建议人工复核争议项"
        
        return ConsensusResult(
            status=status,
            validator_a=a,
            validator_b=b,
            merged_issues=merged_issues,
            disagreement_areas=disagreement_areas,
            recommendation=recommendation
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self.history:
            return {"total": 0}
        
        total = len(self.history)
        agree_pass = sum(1 for h in self.history if h.status == ConsensusStatus.AGREE_PASS)
        agree_fail = sum(1 for h in self.history if h.status == ConsensusStatus.AGREE_FAIL)
        disagree = sum(1 for h in self.history if h.status == ConsensusStatus.DISAGREE)
        single = sum(1 for h in self.history if h.status == ConsensusStatus.SINGLE_MODEL)
        
        return {
            "total": total,
            "agree_pass": agree_pass,
            "agree_fail": agree_fail,
            "disagree": disagree,
            "single_model": single,
            "agreement_rate": (agree_pass + agree_fail) / max(total - single, 1) * 100 if total > single else 0
        }


# Singleton cache
_validator_cache: Dict[str, DualModelValidator] = {}


def get_validator(model_a: str = "kimi-coding", model_b: Optional[str] = None) -> DualModelValidator:
    """Get or create validator instance with specified models."""
    cache_key = f"{model_a}:{model_b or 'none'}"
    if cache_key not in _validator_cache:
        _validator_cache[cache_key] = DualModelValidator(model_a, model_b)
    return _validator_cache[cache_key]
