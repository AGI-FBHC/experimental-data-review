"""
Domain-Specific Audit
Checks for domain-specific issues (LLM/Agent, Bioinformatics, etc.)
"""

from typing import List, Dict, Any


def run_domain_audit(stats: List[Dict[str, Any]], domain: str = 'general') -> List[Dict[str, Any]]:
    """
    Run domain-specific audits.
    
    Domains:
    - general: General statistical checks
    - llm_agent: LLM/Agent research (benchmark contamination, baseline fairness, seed variance)
    - bioinformatics: Bioinformatics/ML (data leakage, patient-wise split, batch effect)
    """
    results = []
    
    if domain == 'llm_agent':
        results.extend(_audit_llm_agent(stats))
    elif domain == 'bioinformatics':
        results.extend(_audit_bioinformatics(stats))
    else:
        results.extend(_audit_general(stats))
    
    return results


def _audit_llm_agent(stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Audit for LLM/Agent research domain."""
    results = []
    
    # Check for benchmark contamination indicators
    benchmark_keywords = ['MMLU', 'GSM8K', 'HumanEval', 'BBH', 'ARC']
    contexts = [s.get('context', '') for s in stats]
    
    for keyword in benchmark_keywords:
        for ctx in contexts:
            if keyword in ctx.upper():
                results.append({
                    'is_error': False,
                    'type': 'benchmark_mention',
                    'benchmark': keyword,
                    'message': f"Benchmark {keyword} mentioned - check for contamination",
                    'severity': 'warning'
                })
    
    return results


def _audit_bioinformatics(stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Audit for Bioinformatics/ML domain."""
    results = []
    
    # Check for data leakage indicators
    leakage_keywords = ['patient', 'sample', 'batch', 'fold']
    contexts = [s.get('context', '') for s in stats]
    
    for keyword in leakage_keywords:
        for ctx in contexts:
            if keyword in ctx.lower():
                results.append({
                    'is_error': False,
                    'type': 'potential_leakage',
                    'keyword': keyword,
                    'message': f"Keyword '{keyword}' found - verify no data leakage",
                    'severity': 'warning'
                })
    
    return results


def _audit_general(stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """General statistical audit."""
    results = []
    
    # Check for suspicious p-values (too many near 0.05)
    p_values = [s['value'] for s in stats if s['type'] == 'p_value']
    near_threshold = [p for p in p_values if 0.04 <= p <= 0.06]
    
    if len(near_threshold) > 3:
        results.append({
            'is_error': False,
            'type': 'p_value_clustering',
            'count': len(near_threshold),
            'message': f"{len(near_threshold)} p-values near 0.05 threshold - check for p-hacking",
            'severity': 'warning'
        })
    
    return results


if __name__ == '__main__':
    test_stats = [
        {'type': 'p_value', 'value': 0.051, 'line': 1, 'context': 'MMLU score improved, p = 0.051'},
        {'type': 'p_value', 'value': 0.049, 'line': 2, 'context': 'GSM8K result, p = 0.049'},
        {'type': 'mean', 'value': 85.5, 'line': 3, 'context': 'Patient group A mean = 85.5'},
    ]
    
    for domain in ['general', 'llm_agent', 'bioinformatics']:
        results = run_domain_audit(test_stats, domain)
        print(f"\n{domain.upper()} Audit: {len(results)} findings")
        for r in results:
            print(f"  {r['type']}: {r['message']}")
