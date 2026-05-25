#!/usr/bin/env python3
"""
Cross-Reference Consistency Audit v2
Entity-aware matching, proper figure/table citation detection,
improved SD/SEM confusion logic.
"""

import json
import re
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Set, Tuple


@dataclass
class ConsistencyFlag:
    flag_type: str
    severity: str
    locations: List[str]
    description: str
    value_a: Optional[str]
    value_b: Optional[str]
    recommendation: str
    check_type: str = "deterministic"  # deterministic / heuristic / llm_assisted


@dataclass
class ResultEntity:
    """A unified entity extracted from manuscript for cross-reference matching."""
    entity_type: str        # "mean_sd", "p_value", "sample_size", "proportion"
    section: str            # "abstract", "methods", "results", "table_1", "figure_2"
    experiment_id: Optional[str]
    metric: Optional[str]   # variable name, test name
    group: Optional[str]    # treatment, control, etc.
    value: float
    aux_value: Optional[float]  # SD, SEM, etc.
    n: Optional[int]
    raw_text: str


def extract_n_values(stats: Dict[str, Any]) -> List[ResultEntity]:
    """Extract all sample size mentions as entities."""
    entities = []
    for location, data in stats.items():
        # From descriptives
        for desc in data.get("descriptives", []):
            n = desc.get("n")
            if n:
                entities.append(ResultEntity(
                    entity_type="sample_size",
                    section=location,
                    experiment_id=None,
                    metric=desc.get("variable") or desc.get("raw_text", "")[:40],
                    group=None,
                    value=float(n),
                    aux_value=None,
                    n=n,
                    raw_text=desc.get("raw_text", ""),
                ))
        # From NHST df
        for nhst in data.get("nhst", []):
            tt = nhst.get("test_type", "")
            df1 = nhst.get("df1")
            df2 = nhst.get("df2")
            if tt == "t" and df1 is not None:
                n_est = int(df1) + 2  # df = N-2 for independent t
                entities.append(ResultEntity(
                    entity_type="sample_size",
                    section=location,
                    experiment_id=None,
                    metric=f"t-test: {nhst.get('raw_text', '')[:30]}",
                    group=None,
                    value=float(n_est),
                    aux_value=None,
                    n=n_est,
                    raw_text=nhst.get("raw_text", ""),
                ))
        # From proportions
        for prop in data.get("proportions", []):
            n = prop.get("total_n")
            if n:
                entities.append(ResultEntity(
                    entity_type="sample_size",
                    section=location,
                    experiment_id=None,
                    metric=f"proportion: {prop.get('raw_text', '')[:30]}",
                    group=None,
                    value=float(n),
                    aux_value=None,
                    n=n,
                    raw_text=prop.get("raw_text", ""),
                ))
        # P0: From standalone N mentions (e.g. "N = 120")
        for sn in data.get("standalone_n", []):
            val = sn.get("value")
            if val:
                entities.append(ResultEntity(
                    entity_type="sample_size",
                    section=location,
                    experiment_id=None,
                    metric=sn.get("raw_text", "")[:40],
                    group=None,
                    value=float(val),
                    aux_value=None,
                    n=int(val),
                    raw_text=sn.get("raw_text", ""),
                ))
    return entities


def check_n_consistency(entities: List[ResultEntity]) -> List[ConsistencyFlag]:
    """Check N consistency across sections by comparing entities."""
    flags = []
    # Group entities by rough metric name similarity
    section_order = {"abstract": 0, "methods": 1, "results": 2}

    # Find pairs of entities with same section type but different N
    for i, e1 in enumerate(entities):
        for e2 in entities[i+1:]:
            if e1.section == e2.section:
                continue  # Same section

            # Check if both are from text sections (not tables)
            s1 = e1.section.lower()
            s2 = e2.section.lower()

            # Only compare key sections: abstract vs methods vs results
            is_key1 = any(k in s1 for k in ["abstract", "method", "result"])
            is_key2 = any(k in s2 for k in ["abstract", "method", "result"])

            if not (is_key1 and is_key2):
                continue

            # N difference threshold
            if abs(e1.value - e2.value) >= 2:
                flags.append(ConsistencyFlag(
                    flag_type="n_mismatch",
                    severity="medium",
                    locations=[e1.section, e2.section],
                    description=f"样本量不一致: {e1.section} N={int(e1.value)} vs {e2.section} N={int(e2.value)}",
                    value_a=str(int(e1.value)),
                    value_b=str(int(e2.value)),
                    recommendation="核实各章节报告的样本量是否对应同一实验/分析",
                ))
                # Only report once per pair type
                break

    return flags


