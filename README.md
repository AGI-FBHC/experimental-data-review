# 🔬 Experimental Data Review

> 学术手稿实验数据与统计一致性审查工具 —— 面向论文投稿前的自动化初筛辅助。

## 📖 项目简介

本项目源于对现有学术审查工具的系统性调研，目标是构建一个**面向科研人员的手稿数据审查 Agent Skill**。通过组合确定性数学检查（p值重算、GRIM/GRIMMER/DEBIT）与跨位置一致性分析，帮助作者在投稿前发现统计报告中的潜在问题。

**核心定位**：投稿前初筛辅助（pre-submission screening aid），**非统计审稿人替代品**。所有标记问题需人工复核。

---

## ✨ 核心功能

### 四步审查工作流

```
1. 提取 → 从稿件中提取 NHST 统计量、描述统计、LLM 指标
2. 完整性 → GRIM（整数/离散量表）/ GRIMMER（启发式）/ DEBIT（binary SD）
3. 交叉审查 → Abstract vs Results vs Tables vs Figure Captions 一致性
4. 报告 → 中文 HTML 报告，含风险分级和检查类型标注
```

### 支持的检查类型

| 检查项 | 说明 | 确定性 |
|--------|------|--------|
| **p 值一致性** | 根据 test statistic 和 df 重算 p 值，检测决策翻转 | 数学确定 |
| **GRIM** | 检查整数/离散量表上的均值是否数学可能 | 数学确定 |
| **GRIMMER** | 启发式 SD 一致性检查 | 启发式 |
| **DEBIT** | 检查 reported binary SD 是否匹配理论值 | 数学确定 |
| **SD/SEM 混淆** | 检测同一指标同时标注 SD 和 SEM 的错误 | 启发式 |
| **跨位置一致性** | 摘要、正文、表格、图注数值比对 | LLM 辅助 |
| **领域专项** | LLM/Agent 论文 + 生物信息学+ML 专项检查 | 规则+启发式 |

---

## 🏗️ 技术架构

### 工具链

| 组件 | 技术 | 说明 |
|------|------|------|
| 统计提取 | Python + `scipy` | 从 DOCX/PDF/文本提取 NHST 统计量 |
| 文档解析 | `python-docx`, `PyMuPDF` | Word 和 PDF 格式支持 |
| p 值重算 | `scipy.stats` | t, F, chi², r, z 分布计算 |
| 完整性检查 | 自研 Python | GRIM/GRIMMER/DEBIT 实现 |
| 报告生成 | 自研 Python | 中文 HTML 输出 |

### 推荐后端工具链（生产环境）

- **statcheck** (R/Python) — p 值重算黄金标准
- **JATSdecoder** (R) — 统计量提取（比 statcheck 更广泛）
- **tableParser** (R) — 表格数据提取
- **scrutiny** (R) — GRIM/GRIMMER/DEBIT/SPRITE 正式实现

---

## 📁 项目结构

```
experimental-data-review/
├── README.md                    # 项目说明
├── SKILL.md                     # Agent Skill 定义文档
├── REPORT.md                    # 深度调研报告（工具对比分析）
├── scripts/                     # Python 审查工具脚本
│   ├── manuscript_extractor.py  # Step 1: 统计量提取（32KB）
│   ├── grim_tests.py            # Step 2: GRIM/GRIMMER/DEBIT（10KB）
│   ├── cross_reference_audit.py # Step 3: 交叉位置一致性（17KB）
│   ├── domain_audit.py          # 领域专项检查（15KB）
│   └── report_generator.py      # Step 4: HTML 报告生成（21KB）
└── references/                  # 参考文档
    ├── checklist.md             # 完整检查清单
    ├── risk_grading.md          # 风险分级标准
    └── tool_chain.md            # 推荐工具链说明
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install scipy python-docx pdfminer.six
```

### 四步完成审查

```bash
# Step 1: 提取统计量
python scripts/manuscript_extractor.py -i manuscript.docx -o stats.json

# Step 2: 完整性检查
python scripts/grim_tests.py -i stats.json -o grim.json

# Step 3: 交叉审查
python scripts/cross_reference_audit.py -i stats.json -o cross.json

# Step 4: 生成报告
python scripts/report_generator.py \
  -e stats.json -g grim.json -c cross.json \
  -n "论文标题" --domain general -o report.html
```

### 领域选项

- `--domain general`: 通用学术论文
- `--domain llm_agent`: 大模型/智能体论文
- `--domain bioinformatics_ml`: 生物信息学+ML

---

## 📊 调研报告摘要

详见 [REPORT.md](REPORT.md)。核心结论：

> **不存在任何一个单一工具或 skill 能够完全满足所有需求**。最接近的是 **Manusights Audit**（整合 statcheck + GRIM + GRIMMER + DEBIT）和 **ReviewerZero AI**，但两者仍有重要缺口：方差齐性检查、SD/SEM 混淆检测、实验逻辑问题、多位置数据一致性。

### 工具对比矩阵

| 工具 | p值一致性 | GRIM | 表格提取 | 开源 | 可集成 |
|------|----------|------|----------|------|--------|
| statcheck | ✅ | ❌ | ❌ | ✅ | ✅ |
| JATSdecoder | ✅ | ❌ | ⚠️ | ✅ | ✅ |
| scrutiny | ⚠️ | ✅ | ❌ | ✅ | ✅ |
| Manusights Audit | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| ReviewerZero AI | ✅ | ⚠️ | ⚠️ | ❌ | ❌ |
| **本项目** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🔒 安全与伦理声明

- ✅ 所有检查基于**数学确定性**或**统计启发式**，非 AI 幻觉
- ✅ 标记问题需**人工复核**，不直接作为科研不端判断
- ✅ 未知量表类型自动 SKIP（不是 FAIL），避免误报
- ✅ 决策翻转（decision flip）标记为 HIGH 风险，优先处理

---

## 🗺️ 未来规划

- [ ] 集成 statcheck / JATSdecoder / scrutiny 作为正式后端
- [ ] 支持 LaTeX 原生解析（无需转换为文本）
- [ ] 补充材料（Supplementary Materials）一致性检查
- [ ] 图像重复检测（与 ReviewerZero AI 等效）
- [ ] 引文验证与参考文献完整性检查
- [ ] 投稿系统插件（Editorial Manager / ScholarOne 集成）

---

<p align="center">
  Made with ❤️ by <strong>XClaw Intelligent Agent</strong><br>
  <sub>通用人工智能&食品生物健康交叉研究中心（AGI&FBHC）</sub>
</p>
