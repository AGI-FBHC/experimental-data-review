"""
HTML Report Generator
Generates Chinese HTML review reports with severity-graded flags.
"""

from typing import List, Dict, Any
from datetime import datetime


def generate_html_report(
    stats: List[Dict[str, Any]],
    grim_results: List[Dict[str, Any]],
    cross_results: List[Dict[str, Any]],
    domain_results: List[Dict[str, Any]]
) -> str:
    """Generate a Chinese HTML review report."""
    
    # Count issues by severity
    errors = [r for r in grim_results + cross_results if r.get('is_error')]
    warnings = [r for r in domain_results if not r.get('is_error')]
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>实验数据审查报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .summary-card .number {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .summary-card .label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .section h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .issue {{
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .issue.error {{
            background: #fff2f0;
            border-left: 4px solid #ff4d4f;
        }}
        .issue.warning {{
            background: #fffbe6;
            border-left: 4px solid #faad14;
        }}
        .issue.success {{
            background: #f6ffed;
            border-left: 4px solid #52c41a;
        }}
        .issue-icon {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            flex-shrink: 0;
        }}
        .issue.error .issue-icon {{ background: #ff4d4f; color: white; }}
        .issue.warning .issue-icon {{ background: #faad14; color: white; }}
        .issue.success .issue-icon {{ background: #52c41a; color: white; }}
        .issue-content {{ flex: 1; }}
        .issue-title {{ font-weight: 600; margin-bottom: 4px; }}
        .issue-desc {{ color: #666; font-size: 13px; }}
        .issue-line {{ color: #999; font-size: 12px; margin-top: 4px; }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .stats-table th, .stats-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }}
        .stats-table th {{
            background: #fafafa;
            font-weight: 600;
            color: #666;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 实验数据审查报告</h1>
            <div class="meta">
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                审查引擎: XClaw Experimental Data Review v1.0
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{len(stats)}</div>
                <div class="label">提取统计量</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: #ff4d4f;">{len(errors)}</div>
                <div class="label">发现错误</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: #faad14;">{len(warnings)}</div>
                <div class="label">警告提示</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: #52c41a;">{len(stats) - len(errors)}</div>
                <div class="label">通过检查</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔍 GRIM / GRIMMER / DEBIT 检查</h2>
            {_render_issues(grim_results)}
        </div>
        
        <div class="section">
            <h2>🔗 交叉位置一致性</h2>
            {_render_issues(cross_results)}
        </div>
        
        <div class="section">
            <h2>🎯 领域专项检查</h2>
            {_render_issues(domain_results)}
        </div>
        
        <div class="section">
            <h2>📈 提取统计量详情</h2>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>数值</th>
                        <th>原始文本</th>
                        <th>行号</th>
                    </tr>
                </thead>
                <tbody>
                    {_render_stats_table(stats)}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>本报告由 XClaw 实验数据审查系统自动生成</p>
            <p>仅供参考，所有标记的问题均需人工复核</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


def _render_issues(results: List[Dict[str, Any]]) -> str:
    """Render issue items as HTML."""
    if not results:
        return '<div class="issue success"><div class="issue-icon">✓</div><div class="issue-content"><div class="issue-title">未发现问题</div><div class="issue-desc">所有检查项均通过</div></div></div>'
    
    html = ""
    for r in results:
        if r.get('is_error'):
            icon = "✕"
            css_class = "error"
            title = r.get('test', r.get('type', 'Error'))
        elif r.get('severity') == 'warning':
            icon = "!"
            css_class = "warning"
            title = r.get('type', 'Warning')
        else:
            icon = "✓"
            css_class = "success"
            title = r.get('test', r.get('type', 'OK'))
        
        html += f"""
        <div class="issue {css_class}">
            <div class="issue-icon">{icon}</div>
            <div class="issue-content">
                <div class="issue-title">{title}</div>
                <div class="issue-desc">{r.get('message', '')}</div>
                {f'<div class="issue-line">行 {r.get("line", "N/A")}</div>' if 'line' in r else ''}
            </div>
        </div>"""
    
    return html


def _render_stats_table(stats: List[Dict[str, Any]]) -> str:
    """Render statistics table rows."""
    if not stats:
        return '<tr><td colspan="4" style="text-align:center;color:#999;">未提取到统计量</td></tr>'
    
    html = ""
    for s in stats[:50]:  # Limit to 50 entries
        value_str = str(s.get('value', ''))
        if 'sd' in s:
            value_str += f" ± {s['sd']}"
        elif 'sem' in s:
            value_str += f" (SEM={s['sem']})"
        
        html += f"""
        <tr>
            <td>{s.get('type', 'unknown')}</td>
            <td>{value_str}</td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;">{s.get('raw', '')}</td>
            <td>{s.get('line', 'N/A')}</td>
        </tr>"""
    
    if len(stats) > 50:
        html += f'<tr><td colspan="4" style="text-align:center;color:#999;">... 还有 {len(stats) - 50} 条记录 ...</td></tr>'
    
    return html


if __name__ == '__main__':
    # Test report generation
    test_stats = [
        {'type': 'p_value', 'value': 0.05, 'raw': 'p = 0.05', 'line': 10},
        {'type': 'mean', 'value': 3.45, 'sd': 1.23, 'raw': '3.45 ± 1.23', 'line': 15},
    ]
    test_grim = [
        {'is_error': False, 'test': 'GRIM', 'message': 'Mean consistent', 'line': 15},
        {'is_error': True, 'test': 'GRIMMER', 'message': 'SD too large for scale', 'line': 15},
    ]
    test_cross = [
        {'is_error': False, 'type': 'duplicate', 'message': 'Duplicate p-value found'},
    ]
    test_domain = [
        {'is_error': False, 'type': 'benchmark', 'message': 'MMLU mentioned', 'severity': 'warning'},
    ]
    
    report = generate_html_report(test_stats, test_grim, test_cross, test_domain)
    with open('/tmp/test_report.html', 'w', encoding='utf-8') as f:
        f.write(report)
    print("Report generated: /tmp/test_report.html")
