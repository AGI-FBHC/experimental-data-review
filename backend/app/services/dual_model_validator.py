"""
Dual-Model Validation Service
Coordinates two independent LLM validators and resolves disagreements.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ConsensusStatus(Enum):
    AGREE_PASS = "agree_pass"
    AGREE_FAIL = "agree_fail"
    DISAGREE = "disagree"
    PARTIAL = "partial"


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
    validator_b: ValidationResult
    merged_issues: List[Dict[str, Any]]
    disagreement_areas: List[str]
    recommendation: str


class DualModelValidator:
    """
    Dual-model validation coordinator.
    
    Usage:
        validator = DualModelValidator()
        result = validator.validate(manuscript_text, domain='llm_agent')
        if result.status == ConsensusStatus.DISAGREE:
            # Trigger human review
            pass
    """
    
    def __init__(
        self,
        model_a_name: str = "claude-sonnet-4",
        model_b_name: str = "gemini-2.5-pro",
        consensus_threshold: float = 0.8
    ):
        self.model_a_name = model_a_name
        self.model_b_name = model_b_name
        self.consensus_threshold = consensus_threshold
        self.history: List[ConsensusResult] = []
    
    def validate(
        self,
        manuscript_text: str,
        domain: str = "general",
        extracted_stats: Optional[List[Dict]] = None
    ) -> ConsensusResult:
        """
        Run dual validation on manuscript.
        
        In production, this would call actual LLM APIs.
        For now, returns simulated results based on deterministic checks.
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
        
        # Simulate Model A validation (strict)
        validator_a = self._simulate_validator_a(
            stats, grim_results, cross_results, domain_results
        )
        
        # Simulate Model B validation (lenient)
        validator_b = self._simulate_validator_b(
            stats, grim_results, cross_results, domain_results
        )
        
        # Compute consensus
        consensus = self._compute_consensus(validator_a, validator_b)
        
        # Store history
        self.history.append(consensus)
        
        return consensus
    
    def _simulate_validator_a(
        self,
        stats: List[Dict],
        grim: List[Dict],
        cross: List[Dict],
        domain: List[Dict]
    ) -> ValidationResult:
        """Simulate strict validator (Claude-style)."""
        issues = []
        
        # Strict: flag all GRIM errors
        for r in grim:
            if r.get('is_error'):
                issues.append({
                    'severity': 'high',
                    'category': 'deterministic',
                    'test': r['test'],
                    'message': r['message'],
                    'line': r.get('line', 0)
                })
        
        # Strict: flag all cross-reference errors
        for r in cross:
            if r.get('is_error'):
                issues.append({
                    'severity': 'high',
                    'category': 'consistency',
                    'type': r['type'],
                    'message': r['message']
                })
        
        # Strict: flag all warnings as issues
        for r in domain:
            issues.append({
                'severity': 'medium',
                'category': 'domain',
                'type': r.get('type', 'warning'),
                'message': r['message']
            })
        
        passed = len([i for i in issues if i['severity'] == 'high']) == 0
        
        return ValidationResult(
            model_name=self.model_a_name,
            passed=passed,
            issues=issues,
            confidence=0.85 if passed else 0.75,
            raw_response=json.dumps({"strict_mode": True, "issues_found": len(issues)})
        )
    
    def _simulate_validator_b(
        self,
        stats: List[Dict],
        grim: List[Dict],
        cross: List[Dict],
        domain: List[Dict]
    ) -> ValidationResult:
        """Simulate lenient validator (Gemini-style)."""
        issues = []
        
        # Lenient: only flag severe GRIM errors
        for r in grim:
            if r.get('is_error') and r['test'] == 'GRIM':
                issues.append({
                    'severity': 'high',
                    'category': 'deterministic',
                    'test': r['test'],
                    'message': r['message'],
                    'line': r.get('line', 0)
                })
        
        # Lenient: only flag cross-reference errors if severe
        for r in cross:
            if r.get('is_error') and 'inconsistent' in r.get('message', '').lower():
                issues.append({
                    'severity': 'medium',
                    'category': 'consistency',
                    'type': r['type'],
                    'message': r['message']
                })
        
        # Lenient: ignore domain warnings unless critical
        for r in domain:
            if r.get('severity') == 'critical':
                issues.append({
                    'severity': 'high',
                    'category': 'domain',
                    'type': r.get('type', 'warning'),
                    'message': r['message']
                })
        
        passed = len([i for i in issues if i['severity'] == 'high']) == 0
        
        return ValidationResult(
            model_name=self.model_b_name,
            passed=passed,
            issues=issues,
            confidence=0.80 if passed else 0.70,
            raw_response=json.dumps({"strict_mode": False, "issues_found": len(issues)})
        )
    
    def _compute_consensus(
        self,
        a: ValidationResult,
        b: ValidationResult
    ) -> ConsensusResult:
        """Compute consensus between two validators."""
        
        # Determine consensus status
        if a.passed and b.passed:
            status = ConsensusStatus.AGREE_PASS
        elif not a.passed and not b.passed:
            status = ConsensusStatus.AGREE_FAIL
        else:
            status = ConsensusStatus.DISAGREE
        
        # Merge issues (union)
        all_issues = a.issues + b.issues
        
        # Deduplicate by message
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
                disagreement_areas.append(f"{a.model_name} passed but {b.model_name} found issues")
            elif b.passed and not a.passed:
                disagreement_areas.append(f"{b.model_name} passed but {a.model_name} found issues")
        
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
        
        return {
            "total": total,
            "agree_pass": agree_pass,
            "agree_fail": agree_fail,
            "disagree": disagree,
            "agreement_rate": (agree_pass + agree_fail) / total * 100
        }


# Singleton instance
_validator: Optional[DualModelValidator] = None


def get_validator() -> DualModelValidator:
    """Get or create singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = DualModelValidator()
    return _validator
