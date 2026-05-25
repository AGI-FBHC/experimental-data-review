#!/usr/bin/env python3
"""
Audit Report Generator v2 — Chinese Localization
Generates structured HTML audit reports with check_type annotations,
domain profiles, and full Chinese interface.
"""

import json
import argparse
import html
from pathlib import Path
from datetime import datetime

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>论文统计一致性审查报告</title>
<style>
:root {{
  --red: #dc3545; --orange: #fd7e14; --yellow: #ffc107;
  --green: #28a745; --blue: #007bff; --gray: #6c757d;
  --purple: #6f42c1; --teal: #20c997;
  --bg: #f8f9fa; --card: #ffffff; --text: #212529;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
h2 {{ font-size: 1.3rem; margin: 1.5rem 0 0.75rem; padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--blue); }}
h3 {{ font-size: 1.1rem; margin: 1rem 0 0.5rem; color: var(--blue); }}
.meta {{ color: var(--gray); font-size: 0.9rem; margin-bottom: 1.5rem; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem; margin: 1rem 0; }}
.card {{ background: var(--card); border-radius: 8px; padding: 1.2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.card h4 {{ font-size: 0.85rem; text-transform: uppercase; color: var(--gray);
  margin-bottom: 0.5rem; }}
.card .number {{ font-size: 2rem; font-weight: bold; }}
.card.high {{ border-left: 4px solid var(--red); }}
.card.medium {{ border-left: 4px solid var(--orange); }}
.card.low {{ border-left: 4px solid var(--yellow); }}
.card.pass {{ border-left: 4px solid var(--green); }}
.card.skip {{ border-left: 4px solid var(--gray); }}
.card.heuristic {{ border-left: 4px solid var(--purple); }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0;
  background: var(--card); border-radius: 8px; overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
th {{ background: var(--blue); color: white; padding: 0.75rem 1rem;
  text-align: left; font-weight: 600; font-size: 0.85rem; }}
td {{ padding: 0.75rem 1rem; border-bottom: 1px solid #e9ecef;
  font-size: 0.9rem; vertical-align: top; }}
tr:hover {{ background: #f1f3f5; }}
.badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
.badge-high {{ background: #f8d7da; color: #721c24; }}
.badge-medium {{ background: #fff3cd; color: #856404; }}
.badge-low {{ background: #d1ecf1; color: #0c5460; }}
.badge-pass {{ background: #d4edda; color: #155724; }}
.badge-fail {{ background: #f8d7da; color: #721c24; }}
.badge-skip {{ background: #e2e3e5; color: #383d41; }}
.badge-det {{ background: #d4edda; color: #155724; }}
.badge-heu {{ background: #e2d4f0; color: #4a2c7a; }}
.badge-llm {{ background: #d1ecf1; color: #0c5460; }}
.flag {{ margin: 0.5rem 0; padding: 1rem; border-radius: 6px;
  background: var(--card); box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.flag-high {{ border-left: 4px solid var(--red); }}
.flag-medium {{ border-left: 4px solid var(--orange); }}
.flag-low {{ border-left: 4px solid var(--yellow); }}
.flag-title {{ font-weight: 600; margin-bottom: 0.3rem; }}
.flag-loc {{ font-size: 0.85rem; color: var(--gray); }}
.flag-rec {{ margin-top: 0.5rem; font-size: 0.9rem; color: var(--blue); }}
.raw-text {{ font-family: "Courier New", monospace; background: #f1f3f5;
  padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.85rem; }}
.check-type-tag {{ font-size: 0.75rem; color: var(--purple); font-weight: 600; }}
.domain-tag {{ display: inline-block; background: var(--teal); color: white;
  padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; }}
</style>
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>
"""


def sev_label(sev: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(sev, sev)


def check_type_label(ct: str) -> str:
    return {
        "deterministic": "数学确定",
        "heuristic": "启发式",
        "llm_assisted": "LLM辅助",
    }.get(ct, ct)


def gen_summary_card(title: str, count: int, level: str) -> str:
    return f'<div class="card {level}"><h4>{html.escape(title)}</h4><div class="number">{count}</div></div>'


def gen_nhst_section(extracted: dict) -> str:
    all_nhst = []
    for loc, data in extracted.items():
        for nhst in data.get("nhst", []):
            nhst["_location"] = loc
            all_nhst.append(nhst)

    if not all_nhst:
        return ""

    parts = []
    parts.append(f'<h2>假设检验结果提取 ({len(all_nhst)} 个)</h2>')

    rows = []
    for r in all_nhst:
        de = r.get("decision_error", False)
        status = "结论翻转" if de else ("一致" if r.get("consistent") else ("不一致" if r.get("consistent") is False else "无法判定"))
        badge = "badge-fail" if de else ("badge-pass" if r.get("consistent") else "badge-low")
        ct = r.get("check_type", "deterministic")
        ct_badge = "badge-det" if ct == "deterministic" else "badge-heu"

        df_str = str(r.get("df1", ""))
        if r.get("df2") is not None:
            df_str += f", {r['df2']}"

        raw = html.escape(r.get("raw_text", ""))
        rows.append(f"""<tr>
            <td><span class="badge {badge}">{html.escape(status)}</span></td>
            <td><span class="badge {ct_badge}">{check_type_label(ct)}</span></td>
            <td>{html.escape(r.get("_location", ""))}</td>
            <td><span class="raw-text">{raw}</span></td>
            <td>{r.get("test_type", "")}</td>
            <td>{r.get("test_statistic", "")}</td>
            <td>{df_str}</td>
            <td>{html.escape(str(r.get("reported_p_expr", "")))}</td>
            <td>{f"{r.get('computed_p'):.4f}" if r.get("computed_p") else "N/A"}</td>
        </tr>""")

    parts.append(f"""<table>
        <tr><th>一致性</th><th>检查类型</th><th>位置</th><th>原文</th><th>检验</th>
        <th>统计量</th><th>df</th><th>报告p值</th><th>重算p值</th></tr>
        {''.join(rows)}
    </table>""")

    return "\n".join(parts)


def gen_grim_section(grim_data: dict) -> str:
    if not grim_data:
        return ""

    parts = []
    s = grim_data.get("summary", {})

    cards = []
    cards.append(gen_summary_card("GRIM通过", s.get("grim_pass", 0), "pass"))
    cards.append(gen_summary_card("GRIM失败", s.get("grim_fail", 0), "high"))
    cards.append(gen_summary_card("GRIM跳过", s.get("grim_skip", 0), "skip"))
    cards.append(gen_summary_card("GRIMMER通过", s.get("grimmer_pass", 0), "pass"))
    cards.append(gen_summary_card("GRIMMER失败", s.get("grimmer_fail", 0), "high"))
    cards.append(gen_summary_card("DEBIT通过", s.get("debit_pass", 0), "pass"))
    cards.append(gen_summary_card("DEBIT失败", s.get("debit_fail", 0), "high"))
    cards.append(gen_summary_card("DEBIT跳过", s.get("debit_skip", 0), "skip"))

    parts.append('<h2>描述统计完整性 (GRIM / GRIMMER / DEBIT)</h2>')
    parts.append('<div class="summary-grid">' + "".join(cards) + '</div>')

    # GRIM results
    grim_items = grim_data.get("grim", [])
    if grim_items:
        parts.append('<h3>GRIM 测试结果</h3>')
        rows = []
        for r in grim_items:
            status = r.get("status", "run")
            raw = html.escape(r.get("raw_text", ""))
            if status == "skipped":
                rows.append(f"""<tr>
                    <td><span class="badge badge-skip">跳过</span></td>
                    <td>{html.escape(r.get("location", ""))}</td>
                    <td><span class="raw-text">{raw}</span></td>
                    <td colspan="4">{html.escape(r.get("reason", ""))}</td>
                </tr>""")
            elif r.get("grim_pass"):
                rows.append(f"""<tr>
                    <td><span class="badge badge-pass">通过</span></td>
                    <td>{html.escape(r.get("location", ""))}</td>
                    <td><span class="raw-text">{raw}</span></td>
                    <td>{r.get("mean")}</td><td>{r.get("n")}</td>
                    <td>{r.get("scale_min")}-{r.get("scale_max")}</td>
                    <td>数学可能</td>
                </tr>""")
            else:
                rows.append(f"""<tr>
                    <td><span class="badge badge-fail">失败</span></td>
                    <td>{html.escape(r.get("location", ""))}</td>
                    <td><span class="raw-text">{raw}</span></td>
                    <td>{r.get("mean")}</td><td>{r.get("n")}</td>
                    <td>{r.get("scale_min")}-{r.get("scale_max")}</td>
                    <td>最接近合法值: {r.get("closest_possible")}</td>
                </tr>""")
        parts.append(f"""<table>
            <tr><th>结果</th><th>位置</th><th>原文</th><th>均值</th><th>N</th><th>量表</th><th>说明</th></tr>
            {''.join(rows)}
        </table>""")

    # GRIMMER failures
    grimmer_items = grim_data.get("grimmer", [])
    failures = [r for r in grimmer_items if not r.get("overall_pass", True)]
    if failures:
        parts.append('<h3>GRIMMER 测试失败</h3>')
        parts.append('<p><span class="check-type-tag">[启发式检查]</span> '
                    '内置GRIMMER为轻量级启发式，正式forensic判断建议使用 scrutiny::grimmer_map() (R)</p>')
        rows = []
        for r in failures:
            raw = html.escape(r.get("raw_text", ""))
            details = html.escape(r.get("discrepancy_details", ""))
            rows.append(f"""<tr>
                <td><span class="badge badge-fail">失败</span></td>
                <td>{html.escape(r.get("location", ""))}</td>
                <td><span class="raw-text">{raw}</span></td>
                <td>M={r.get("mean")}, SD={r.get("sd")}, N={r.get("n")}</td>
                <td>{details}</td>
            </tr>""")
        parts.append(f"""<table>
            <tr><th>结果</th><th>位置</th><th>原文</th><th>数值</th><th>详情</th></tr>
            {''.join(rows)}
        </table>""")

    # DEBIT
    debit_items = grim_data.get("debit", [])
    if debit_items:
        parts.append('<h3>DEBIT 测试结果 (二元数据)</h3>')
        rows = []
        for r in debit_items:
            status = r.get("status", "run")
            raw = html.escape(r.get("raw_text", ""))
            if status == "skipped":
                rows.append(f"""<tr>
                    <td><span class="badge badge-skip">跳过</span></td>
                    <td colspan="4">{html.escape(r.get("reason", ""))}</td>
                </tr>""")
            elif r.get("overall_pass"):
                rows.append(f"""<tr>
                    <td><span class="badge badge-pass">通过</span></td>
                    <td>{html.escape(r.get("location", ""))}</td>
                    <td><span class="raw-text">{raw}</span></td>
                    <td>p={r.get("proportion"):.4f}, SD={r.get("reported_sd")}, N={r.get("n")}</td>
                    <td>一致</td>
                </tr>""")
            else:
                rows.append(f"""<tr>
                    <td><span class="badge badge-fail">失败</span></td>
                    <td>{html.escape(r.get("location", ""))}</td>
                    <td><span class="raw-text">{raw}</span></td>
                    <td>p={r.get("proportion"):.4f}, SD={r.get("reported_sd")}, N={r.get("n")}</td>
                    <td>{html.escape(r.get("discrepancy_details", ""))}</td>
                </tr>""")
        parts.append(f"""<table>
            <tr><th>结果</th><th>位置</th><th>原文</th><th>数值</th><th>详情</th></tr>
            {''.join(rows)}
        </table>""")

    return "\n".join(parts)


def gen_cross_section(cross_data: dict) -> str:
    if not cross_data:
        return ""

    parts = []
    s = cross_data.get("summary", {})

    cards = []
    total = s.get("total_flags", 0)
    cards.append(gen_summary_card("总标记数", total, "high" if s.get("high", 0) > 0 else "pass"))
    cards.append(gen_summary_card("高风险", s.get("high", 0), "high"))
    cards.append(gen_summary_card("中风险", s.get("medium", 0), "medium"))
    cards.append(gen_summary_card("低风险", s.get("low", 0), "low"))

    parts.append('<h2>论文内部一致性审查</h2>')
    parts.append('<div class="summary-grid">' + "".join(cards) + '</div>')

    for sev in ["high", "medium", "low"]:
        flags = cross_data.get("by_severity", {}).get(sev, [])
        if not flags:
            continue

        parts.append(f'<h3>{sev_label(sev)}风险标记 ({len(flags)})</h3>')
        for flag in flags:
            locs = ", ".join(flag.get("locations", []))
            desc = html.escape(flag.get("description", ""))
            rec = html.escape(flag.get("recommendation", ""))
            va = html.escape(str(flag.get("value_a", "") or ""))
            vb = html.escape(str(flag.get("value_b", "") or ""))
            ct = flag.get("check_type", "deterministic")
            ct_label = check_type_label(ct)
            ct_badge = {"deterministic": "badge-det", "heuristic": "badge-heu", "llm_assisted": "badge-llm"}.get(ct, "badge-det")

            parts.append(f"""
            <div class="flag flag-{sev}">
                <div class="flag-title">
                    <span class="badge badge-{sev}">{sev_label(sev)}</span>
                    <span class="badge {ct_badge}">{ct_label}</span>
                    {html.escape(flag.get("flag_type", "").replace("_", " "))}
                </div>
                <div class="flag-loc">{html.escape(locs)}</div>
                <p>{desc}</p>
                {f'<p>A: <span class="raw-text">{va}</span> | B: <span class="raw-text">{vb}</span></p>' if va or vb else ''}
                <div class="flag-rec"><strong>建议:</strong> {rec}</div>
            </div>
            """)

    return "\n".join(parts)


def gen_domain_section(domain_data: dict) -> str:
    if not domain_data or not domain_data.get("flags"):
        return ""
    parts = []
    s = domain_data.get("summary", {})
    domain_labels = {"llm_agent": "大模型/智能体", "bioinformatics_ml": "生物信息学+ML"}
    label = domain_labels.get(domain_data.get("domain"), domain_data.get("domain", ""))
    parts.append(f'<h2>领域专项审查 ({html.escape(label)})</h2>')
    parts.append(f'<p><span class="check-type-tag">[需人工核实的领域完整性提示]</span> '
                 f'共{s.get("total_flags", 0)}项 (高:{s.get("high",0)} 中:{s.get("medium",0)} 低:{s.get("low",0)})</p>')
    for flag in domain_data["flags"]:
        sev = flag.get("severity", "low")
        cat = flag.get("category", "reporting_completeness")
        cat_label = "完整性" if cat == "reporting_completeness" else "统计错误"
        parts.append(f"""
        <div class="flag flag-{sev}">
            <div class="flag-title">
                <span class="badge badge-{sev}">{sev_label(sev)}</span>
                <span class="badge badge-heu">启发式</span>
                <span class="badge badge-low">{html.escape(cat_label)}</span>
                {html.escape(flag.get("flag_type", "").replace("_", " "))}
            </div>
            <p>{html.escape(flag.get("description", ""))}</p>
            <div class="flag-rec"><strong>建议:</strong> {html.escape(flag.get("recommendation", ""))}</div>
        </div>
        """)
    return "\n".join(parts)


def generate_report(grim_data: dict = None, cross_data: dict = None,
                    extracted_data: dict = None, manuscript_name: str = "",
                    domain: str = "general", domain_data: dict = None) -> str:
    domain_labels = {
        "llm_agent": "大模型/智能体论文",
        "bioinformatics_ml": "生物信息学+机器学习",
        "general": "通用学术论文",
    }
    domain_label = domain_labels.get(domain, domain)

    body_parts = []
    body_parts.append(f"""
    <h1>论文统计一致性审查报告</h1>
    <div class="meta">
        <strong>稿件:</strong> {html.escape(manuscript_name) or "未命名"}<br>
        <strong>生成时间:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M")}<br>
        <strong>审查领域:</strong> <span class="domain-tag">{html.escape(domain_label)}</span><br>
        <strong>工具链:</strong> 统计重算 + GRIM/GRIMMER/DEBIT + 跨位置一致性审查
    </div>
    """)

    # Legend
    body_parts.append("""
    <div class="card" style="margin-bottom:1rem;">
        <h4>图例说明</h4>
        <p>
        <span class="badge badge-det">数学确定</span> = 基于数学公式的确定性判断 (如p值重算、GRIM)<br>
        <span class="badge badge-heu">启发式</span> = 基于统计经验的启发式规则 (如SD/SEM混淆检测)<br>
        <span class="badge badge-llm">LLM辅助</span> = 需要大语言模型辅助的语义判断<br>
        <span class="badge badge-high">高</span> = 必须修正 | <span class="badge badge-medium">中</span> = 需核实 | <span class="badge badge-low">低</span> = 建议优化
        </p>
    </div>
    """)

    if extracted_data:
        body_parts.append(gen_nhst_section(extracted_data))

    if grim_data:
        body_parts.append(gen_grim_section(grim_data))

    if cross_data:
        body_parts.append(gen_cross_section(cross_data))

    if domain_data:
        body_parts.append(gen_domain_section(domain_data))

    body_parts.append("""
    <h2>修复建议</h2>
    <div class="card high">
        <h4>高优先级 (投稿前必须处理)</h4>
        <ul>
            <li>处理所有<span class="badge badge-high">高风险</span>标记，特别是显著性结论翻转</li>
            <li>核实GRIM失败的均值是否在整数量表上数学可能</li>
            <li>确保Abstract、Methods、Results的样本量(N)一致</li>
        </ul>
    </div>
    <div class="card medium">
        <h4>中优先级 (建议核实)</h4>
        <ul>
            <li>检查p值数值偏差 (无结论翻转但数值不匹配)</li>
            <li>核实SD/SEM标注是否正确</li>
            <li>确保正文与表格中的均值/标准差一致</li>
        </ul>
    </div>
    <div class="card low">
        <h4>低优先级 (可选优化)</h4>
        <ul>
            <li>确保所有图表在正文中被引用</li>
            <li>统一统计报告的格式规范</li>
        </ul>
    </div>
    <div class="card">
        <h4>已知局限性与误报风险</h4>
        <ul>
            <li><strong>校正p值 (Bonferroni/FDR/Holm):</strong> 校正后的p值不会与原始重算值匹配。请检查脚注中的校正声明。</li>
            <li><strong>单尾检验:</strong> 单尾p值会显示偏差。请核实文中是否有"one-tailed"/"directional"关键词。</li>
            <li><strong>连续量表 (VAS等):</strong> 连续量表数据不应进行GRIM测试，会自动跳过。</li>
            <li><strong>PDF表格提取:</strong> 复杂表格可能丢失对齐信息。优先使用DOCX输入。</li>
            <li><strong>子群分析:</strong> 子群均值与总体均值不同是合理的，不属于错误。</li>
        </ul>
    </div>
    """)

    return HTML_TEMPLATE.format(body="\n".join(body_parts))


def main():
    parser = argparse.ArgumentParser(description="生成审查报告")
    parser.add_argument("--extracted", "-e", help="提取的统计JSON")
    parser.add_argument("--grim", "-g", help="GRIM结果JSON")
    parser.add_argument("--cross", "-c", help="交叉审查JSON")
    parser.add_argument("--name", "-n", default="", help="稿件名称")
    parser.add_argument("--domain", "-d", default="general",
                        choices=["general", "llm_agent", "bioinformatics_ml"],
                        help="审查领域")
    parser.add_argument("--domain-audit", "-a", help="domain_audit.json")
    parser.add_argument("--output", "-o", default="audit_report.html", help="输出HTML")
    args = parser.parse_args()

    extracted = json.load(open(args.extracted, "r", encoding="utf-8")) if args.extracted else None
    grim_data = json.load(open(args.grim, "r", encoding="utf-8")) if args.grim else None
    cross_data = json.load(open(args.cross, "r", encoding="utf-8")) if args.cross else None
    domain_data = json.load(open(args.domain_audit, "r", encoding="utf-8")) if args.domain_audit else None

    report = generate_report(grim_data, cross_data, extracted, args.name, args.domain, domain_data)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"报告已生成: {args.output}")


if __name__ == "__main__":
    main()
