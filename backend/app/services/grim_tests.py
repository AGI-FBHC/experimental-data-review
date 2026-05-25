"""
GRIM / GRIMMER / DEBIT Tests
Mathematical consistency checks for reported statistics.
"""

import math
from typing import List, Dict, Any


def grim_test(mean: float, n: int, scale_min: int = 1, scale_max: int = 5) -> Dict[str, Any]:
    """
    GRIM (Granularity-Related Inconsistency of Means) test.
    Checks if a reported mean is mathematically possible given sample size and scale granularity.
    
    For integer scales (e.g., Likert 1-5), the mean must be a multiple of 1/n.
    """
    if n <= 0:
        return {'is_error': True, 'message': 'Invalid sample size'}
    
    # Check if mean is a multiple of 1/n (for integer scales)
    expected_remainder = round(mean * n) / n
    is_consistent = abs(mean - expected_remainder) < 1e-10
    
    return {
        'is_error': not is_consistent,
        'test': 'GRIM',
        'mean': mean,
        'n': n,
        'expected': expected_remainder,
        'message': f"Mean {mean} is {'consistent' if is_consistent else 'inconsistent'} with n={n}"
    }


def grimmer_test(mean: float, sd: float, n: int, scale_min: int = 1, scale_max: int = 5) -> Dict[str, Any]:
    """
    GRIMMER (GRIM for Standard Deviations) test.
    Heuristic check if reported SD is possible given mean and sample size.
    """
    if n <= 1:
        return {'is_error': True, 'message': 'Sample size too small for SD'}
    
    # Maximum possible SD for given scale
    max_sd = math.sqrt((scale_max - scale_min) ** 2 / 4)
    
    # Heuristic: SD should be reasonable
    is_reasonable = sd <= max_sd * 1.1  # Allow 10% tolerance
    
    return {
        'is_error': not is_reasonable,
        'test': 'GRIMMER',
        'mean': mean,
        'sd': sd,
        'n': n,
        'max_possible_sd': max_sd,
        'message': f"SD {sd} is {'reasonable' if is_reasonable else 'unreasonable'} for scale [{scale_min}-{scale_max}]"
    }


def debit_test(mean: float, sd: float, n: int) -> Dict[str, Any]:
    """
    DEBIT (Decimal Binary Inconsistency Test).
    Checks if reported binary SD is consistent with mean.
    """
    if n <= 1 or sd <= 0:
        return {'is_error': False, 'message': 'Cannot test with invalid values'}
    
    # For binary data (0/1), SD is determined by mean
    # SD = sqrt(mean * (1 - mean))
    expected_sd = math.sqrt(mean * (1 - mean))
    is_consistent = abs(sd - expected_sd) < 0.05  # Allow 5% tolerance
    
    return {
        'is_error': not is_consistent,
        'test': 'DEBIT',
        'mean': mean,
        'sd': sd,
        'expected_sd': expected_sd,
        'message': f"SD {sd} vs expected {expected_sd:.4f} for binary data"
    }


def run_grim_tests(stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run GRIM/GRIMMER/DEBIT tests on extracted statistics.
    """
    results = []
    
    # Group stats by context to find related mean/SD pairs
    mean_entries = [s for s in stats if s['type'] == 'mean']
    sample_sizes = [s for s in stats if s['type'] == 'sample_size']
    
    # Default sample size if not found
    default_n = sample_sizes[0]['value'] if sample_sizes else 30
    
    for stat in mean_entries:
        mean = stat['value']
        sd = stat.get('sd', 0)
        n = default_n
        
        # Run GRIM test
        grim_result = grim_test(mean, n)
        grim_result['line'] = stat.get('line', 0)
        grim_result['context'] = stat.get('context', '')
        results.append(grim_result)
        
        # Run GRIMMER test if SD available
        if sd > 0:
            grimmer_result = grimmer_test(mean, sd, n)
            grimmer_result['line'] = stat.get('line', 0)
            grimmer_result['context'] = stat.get('context', '')
            results.append(grimmer_result)
        
        # Run DEBIT test if data looks binary (mean between 0 and 1)
        if 0 < mean < 1:
            debit_result = debit_test(mean, sd if sd > 0 else 0.5, n)
            debit_result['line'] = stat.get('line', 0)
            debit_result['context'] = stat.get('context', '')
            results.append(debit_result)
    
    return results


if __name__ == '__main__':
    # Test GRIM tests
    test_stats = [
        {'type': 'mean', 'value': 3.45, 'sd': 1.23, 'line': 1, 'context': 'Mean = 3.45 ± 1.23'},
        {'type': 'sample_size', 'value': 30, 'line': 2, 'context': 'N = 30'},
        {'type': 'mean', 'value': 0.75, 'sd': 0.43, 'line': 3, 'context': 'Mean = 0.75 ± 0.43'},
    ]
    
    results = run_grim_tests(test_stats)
    print(f"GRIM Tests: {len(results)} checks")
    for r in results:
        status = "❌" if r['is_error'] else "✅"
        print(f"  {status} {r['test']}: {r['message']}")