def check_p_consistency_v2(stats: Dict[str, Any]) -> List[ConsistencyFlag]:
    """Check p-value consistency with decision-error priority."""
    flags = []
    for location, data in stats.items():
        for nhst in data.get("nhst", []):
            computed = nhst.get("computed_p")
            reported = nhst.get("reported_p_value")
            sign = nhst.get("sign")
            raw = nhst.get("raw_text", "")
            tt = nhst.get("test_type", "")
            df1 = nhst.get("df1")
            decision_error = nhst.get("decision_error", False)

            if computed is None:
                continue

            # Decision error is highest priority
            if decision_error:
                flags.append(ConsistencyFlag(
                    flag_type="p_decision_error",
                    severity="high",
                    locations=[location],
                    description=f"【显著性结论翻转】{tt}({df1})={nhst['test_statistic']}, "
                               f"报告 p{nhst.get('reported_p_expr', '')} 暗示显著, "
                               f"但重算 p={computed:.4f} 暗示不显著",
                    value_a=f"reported p{nhst.get('reported_p_expr', '')}",
                    value_b=f"computed p={computed:.4f}",
                    recommendation="重新计算p值或修正报告值; 核实是否为单尾检验",
                    check_type="deterministic",
                ))
            elif sign == "=" and reported is not None and abs(computed - reported) > 0.01:
                flags.append(ConsistencyFlag(
                    flag_type="p_mismatch",
                    severity="medium",
                    locations=[location],
                    description=f"p值数值偏差: 报告={reported}, 重算={computed:.4f}",
                    value_a=str(reported),
                    value_b=f"{computed:.4f}",
                    recommendation="核实test statistic和degrees of freedom",
                    check_type="deterministic",
                ))

    return flags


def check_mean_consistency(stats: Dict[str, Any]) -> List[ConsistencyFlag]:
    flags = []
    means_by_ctx: Dict[str, List[Dict]] = {}

    for location, data in stats.items():
        for desc in data.get("descriptives", []):
            mean = desc.get("mean")
            if mean is None:
                continue
            # Use first few chars of raw text as grouping key
            key = desc.get("raw_text", "")[:25].strip()
            means_by_ctx.setdefault(key, []).append({
                "location": location,
                "mean": mean,
                "sd": desc.get("sd"),
                "n": desc.get("n"),
                "raw": desc.get("raw_text", ""),
            })

    for key, entries in means_by_ctx.items():
        if len(entries) <= 1:
            continue
        for i in range(len(entries)):
            for j in range(i+1, len(entries)):
                a, b = entries[i], entries[j]
                if a["location"] == b["location"]:
                    continue
                diff = abs(a["mean"] - b["mean"])
                if diff > 0.01:
                    rel = diff / max(abs(a["mean"]), 0.001)
                    sev = "high" if rel > 0.05 else "medium"
                    flags.append(ConsistencyFlag(
                        flag_type="mean_mismatch",
                        severity=sev,
                        locations=[a["location"], b["location"]],
                        description=f"同一指标均值不一致: {a['mean']:.4f} vs {b['mean']:.4f} (diff={diff:.4f})",
                        value_a=f"{a['mean']:.4f}",
                        value_b=f"{b['mean']:.4f}",
                        recommendation="核实哪个值正确，确保全文一致",
                    ))

                if a.get("sd") and b.get("sd") and abs(a["sd"] - b["sd"]) > 0.01:
                    flags.append(ConsistencyFlag(
                        flag_type="sd_mismatch",
                        severity="medium",
                        locations=[a["location"], b["location"]],
                        description=f"同一指标SD不一致: {a['sd']:.4f} vs {b['sd']:.4f}",
                        value_a=f"{a['sd']:.4f}",
                        value_b=f"{b['sd']:.4f}",
                        recommendation="核实SD值，检查SD/SEM是否混淆",
                    ))
    return flags


def check_sd_sem_confusion_v2(stats: Dict[str, Any]) -> List[ConsistencyFlag]:
    """
    P1-9: Only flag SD/SEM confusion when BOTH labels exist for same metric,
    or when the same value appears in two locations with different labels,
    or when SD ~= SEM * sqrt(N) for the same metric.
    """
    flags = []
    # Collect all descriptives with labels
    labeled_items: List[Dict] = []
    for location, data in stats.items():
        for desc in data.get("descriptives", []):
            label = desc.get("spread_label", "")
            if label in ("SD", "SEM", "SE"):
                labeled_items.append({
                    "location": location,
                    "mean": desc.get("mean"),
                    "sd": desc.get("sd"),
                    "sem": desc.get("sem"),
                    "spread": desc.get("sd") or desc.get("sem"),
                    "label": label,
                    "n": desc.get("n"),
                    "raw": desc.get("raw_text", ""),
                })

    # Check pairs: same mean, different labels, ratio ~= sqrt(n)
    for i, a in enumerate(labeled_items):
        for b in labeled_items[i+1:]:
            if a["label"] == b["label"]:
                continue  # Same label, no confusion
            if a["mean"] != b["mean"]:
                continue  # Different metrics

            # Check ratio
            val_a = a["spread"] or 0
            val_b = b["spread"] or 0
            if val_a <= 0 or val_b <= 0:
                continue

            n = a["n"] or b["n"]
            if n and n > 1:
                ratio = max(val_a, val_b) / min(val_a, val_b)
                expected_ratio = n ** 0.5
                if abs(ratio - expected_ratio) < expected_ratio * 0.3:
                    flags.append(ConsistencyFlag(
                        flag_type="sd_sem_confusion",
                        severity="medium",
                        locations=[a["location"], b["location"]],
                        description=f"SD/SEM可能混淆: 位置1={a['label']}={val_a}, "
                                   f"位置2={b['label']}={val_b}, 比值≈√N={expected_ratio:.1f}",
                        value_a=f"{a['label']}={val_a}",
                        value_b=f"{b['label']}={val_b}",
                        recommendation="核实同一指标在不同位置的SD/SEM标注是否一致",
                    ))
                    break

    return flags


