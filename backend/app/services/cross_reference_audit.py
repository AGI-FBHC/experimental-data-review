"""
Cross-Reference Audit
Checks consistency between Abstract, Results, Tables, and Captions.
"""

from typing import List, Dict, Any


def find_value_in_context(value: float, contexts: List[str], tolerance: float = 0.01) -> bool:
    """Check if a value appears in any of the given contexts."""
    for context in contexts:
        # Simple string matching (in production, use more sophisticated matching)
        if str(value) in context or str(round(value, 2)) in context:
            return True
    return False


def run_cross_reference_audit(stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Audit cross-location consistency of statistics.
    In a real implementation, this would compare values across:
    - Abstract
    - Results section
    - Tables
    - Figure captions
    """
    results = []
    
    # Group by type
    p_values = [s for s in stats if s['type'] == 'p_value']
    means = [s for s in stats if s['type'] == 'mean']
    
    # Check for duplicate p-values with different significances
    for i, p1 in enumerate(p_values):
        for p2 in p_values[i+1:]:
            if abs(p1['value'] - p2['value']) < 0.001:
                # Same p-value found in different locations
                results.append({
                    'is_error': False,
                    'type': 'duplicate_p_value',
                    'value': p1['value'],
                    'locations': [p1.get('line', 0), p2.get('line', 0)],
                    'message': f"Same p-value {p1['value']} appears in multiple locations"
                })
    
    # Check for mean inconsistencies
    for i, m1 in enumerate(means):
        for m2 in means[i+1:]:
            # If same context but different values
            if m1.get('context', '')[:50] == m2.get('context', '')[:50]:
                if abs(m1['value'] - m2['value']) > 0.01:
                    results.append({
                        'is_error': True,
                        'type': 'inconsistent_mean',
                        'value1': m1['value'],
                        'value2': m2['value'],
                        'locations': [m1.get('line', 0), m2.get('line', 0)],
                        'message': f"Inconsistent means: {m1['value']} vs {m2['value']}"
                    })
    
    return results


if __name__ == '__main__':
    test_stats = [
        {'type': 'p_value', 'value': 0.05, 'line': 10, 'context': 'p = 0.05'},
        {'type': 'p_value', 'value': 0.05, 'line': 25, 'context': 'p = 0.05'},
        {'type': 'mean', 'value': 3.45, 'line': 15, 'context': 'Group A mean = 3.45'},
        {'type': 'mean', 'value': 3.46, 'line': 16, 'context': 'Group A mean = 3.46'},
    ]
    
    results = run_cross_reference_audit(test_stats)
    print(f"Cross-Reference Audit: {len(results)} issues")
    for r in results:
        status = "❌" if r['is_error'] else "⚠️"
        print(f"  {status} {r['type']}: {r['message']}")
