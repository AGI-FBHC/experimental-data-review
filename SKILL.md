---
name: manuscript-experimental-data-audit
description: Audit experimental data and statistical consistency in scientific manuscripts, theses, preprints, or journal submissions (.docx, .tex, .pdf). Use when reviewing academic papers to verify reported statistics are internally consistent, mathematically possible, and free from forensic anomalies. Covers p-value recomputation with decision-flip detection, GRIM/GRIMMER/DEBIT tests (with proper scale-type gating), cross-section consistency (Abstract vs Results vs Tables vs Figure Captions), SD/SEM confusion detection, and domain-specific checks for LLM/Agent papers and bioinformatics+ML papers. Generates a Chinese-localized HTML audit report with severity-graded flags and check-type annotations. Triggers on requests involving manuscript review, statistical audit, data validation, paper consistency checking, experimental results verification, or reported statistics integrity.
---

# Manuscript Experimental Data Audit

论文统计一致性审查工具。组合确定性检查（p值重算、GRIM/GRIMMER/DEBIT）与跨位置一致性分析，生成结构化HTML审查报告。

## 定位声明

**本工具是投稿前初筛辅助（pre-submission screening aid），而非统计审稿人替代品。** 所有标记的问题均需人工复核，不应直接作为科研不端判断依据。

## 工作流概览

```
1. 提取 -> 从稿件中提取NHST统计量、描述统计、比例、LLM指标
2. 完整性 -> GRIM（仅整数/离散量表）/ GRIMMER（启发式）/ DEBIT（仅报告了binary SD时）
3. 交叉审查 -> Abstract vs Results vs Tables vs Figure Captions 一致性
4. 报告 -> 中文HTML报告，含风险分级和检查类型标注
```

## 输入格式

- **优先**: `.docx` (Word), `.pdf` (PDF), 粘贴纯文本
- **扩展**: `.tex` (LaTeX) -> 先转换为文本
- **辅助**: `.html`, `.xml` (JATS)

## Step 1: 提取统计量

```bash
python scripts/manuscript_extractor.py --input manuscript.docx --output stats.json
python scripts/manuscript_extractor.py --text "Results: t(28)=2.14, p=.04..." --output stats.json
```

提取内容:
- **NHST**: t, F, chi2, r, z, Q, W — 含test statistic, df, p值表达式
- **描述统计**: mean ± SD/SEM + n，自动推断量表类型（integer/continuous/unknown）
- **比例**: 百分比和计数（**不**自动计算SD）
- **LLM指标**: pass@k, win rate, success rate, exact match

**依赖安装**: `pip install scipy`（必须，用于p值重算）; `pip install python-docx`（DOCX）; `pip install pdfminer.six` 或 `PyMuPDF`（PDF）

### p值一致性检查规则

**优先级: 决策一致性 > 数值一致性**

| 报告格式 | 检查方式 |
|---------|---------|
| p = .04 | 数值对比 ±0.01 |
| p < .05 | 检查computed p是否真 < .05 |
| p > .05 | 检查computed p是否真 > .05 |
| ns | 检查computed p >= .05 |

**决策翻转**（reported significant 但 computed nonsignificant，或反之）= **HIGH风险**，不受数值容差保护。

### r(df) p值公式

APA格式r(48) = 0.31中的48即为df。使用: `t = r * sqrt(df / (1-r^2))`，双尾p from t(df)。**不要**再减2。

## Step 2: 完整性检查 (GRIM / GRIMMER / DEBIT)

```bash
python scripts/grim_tests.py --input stats.json --output grim.json
```

### GRIM — 仅整数/离散量表

- **适用**: Likert 1-5, 1-7, 计数数据, 整数评分
- **不适用**: VAS 0-100, 反应时, 年龄, 连续生理指标
- **未知量表**: 自动SKIP（不是FAIL）
- 通过上下文关键词自动推断量表类型（"Likert", "score", "count", "continuous", "VAS", "age"）

### GRIMMER — 启发式检查

**注意**: 内置GRIMMER为轻量级启发式，**不等价**于R scrutiny包的正式实现。
- 正式forensic判断: `scrutiny::grimmer_map()` (R)

### DEBIT — 仅当有reported binary SD

- **无reported SD时自动SKIP**（不自己算SD再自证）
- 检查: reported SD是否匹配理论binary SD = sqrt(p(1-p))

## Step 3: 交叉审查

```bash
python scripts/cross_reference_audit.py --input stats.json --text "full_text.txt" --output cross.json
```

检查项:
- **N一致性**: Abstract vs Methods vs Results
- **均值/SD一致性**: 正文 vs 表格（考虑四舍五入容差）
- **SD/SEM混淆**: 仅当同一指标同时有SD和SEM标签，或spread值相差约sqrt(N)倍
- **图表引用**: 区分caption declaration与in-text citation
- **决策翻转**: p值显著性结论跨位置不一致

## Step 4: 生成报告

```bash
python scripts/report_generator.py \
  --extracted stats.json \
  --grim grim.json \
  --cross cross.json \
  --name "论文标题" \
  --domain llm_agent \
  --output audit_report.html
```

`--domain` 选项:
- `llm_agent`: 大模型/智能体论文（含benchmark、baseline、ablation、seed variance检查）
- `bioinformatics_ml`: 生物信息学+ML（含data leakage、patient-wise split、batch effect检查）
- `general`: 通用学术论文

报告包含:
- 图例说明（数学确定 / 启发式 / LLM辅助 / 高中低风险）
- NHST结果表（一致性、检查类型、决策翻转标记）
- GRIM/GRIMMER/DEBIT结果（通过/失败/跳过）
- 跨位置一致性标记（含具体建议和修复优先级）
- 已知局限性与误报风险说明

## 检查清单速查

详见 `references/checklist.md`，核心要点:

1. **p值一致性**: 决策翻转 > 数值偏差; p</p=/p>/ns分别处理
2. **GRIM/GRIMMER/DEBIT**: 整数量表才GRIM; 有reported SD才DEBIT; 未知量表SKIP
3. **交叉位置**: Abstract↔Results↔Tables↔Captions数值一致
4. **实验逻辑**: 对照组、N追踪、剂量-反应合理
5. **可疑模式**: 终端数字、p-hacking信号、选择性报告
6. **LLM/Agent专项**: benchmark污染、baseline公平性、seed variance、judge bias
7. **Bioinfo专项**: data leakage、patient-wise split、batch effect、外部验证

## 完整命令

```bash
# 四步完成审查
python scripts/manuscript_extractor.py -i manuscript.docx -o stats.json
python scripts/grim_tests.py -i stats.json -o grim.json
python scripts/cross_reference_audit.py -i stats.json -o cross.json
python scripts/report_generator.py -e stats.json -g grim.json -c cross.json -o report.html
```

在浏览器中打开 `report.html` 查看完整审查结果。
