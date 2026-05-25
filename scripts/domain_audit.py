#!/usr/bin/env python3
"""
Domain-Specific Audit v1
Presence/absence checks for LLM/Agent and Bioinformatics+ML papers.
These are keyword-based heuristic checks, not deep reasoning.

Usage:
    python domain_audit.py --input stats.json --text "manuscript.txt" --domain llm_agent --output domain.json
"""

import json
import re
import argparse
from typing import Dict, Any, List


# Negation-aware matcher: if a negation word appears within 8 tokens
# of the match, it's likely a negative mention ("no external validation")
NEGATION_WORDS = re.compile(
    r'\b(no|not|without|absent|lack|lacking|did not|does not|do not|'
    r'never|none|non-|failing to|failure to|omitting|omit|missed|missing|'
    r'unable to|cannot|could not|was not|were not|wasn\'t|weren\'t|'
    r'didn\'t|don\'t|doesn\'t|no)\b',
    re.IGNORECASE
)


def has_positive_mention(text: str, pattern: str, window: int = 8) -> bool:
    """
    Check if pattern matches in text AND the match is NOT negated
    (i.e. no negation word within `window` tokens before it).
    """
    pat = re.compile(pattern, re.IGNORECASE)
    for m in pat.finditer(text):
        start = m.start()
        prefix = text[max(0, start - 120):start]
        prefix_tokens = prefix.split()
        recent_tokens = prefix_tokens[-window:] if len(prefix_tokens) > window else prefix_tokens
        prefix_text = " ".join(recent_tokens)
        if NEGATION_WORDS.search(prefix_text):
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# LLM/Agent paper audit
# ---------------------------------------------------------------------------