def check_figure_table_citations_v2(full_text: str) -> List[ConsistencyFlag]:
    """
    P1-10: Separate figure/table declarations (captions) from in-text citations.
    Declarations: "Figure 1.", "Table 2 —", "Fig. 3:", \\caption{}
    Citations: "as shown in Figure 1", "see Fig. 2", "Figure 3 shows"
    """
    flags = []
    if not full_text:
        return flags

    # Find all declared figures/tables (captions)
    decl_fig = set(re.findall(r'(?:Figure|Fig\.?)\s+(\d+)[\.:\n]', full_text, re.IGNORECASE))
    decl_tbl = set(re.findall(r'Table\s+(\d+)[\.:\n]', full_text, re.IGNORECASE))

    # Find all in-text citations (different pattern)
    cite_patterns = [
        re.compile(r'(?:in|from|see|as shown in|according to|as in)\s+(?:Figure|Fig\.?)\s+(\d+)', re.IGNORECASE),
        re.compile(r'(?:Figure|Fig\.?)\s+(\d+)\s+(?:shows?|displays?|presents?|illustrates?|depicts?)', re.IGNORECASE),
        re.compile(r'(?:in|from|see|as shown in)\s+Table\s+(\d+)', re.IGNORECASE),
        re.compile(r'Table\s+(\d+)\s+(?:shows?|displays?|presents?|summarizes?)', re.IGNORECASE),
    ]

    cited_figs: Set[str] = set()
    cited_tbls: Set[str] = set()

    for pat in cite_patterns:
        for m in pat.finditer(full_text):
            num = m.group(1)
            # Classify based on what was matched
            matched_text = m.group(0).lower()
            if "fig" in matched_text or "figure" in matched_text:
                cited_figs.add(num)
            elif "table" in matched_text:
                cited_tbls.add(num)

    # Uncited declarations
    for fig in decl_fig - cited_figs:
        flags.append(ConsistencyFlag(
            flag_type="uncited_figure",
            severity="low",
            locations=["manuscript"],
            description=f"Figure {fig} 可能在正文中未被引用",
            value_a=None, value_b=None,
            recommendation=f"在Results或Discussion中添加对Figure {fig}的引用",
        ))
    for tbl in decl_tbl - cited_tbls:
        flags.append(ConsistencyFlag(
            flag_type="uncited_table",
            severity="low",
            locations=["manuscript"],
            description=f"Table {tbl} 可能在正文中未被引用",
            value_a=None, value_b=None,
            recommendation=f"在Results中添加对Table {tbl}的引用",
        ))

    return flags


def run_cross_reference_audit(extracted_stats: Dict[str, Any],
                               full_text: str = "") -> Dict[str, Any]:
    all_flags: List[ConsistencyFlag] = []

    # N consistency
    n_entities = extract_n_values(extracted_stats)
    all_flags.extend(check_n_consistency(n_entities))

    # Mean/SD consistency
    all_flags.extend(check_mean_consistency(extracted_stats))

    # P-value consistency (v2 with decision_error priority)
    all_flags.extend(check_p_consistency_v2(extracted_stats))

    # SD/SEM confusion (v2)
    all_flags.extend(check_sd_sem_confusion_v2(extracted_stats))

    # Figure/table citations (v2)
    if full_text:
        all_flags.extend(check_figure_table_citations_v2(full_text))

    high = [f for f in all_flags if f.severity == "high"]
    medium = [f for f in all_flags if f.severity == "medium"]
    low = [f for f in all_flags if f.severity == "low"]

    return {
        "flags": [asdict(f) for f in all_flags],
        "summary": {"total_flags": len(all_flags), "high": len(high),
                    "medium": len(medium), "low": len(low)},
        "by_severity": {
            "high": [asdict(f) for f in high],
            "medium": [asdict(f) for f in medium],
            "low": [asdict(f) for f in low],
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Cross-reference audit")
    parser.add_argument("--input", "-i", required=True, help="Input JSON")
    parser.add_argument("--output", "-o", default="cross_ref_audit.json", help="Output JSON")
    parser.add_argument("--text", "-t", help="Full manuscript text")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = run_cross_reference_audit(data, args.text or "")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    s = results["summary"]
    print(f"Audit: {s['total_flags']} flags (High: {s['high']}, Medium: {s['medium']}, Low: {s['low']})")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
