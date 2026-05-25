"""
Manuscript Statistics Extractor
Extracts NHST statistics, descriptive statistics, and LLM metrics from manuscripts.
"""

import re
import os
from typing import List, Dict, Any

try:
    import docx
except ImportError:
    docx = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def extract_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    if docx is None:
        return ""
    try:
        document = docx.Document(file_path)
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    if fitz is None:
        return ""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception:
        return ""


def extract_statistics(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract statistical values from manuscript.
    Returns list of extracted statistics with metadata.
    """
    # Determine file type and extract text
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        text = extract_from_docx(file_path)
    elif ext == '.pdf':
        text = extract_from_pdf(file_path)
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    
    stats = []
    lines = text.split('\n')
    
    # Pattern definitions for common statistical notations
    patterns = {
        'p_value': re.compile(
            r'p\s*[<>=]\s*(0?\.\d+)|p\s*=\s*(0?\.\d+(?:e[+-]?\d+)?)',
            re.IGNORECASE
        ),
        'mean_sd': re.compile(
            r'(\d+\.?\d*)\s*±\s*(\d+\.?\d*)',
            re.IGNORECASE
        ),
        'mean_sem': re.compile(
            r'(\d+\.?\d*)\s*\(\s*SEM\s*[=:]?\s*(\d+\.?\d*)\s*\)',
            re.IGNORECASE
        ),
        't_test': re.compile(
            r't\s*\(\s*(\d+)\s*\)\s*[=:]?\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
        'f_test': re.compile(
            r'F\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*[=:]?\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
        'chi_square': re.compile(
            r'χ²\s*\(\s*(\d+)\s*\)\s*[=:]?\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
        'correlation': re.compile(
            r'r\s*\(\s*(\d+)\s*\)\s*[=:]?\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
        'cohen_d': re.compile(
            r'd\s*[=:]?\s*([+-]?\d+\.?\d*)',
            re.IGNORECASE
        ),
        'sample_size': re.compile(
            r'N\s*[=:]?\s*(\d+)',
            re.IGNORECASE
        ),
    }
    
    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        
        # Extract p-values
        for match in patterns['p_value'].finditer(line):
            p_val = match.group(1) or match.group(2)
            if p_val:
                stats.append({
                    'type': 'p_value',
                    'value': float(p_val),
                    'raw': match.group(0),
                    'line': line_num,
                    'context': line.strip()[:200]
                })
        
        # Extract mean ± SD
        for match in patterns['mean_sd'].finditer(line):
            stats.append({
                'type': 'mean',
                'value': float(match.group(1)),
                'sd': float(match.group(2)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract mean (SEM)
        for match in patterns['mean_sem'].finditer(line):
            stats.append({
                'type': 'mean_sem',
                'value': float(match.group(1)),
                'sem': float(match.group(2)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract t-tests
        for match in patterns['t_test'].finditer(line):
            stats.append({
                'type': 't_test',
                'df': int(match.group(1)),
                'value': float(match.group(2)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract F-tests
        for match in patterns['f_test'].finditer(line):
            stats.append({
                'type': 'f_test',
                'df1': int(match.group(1)),
                'df2': int(match.group(2)),
                'value': float(match.group(3)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract chi-square
        for match in patterns['chi_square'].finditer(line):
            stats.append({
                'type': 'chi_square',
                'df': int(match.group(1)),
                'value': float(match.group(2)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract correlations
        for match in patterns['correlation'].finditer(line):
            stats.append({
                'type': 'correlation',
                'df': int(match.group(1)),
                'value': float(match.group(2)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract Cohen's d
        for match in patterns['cohen_d'].finditer(line):
            stats.append({
                'type': 'cohen_d',
                'value': float(match.group(1)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
        
        # Extract sample sizes
        for match in patterns['sample_size'].finditer(line):
            stats.append({
                'type': 'sample_size',
                'value': int(match.group(1)),
                'raw': match.group(0),
                'line': line_num,
                'context': line.strip()[:200]
            })
    
    return stats


if __name__ == '__main__':
    # Test extraction
    test_text = """
    The mean score was 3.45 ± 1.23. 
    t(28) = 2.45, p = 0.018.
    F(2, 27) = 4.56, p < 0.05.
    χ²(1) = 3.84, p = 0.05.
    r(30) = 0.45, p = 0.01.
    Cohen's d = 0.82.
    N = 50.
    """
    
    with open('/tmp/test_manuscript.txt', 'w') as f:
        f.write(test_text)
    
    results = extract_statistics('/tmp/test_manuscript.txt')
    print(f"Extracted {len(results)} statistics:")
    for r in results:
        print(f"  {r['type']}: {r['raw']} (line {r['line']})")