def audit_llm_agent(text: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """Presence/absence checks for LLM/Agent papers."""
    flags = []
    lower = text.lower()

    # Rule 1: seed/variance reporting
    has_seed = has_positive_mention(lower, r'\bseed[s]?\b')
    has_std = has_positive_mention(lower, r'(?:±|\\pm|std|standard deviation|sd\s*=|std\s*=)')
    has_ci = has_positive_mention(lower, r'(?:confidence interval|95% CI|CI\s*\[)')
    if not (has_seed or has_std or has_ci):
        flags.append({
            "flag_type": "llm_seed_variance_missing",
            "severity": "medium",
            "category": "reporting_completeness",
            "description": "未报告多随机种子结果或方差估计 (seed/std/CI)",
            "recommendation": "NeurIPS checklist建议报告mean±std over multiple seeds或提供confidence interval",
            "check_type": "heuristic",
        })

    # Rule 2: baseline fairness indicators
    baseline_checks = [
        ("model size", r'(?:model size|parameter[s]?|\d+B|\d+\s*billion)'),
        ("temperature", r'temperature\s*[=:]\s*\d'),
        ("tool access", r'(?:tool[s]? access|api access|function call)'),
        ("retrieval", r'(?:retriev|search engine|knowledge base)'),
        ("budget", r'(?:budget|max token|token limit|turn limit)'),
    ]
    missing_baseline = []
    for name, pat in baseline_checks:
        if not has_positive_mention(lower, pat):
            missing_baseline.append(name)
    if len(missing_baseline) >= 3:
        flags.append({
            "flag_type": "llm_baseline_fairness_unclear",
            "severity": "low",
            "category": "reporting_completeness",
            "description": f"baseline设置可能不完整，缺少: {', '.join(missing_baseline[:3])}...",
            "recommendation": "确保baseline使用相同模型规模、temperature、工具权限和budget",
            "check_type": "heuristic",
        })

    # Rule 3: ablation completeness
    ablation_indicators = [
        ("w/o tools", r'(?:without tool|w/o tool|no tool|abl.*tool)'),
        ("w/o memory", r'(?:without memor|w/o memor|no memor|abl.*memor)'),
        ("w/o planning", r'(?:without plan|w/o plan|no plan|abl.*plan)'),
        ("w/o reflection", r'(?:without reflect|w/o reflect|no reflect|abl.*reflect)'),
        ("w/o RAG", r'(?:without RAG|w/o RAG|no RAG|abl.*RAG)'),
    ]
    found_ablations = [name for name, pat in ablation_indicators if has_positive_mention(lower, pat)]
    if len(found_ablations) < 2 and "ablation" in lower:
        flags.append({
            "flag_type": "llm_ablation_incomplete",
            "severity": "low",
            "category": "reporting_completeness",
            "description": f"ablation可能不完整，仅发现: {found_ablations or '无明确ablation'}",
            "recommendation": "关键ablation应包括: 无tools、无memory、无planning、无reflection、无RAG",
            "check_type": "heuristic",
        })

    # Rule 4: cost/latency reporting
    has_cost = has_positive_mention(lower, r'\b(?:cost|latency|token[s]?|api call|wall.?clock|runtime)\b')
    if not has_cost:
        flags.append({
            "flag_type": "llm_cost_latency_missing",
            "severity": "low",
            "category": "reporting_completeness",
            "description": "未报告cost、latency或token使用量",
            "recommendation": "Agent论文应报告token cost/latency/API调用次数，以便效率比较",
            "check_type": "heuristic",
        })

    # Rule 5: LLM-as-judge disclosure
    judge_checks = [
        ("judge model", r'(?:judge model|evaluator model|gpt-4.*judge)'),
        ("judge prompt", r'(?:judge prompt|evaluation prompt|prompt.*evaluat)'),
        ("judge temperature", r'(?:judge.*temperature|evaluator.*temperature)'),
        ("human agreement", r'(?:human agreement|inter.?annotator|human evaluat)'),
    ]
    has_judge = has_positive_mention(lower, r'(?:llm.?as.?judge|llm.?judge|gpt-4.*evaluat)')
    if has_judge:
        missing_judge = [name for name, pat in judge_checks if not has_positive_mention(lower, pat)]
        if missing_judge:
            flags.append({
                "flag_type": "llm_judge_incomplete",
                "severity": "medium",
                "category": "reporting_completeness",
                "description": f"LLM-as-judge设置披露不完整，缺少: {', '.join(missing_judge[:3])}",
                "recommendation": "报告judge model、prompt、temperature、human agreement和order bias检查",
                "check_type": "heuristic",
            })

    # Rule 6: benchmark contamination
    has_contamination = has_positive_mention(lower, r'(?:contamination|data leak|train.*test overlap|benchmark version)')
    has_benchmark = has_positive_mention(lower, r'(?:benchmark|dataset|MMLU|GSM8K|HumanEval|MBPP|HotpotQA)')
    if has_benchmark and not has_contamination:
        flags.append({
            "flag_type": "llm_benchmark_contamination_check_missing",
            "severity": "low",
            "category": "reporting_completeness",
            "description": "使用了benchmark但未检查/报告contamination",
            "recommendation": "明确声明是否检查了test set contamination和benchmark version",
            "check_type": "heuristic",
        })

    # Count LLM metrics extracted
    total_llm_metrics = sum(len(s.get("llm_metrics", [])) for s in stats.values())

    return {
        "domain": "llm_agent",
        "flags": flags,
        "summary": {
            "total_flags": len(flags),
            "high": len([f for f in flags if f["severity"] == "high"]),
            "medium": len([f for f in flags if f["severity"] == "medium"]),
            "low": len([f for f in flags if f["severity"] == "low"]),
            "llm_metrics_extracted": total_llm_metrics,
            "has_seed_reporting": has_seed or has_std or has_ci,
            "has_cost_latency": has_cost,
            "has_ablation": len(found_ablations) >= 2 if "ablation" in lower else None,
        },
    }


# ---------------------------------------------------------------------------
# Bioinformatics + ML audit
# ---------------------------------------------------------------------------

def audit_bioinformatics_ml(text: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """Presence/absence checks for bioinformatics + ML papers."""
    flags = []
    lower = text.lower()

    # Rule 1: patient-wise / group-wise split (negation-aware)
    has_patient_split = has_positive_mention(
        lower, r'(?:patient.wise|subject.wise|donor.wise|group.wise|'
        r'patient.level|subject.level|leave.one.patient)'
    )
    has_random_split = has_positive_mention(lower, r'random split|randomly split')
    if has_random_split and not has_patient_split:
        flags.append({
            "flag_type": "bio_random_split_warning",
            "severity": "medium",
            "category": "reporting_completeness",
            "description": "使用random split而非patient-wise split",
            "recommendation": "生物医学数据应按patient/subject/donor分组切分，避免同一样本进入train和test",
            "check_type": "heuristic",
        })

    # Rule 2: batch effect (negation-aware)
    has_batch = has_positive_mention(
        lower, r'(?:batch effect|batch correction|combat|harmoniz|sequencing center|platform correction)'
    )
    has_omics = has_positive_mention(lower, r'(?:omics|transcriptomic|proteomic|genomic|metabolomic|scRNA|RNA-seq)')
    if has_omics and not has_batch:
        flags.append({
            "flag_type": "bio_batch_effect_unchecked",
            "severity": "medium",
            "category": "reporting_completeness",
            "description": "组学数据未报告batch effect检查或校正",
            "recommendation": "报告batch、platform、sequencing center，并在正确范围内拟合batch correction",
            "check_type": "heuristic",
        })

    # Rule 3: feature selection leakage
    has_fs_leakage_check = has_positive_mention(
        lower, r'(?:feature selection before split|feature selection.*train|prevent.*leakage)'
    )
    has_feature_selection = has_positive_mention(
        lower, r'(?:feature selection|differential expression|DE analysis|marker gene)'
    )
    if has_feature_selection and not has_fs_leakage_check:
        flags.append({
            "flag_type": "bio_feature_selection_leakage_risk",
            "severity": "high",
            "category": "reporting_completeness",
            "description": "feature selection可能在全数据上进行，存在data leakage风险",
            "recommendation": "feature selection必须在train set内部完成，不能先在整个数据集上选特征再split",
            "check_type": "heuristic",
        })

    # Rule 4: external validation (negation-aware — "no external validation" should NOT count)
    has_external = has_positive_mention(
        lower, r'(?:external cohort|independent dataset|held.out|validation cohort|test cohort|prospective)'
    )
    has_cv_only = has_positive_mention(lower, r'(?:cross.validation|CV|k.fold)')
    if has_cv_only and not has_external:
        flags.append({
            "flag_type": "bio_no_external_validation",
            "severity": "medium",
            "category": "reporting_completeness",
            "description": "仅有内部cross-validation，无独立外部验证",
            "recommendation": "生物标志物/预测模型应在独立cohort/external dataset上验证",
            "check_type": "heuristic",
        })

    # Rule 5: multiple testing correction
    has_fdr = has_positive_mention(lower, r'(?:FDR|false discovery rate|Benjamini|q.value|adjusted p)')
    has_multiple_testing = has_positive_mention(
        lower, r'(?:differential expression|enrichment analysis|GWAS|multiple comparison|multiple test)'
    )
    if has_multiple_testing and not has_fdr:
        flags.append({
            "flag_type": "bio_multiple_testing_uncorrected",
            "severity": "high",
            "category": "reporting_completeness",
            "description": "多重检验未报告FDR/q-value校正",
            "recommendation": "差异表达/通路富集/GWAS必须报告FDR或q-value",
            "check_type": "heuristic",
        })

    # Rule 6: technical vs biological replicates
    has_replicate_type = has_positive_mention(
        lower, r'(?:biological replicate|technical replicate|independent sample)'
    )
    has_omics_exp = has_positive_mention(lower, r'(?:cell line|tissue sample|biopsy|patient sample)')
    if has_omics_exp and not has_replicate_type:
        flags.append({
            "flag_type": "bio_replicate_type_undefined",
            "severity": "low",
            "category": "reporting_completeness",
            "description": "未区分biological replicates与technical replicates",
            "recommendation": "明确N是按独立样本还是按技术重复计算",
            "check_type": "heuristic",
        })

    return {
        "domain": "bioinformatics_ml",
        "flags": flags,
        "summary": {
            "total_flags": len(flags),
            "high": len([f for f in flags if f["severity"] == "high"]),
            "medium": len([f for f in flags if f["severity"] == "medium"]),
            "low": len([f for f in flags if f["severity"] == "low"]),
        },
    }


def run_domain_audit(text: str, stats: Dict[str, Any], domain: str) -> Dict[str, Any]:
    if domain == "llm_agent":
        return audit_llm_agent(text, stats)
    elif domain == "bioinformatics_ml":
        return audit_bioinformatics_ml(text, stats)
    else:
        return {"domain": domain, "flags": [], "summary": {"total_flags": 0, "note": "general domain: no specific checks"}}


def main():
    parser = argparse.ArgumentParser(description="Domain-specific audit")
    parser.add_argument("--input", "-i", required=True, help="stats.json from extractor")
    parser.add_argument("--text", "-t", required=True, help="manuscript text file")
    parser.add_argument("--domain", "-d", required=True, choices=["llm_agent", "bioinformatics_ml", "general"])
    parser.add_argument("--output", "-o", default="domain_audit.json", help="output JSON")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        stats = json.load(f)
    with open(args.text, "r", encoding="utf-8") as f:
        text = f.read()

    result = run_domain_audit(text, stats, args.domain)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    s = result["summary"]
    print(f"Domain audit ({args.domain}): {s.get('total_flags', 0)} flags")
    print(f"  High: {s.get('high', 0)}, Medium: {s.get('medium', 0)}, Low: {s.get('low', 0)}")


if __name__ == "__main__":
    main()
