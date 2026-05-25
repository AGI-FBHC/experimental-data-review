
# 学术手稿实验数据审查工具与 Agent Skill 深度调研报告

## 核心结论摘要

**不存在任何一个单一工具或 skill 能够完全满足所有需求**。最接近的是 **Manusights Audit**（整合 statcheck + GRIM + GRIMMER + DEBIT）和 **ReviewerZero AI**（综合统计检查 + 图像检查 + 引文验证），但两者仍有重要缺口：方差齐性检查、SD/SEM 混淆检测、实验逻辑问题（剂量-反应、时间序列、对照组完整性）以及多位置数据一致性（摘要 vs 正文 vs 表格 vs 图注）。

**推荐方案**：以 **manuscript-experimental-data-audit** 为新 skill，以 `statcheck` + `JATSdecoder`/`tableParser` + `scrutiny` 为后端工具链，构建一个面向论文稿件 reported results 的统计一致性审查 skill。

---

## 一、已发现的候选工具与技能分类

### A 类：现有 Agent / Claude Code / MCP Skill

| # | Skill/工具名称 | 链接 | 类型 | 支持输入 | 匹配度 |
|---|--------------|------|------|---------|--------|
| 1 | **Scientific Manuscript Review** (Claude Code Skill) | https://mcpmarket.com/tools/skills/scientific-manuscript-review | Claude Code Skill | DOCX, TEX, PDF, MD | 中 |
| 2 | **Scientific Peer Review Evaluation** (Claude Code Skill) | https://mcpmarket.com/tools/skills/scientific-peer-review-evaluation-2 | Claude Code Skill | DOCX, TEX, PDF, MD | 中 |
| 3 | **manuscript-audit-skill.md** (dougwyu) | https://github.com/dougwyu/claude-zotero-skills | Claude Code Skill | 配合 Zotero 使用 | 低 |
| 4 | **AIPOCH Peer Review Skill** | https://github.com/aipoch/medical-research-skills | Agent Skill (OpenClaw/Claude) | DOCX, TEX, PDF | 中 |
| 5 | **K-Dense Peer Review Skill** | https://www.aipoch.com/blog/peer-review-agent-skill-comparison | Agent Skill | DOCX, TEX, PDF | 中 |
| 6 | **Paper Sprint Review** (AIPOCH) | https://www.aipoch.com/blog/top-aipoch-agent-skills-for-researchers | Agent Skill | DOCX, TEX, MD, PDF | 中 |

### B 类：成熟工具（可直接作为 Skill 后端）

| # | 工具名称 | 链接 | 类型 | 支持输入 | 核心功能 | 匹配度 |
|---|---------|------|------|---------|---------|--------|
| 1 | **statcheck** (R/Python/Web) | https://statcheck.io, https://github.com/MicheleNuijten/statcheck | R/Python/Web App | PDF, HTML, DOCX, text | 从正文中提取 NHST 统计量，根据 test statistic 和 df 重算 p-value，检查一致性 | **高** |
| 2 | **JATSdecoder** (R) | https://github.com/ingmarboeschen/JATSdecoder, https://www.get-stats.app | R package / Web | DOCX, PDF, HTML, XML, CERMXML | 从全文中提取所有统计结果（get.stats），重算 p-value，支持 20+ 种统计量 | **高** |
| 3 | **tableParser** (R) | https://github.com/ingmarboeschen/tableParser, https://www.get-stats.app | R package / Web | DOCX, HTML, XML, PDF (有限) | 从表格中提取统计数据并转换为可检查的格式（table2stats） | **高** |
| 4 | **get-stats.app** | https://www.get-stats.app | Web App | DOCX, PDF, HTML, XML | JATSdecoder + tableParser 的网页接口，支持单文件上传检查 | **高** |
| 5 | **Manusights Audit** | https://manusights.com/tools/stats-audit | Web App | 粘贴文本（APA/LaTeX/表格） | LLM 提取 + statcheck + GRIM + GRIMMER + DEBIT 四合一手动检查 | **高** |
| 6 | **scrutiny** (R) | https://lhdjung.github.io/scrutiny/ | R package | 数据框/R 对象 | GRIM, GRIMMER, SPRITE, debit, 视觉级联测试, 数字分析 | **高** |
| 7 | **rsprite2** (R) | https://lukaswallrich.github.io/rsprite2/ | R package | R 对象 | SPRITE：从 summary statistics 反推可能的数据分布 | **中** |
| 8 | **statcheck_python** | https://github.com/hplisiecki/statcheck_python | Python package | PDF, HTML, text | statcheck 的 Python 移植版 | **中** |
| 9 | **CheckMyManuscript** | https://checkmymanuscript.com | Web App | DOCX, TEX, PDF | 80+ 自动检查：图表编号、引用、参考文献、摘要结构 | **中** |
| 10 | **ReviewerZero AI** | https://www.reviewerzero.ai | Web App / SaaS | PDF | 统计检查、图像重复检测、引文验证、作者验证、AI 文本检测 | **高** |

### C 类：论文与方法（暂不能直接使用）

| # | 方法名称 | 论文/链接 | 说明 |
|---|---------|----------|------|
| 1 | **Carlisle Test** | Carlisle, 2012, 2017 | 基于 Stouffer 方法检测临床试验中的异常分布 |
| 2 | **TIVA** (Test of Insufficient Variance) | Schimmack, 2015 | 检测 p-value 分布方差是否过低（暗示 p-hacking） |
| 3 | **TIDES** | Hussey et al., 2024 | 检测 summary statistics 在已知边界量表上的一致性 |
| 4 | **ANCHOR** | Hussey | 检查整样本与子群统计量的一致性 |
| 5 | **PORT** | Hussey | 检测相关性表格的一致性 |
| 6 | **Ellipse of Insignificance** | David Robert Grimes | 检验二分结果试验的稳健性 |

---

## 二、详细功能对比表

### 2.1 核心统计一致性检查能力

| 工具/技能 | p-value 与 test statistic/df 一致性 | mean/SD/SEM/n 一致性 | 方差/CV/SD-SEM 混淆检查 | GRIM/GRIMMER/SPRITE/DEBIT | 实验逻辑问题（组别/对照/剂量/时间） | 图表-正文一致性 |
|-----------|-----------------------------------|---------------------|------------------------|--------------------------|-----------------------------------|---------------|
| statcheck | ✅ 核心功能 | ❌ | ❌ | ❌ | ❌ | ❌ |
| JATSdecoder | ✅ 核心功能（比 statcheck 更广泛） | ⚠️ 提取但非专门检查 | ❌ | ❌ | ❌ | ⚠️ 提取表格和正文 |
| tableParser | ⚠️ 通过 table2stats | ⚠️ 提取表格数据 | ❌ | ❌ | ❌ | ✅ 表格-正文 |
| scrutiny | ⚠️ 部分支持 | ✅ GRIM/GRIMMER/DEBIT | ⚠️ 通过 GRIMMER | ✅ GRIM/GRIMMER/DEBIT/SPRITE | ❌ | ❌ |
| Manusights Audit | ✅ statcheck 等效 | ✅ GRIM + GRIMMER | ⚠️ GRIMMER | ✅ GRIM+GRIMMER+DEBIT | ❌ | ❌ |
| ReviewerZero AI | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ |
| CheckMyManuscript | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ 图表编号/引用 |
| SciScore | ❌ | ❌ | ❌ | ❌ | ⚠️ 报告完整性 | ❌ |
| StatReviewer | ⚠️ 自动测试 | ⚠️ | ⚠️ | ❌ | ⚠️ | ❌ |

### 2.2 输入格式与数据提取能力

| 工具/技能 | DOCX | TEX | PDF | JATS XML | 正文统计提取 | 表格数据提取 | 图注提取 | 补充材料 |
|-----------|------|-----|-----|----------|-------------|-------------|---------|---------|
| statcheck | ✅ | ❌ | ✅ | ❌ | ✅ (APA 风格, ~60% 检出率) | ❌ (明确不支持) | ❌ | ❌ |
| JATSdecoder | ✅ | ❌ | ⚠️ (需 CERMINE 转换) | ✅ (原生) | ✅ (比 statcheck 更广泛) | ⚠️ (需 tableParser) | ✅ | ⚠️ |
| tableParser | ✅ | ❌ | ⚠️ (有限) | ✅ | ⚠️ (通过 table2stats) | ✅ (核心功能) | ✅ | ❌ |
| get-stats.app | ✅ | ❌ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ❌ |
| statcheck_python | ⚠️ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Manusights Audit | ❌ (仅粘贴文本) | ⚠️ (粘贴 LaTeX) | ❌ | ❌ | ✅ (LLM 提取) | ⚠️ (需粘贴) | ⚠️ | ❌ |
| ReviewerZero AI | ❌ | ❌ | ✅ | ❌ | ✅ (AI 提取) | ⚠️ | ⚠️ | ❌ |
| CheckMyManuscript | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ (仅检查编号) | ✅ (检查编号) | ❌ |

### 2.3 报告输出与集成能力

| 工具/技能 | 结构化审查报告 | 安装/调用方式 | 是否可作为 Skill 后端 | 文档质量 |
|-----------|--------------|--------------|---------------------|---------|
| statcheck | ✅ (R data.frame/CSV) | `install.packages("statcheck")` / Python `pip install statcheck` | ✅ 极佳后端 | 高 |
| JATSdecoder | ✅ (R list/data.frame) | `install.packages("JATSdecoder")` | ✅ 极佳后端 | 高 |
| tableParser | ✅ (R data.frame) | `install.packages("tableParser")` / GitHub | ✅ 极佳后端 | 高 |
| scrutiny | ✅ (R data.frame + 可视化) | `install.packages("scrutiny")` | ✅ 极佳后端 | 高 |
| Manusights Audit | ✅ (网页报告 + 分享 URL) | Web 使用 | ⚠️ 仅粘贴文本 | 中 |
| ReviewerZero AI | ✅ (PDF/Word/PPT 导出) | Web SaaS | ❌ 闭源 | 中 |
| CheckMyManuscript | ✅ (邮件报告) | Web 使用 | ❌ | 中 |
| SciScore | ✅ (评分报告) | 集成到投稿系统 | ❌ 闭源 | 中 |
| StatReviewer | ✅ (编辑系统报告) | 集成到 Editorial Manager | ❌ 闭源 | 中 |

---

## 三、关键发现与缺口分析

### 3.1 不存在"完全满足需求"的单一工具

经过对 15+ 工具和 6+ 个 agent skill 的调研，**没有任何一个单一工具或 skill 能够同时满足**：

1. **多格式输入**：同时支持 DOCX / TEX / PDF / JATS XML
2. **全量数据提取**：正文统计结果 + 表格数据 + 图注数据 + 补充材料
3. **统计一致性全检查**：p-value 一致性 + mean/SD/SEM/n 一致性 + 方差合理性
4. ** forensic 检测**：GRIM + GRIMMER + SPRITE + DEBIT
5. **实验逻辑检查**：组别/对照/剂量/时间/单位一致性
6. **跨位置一致性**：摘要 vs 正文 vs 表格 vs 图注
7. **结构化报告输出**：可解释的审查报告

### 3.2 最接近的现有方案

#### 方案一：Manusights Audit（粘贴文本模式）
- **优势**：在一个网页中整合了 statcheck + GRIM + GRIMMER + DEBIT；使用 LLM（Claude Haiku）提取统计量，比正则表达式更灵活
- **劣势**：仅支持粘贴文本，不直接处理 DOCX/TEX/PDF 文件；不支持表格内统计量自动提取；不支持方差齐性检查；不支持实验逻辑问题
- **匹配度**：中高

#### 方案二：get-stats.app（JATSdecoder + tableParser）
- **优势**：支持 DOCX/PDF/HTML/XML；同时提取正文统计量和表格统计量；可重算 p-value 并检查一致性
- **劣势**：不直接支持 TEX；不执行 GRIM/GRIMMER/DEBIT 检查；不检查实验逻辑；不检查图表编号/引用一致性
- **匹配度**：高

#### 方案三：ReviewerZero AI
- **优势**：综合平台，统计检查 + 图像重复 + 引文验证 + 作者验证；声称比 statcheck 多发现 43% 统计报告
- **劣势**：闭源 SaaS；不直接处理 TEX/DOCX（仅 PDF）；缺乏 GRIM/GRIMMER 等 forensic 检查；缺乏实验逻辑检查
- **匹配度**：中高

### 3.3 可作为 Skill 后端的工具链

| 需求维度 | 推荐后端工具 | 说明 |
|---------|-------------|------|
| PDF → 文本转换 | `pdftotext` (Xpdf) / `pdftools` (R) | statcheck 和 JATSdecoder 都依赖 |
| 正文统计提取 | `JATSdecoder::get.stats()` | 检出率高于 statcheck，支持更多统计量 |
| 表格统计提取 | `tableParser::table2stats()` | 从 DOCX/HTML/XML 表格中提取统计量 |
| p-value 一致性 | `statcheck` / `JATSdecoder::pCheck()` | 核心功能，成熟可靠 |
| GRIM/GRIMMER/DEBIT | `scrutiny` (R) | 最完整的 R 实现 |
| SPRITE | `rsprite2` (R) / `scrutiny` | 从 summary stats 反推数据分布 |
| 图表编号/引用 | `CheckMyManuscript` API (如可用) | 或自定义规则 |
| LLM 提取增强 | Claude Haiku / GPT-4 | 对非标准格式的补充提取 |

---

## 四、建议：新建 manuscript-experimental-data-audit Skill

### 4.1 Skill 基本信息

| 属性 | 建议内容 |
|------|---------|
| **Skill 名称** | `manuscript-experimental-data-audit` |
| **备选名称** | `scientific-manuscript-statistical-audit` / `reported-results-consistency-review` |
| **适用场景** | 学术论文投稿前自检、同行评审辅助、编辑部技术审查、元分析数据提取验证 |
| **目标用户** | 研究者、审稿人、期刊编辑、元分析研究者、科研诚信官员 |

### 4.2 输入文件类型

- **优先支持**：`.docx` (Word), `.tex` (LaTeX), `.pdf` (PDF manuscript)
- **扩展支持**：`.html`, `.xml` (JATS XML), `.cermxml`
- **辅助输入**：`.bib` (参考文献), 补充材料文件

### 4.3 处理流程（Pipeline）

```
┌─────────────────────────────────────────────────────────────────┐
│                    Input: DOCX / TEX / PDF                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   1. Document Conversion   │
              │   → 统一转换为结构化文本    │
              │   → 识别章节（摘要/方法/    │
              │      结果/讨论/图注/表注）  │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   2. Multi-Source Extraction │
              │   a. 正文统计提取            │
              │      → JATSdecoder::get.stats│
              │   b. 表格统计提取            │
              │      → tableParser::table2stats│
              │   c. 图注/表注提取           │
              │      → 自定义规则 + LLM      │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   3. Consistency Checks      │
              │   a. p-value 重算与比较      │
              │      → statcheck + pCheck    │
              │   b. GRIM / GRIMMER / DEBIT  │
              │      → scrutiny              │
              │   c. SPRITE 分布重建         │
              │      → rsprite2 / scrutiny   │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   4. Cross-Reference Audit   │
              │   a. 摘要 vs 正文一致性      │
              │   b. 正文 vs 表格一致性      │
              │   c. 正文 vs 图注一致性      │
              │   d. 图表编号/引用完整性     │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   5. Experimental Logic      │
              │   a. 样本量一致性检查        │
              │   b. 组别/对照定义完整性     │
              │   c. 单位/时间/剂量一致性    │
              │   d. 异常值/不可能值标记     │
              └─────────────┬──────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   6. Report Generation       │
              │   → 结构化 HTML/PDF 报告     │
              │   → 风险分级（高/中/低）     │
              │   → 人工复核建议             │
              └────────────────────────────┘
```

### 4.4 检查清单（Checklist）

#### 第一层：统计数值一致性
- [ ] **p-value 重算**：test statistic + df → recompute p，与 reported p 比较
- [ ] **显著性翻转检测**：reported significant vs computed non-significant（或反之）
- [ ] **缺失信息标记**：统计报告缺少 df、test statistic 或 p-value
- [ ] **Effect size 合理性**：reported effect size 与 test statistic/df/p 是否逻辑一致

#### 第二层：Summary Statistics 合理性
- [ ] **GRIM 测试**：整数型量表数据的 mean 与 sample size 是否数学可能
- [ ] **GRIMMER 测试**：mean + SD + sample size 是否数学可能
- [ ] **DEBIT 测试**：二元数据的 proportion + SD + N 是否数学可能
- [ ] **SPRITE 重建**：从 summary stats 判断是否存在可能的底层数据分布
- [ ] **SD/SEM 混淆检测**：检查 mean ± SD 和 mean ± SEM 的标注是否正确
- [ ] **方差范围检查**：SD/方差是否异常过大或过小

#### 第三层：论文内部一致性
- [ ] **摘要-正文一致性**：同一统计量在摘要和正文中是否一致
- [ ] **正文-表格一致性**：正文描述的数值与表格中数值是否一致
- [ ] **正文-图注一致性**：正文与图注/表注的描述是否一致
- [ ] **样本量一致性**：Methods 报告的 n 与 Results/Table/Figure caption 中的 n 是否一致
- [ ] **图表编号完整性**：所有图表是否被引用，编号是否连续

#### 第四层：实验逻辑
- [ ] **对照组完整性**：对照组是否定义清晰，是否缺失
- [ ] **剂量-反应关系**：报告的剂量-反应是否生理/物理合理
- [ ] **时间序列一致性**：时间趋势是否与实验叙述矛盾
- [ ] **单位一致性**：同一变量在不同位置的单位是否一致
- [ ] **技术重复 vs 生物重复**：是否混淆 technical replicate 和 biological replicate
- [ ] **数据重复使用**：同一数据是否在不同图表中以不同解释重复出现

#### 第五层：可疑模式
- [ ] **终端数字异常**：过多重复的小数位或终端数字
- [ ] **过度整齐的数据**：数值过于"完美"（如所有 p-value 恰好为 0.05）
- [ ] **不可能精度**：小数位数超过仪器或实验设计精度
- [ ] **四舍五入不一致**：同一数据在不同位置四舍五入不一致
- [ ] **p-hacking 信号**：选择性报告、只报告显著结果

### 4.5 输出报告格式

```yaml
---
manuscript_id: "auto-generated"
filename: "example_manuscript.docx"
date: "2026-01-15T10:30:00Z"
summary:
  total_checks: 156
  flags_high: 3
  flags_medium: 12
  flags_low: 28
  passed: 113
  flag_rate: "22.4%"
---

# 1. 统计数值一致性

## 1.1 p-value 一致性
| Location | Raw | Test Type | df | Reported p | Computed p | Error? | Decision Error? |
|----------|-----|-----------|-----|-----------|-----------|--------|-----------------|
| Results, para 3 | "t(28)=2.14, p=.04" | t | 28 | 0.04 | 0.042 | No | No |
| Table 2, row 5 | "F(2,65)=3.02, p<.05" | F | 2,65 | <0.05 | 0.056 | **Yes** | **Yes** |

## 1.2 Summary Statistics 合理性
| Location | Test | Mean/Proportion | SD | N | Scale | GRIM? | GRIMMER? |
|----------|------|----------------|-----|---|-------|-------|----------|
| Results, para 2 | GRIM | 3.51 | - | 30 | 1-5 | **FAIL** | - |
| Table 1, row 3 | GRIMMER | 2.20 | 1.33 | 20 | 1-5 | Pass | **FAIL** |

# 2. 论文内部一致性

## 2.1 摘要-正文
- **Flag (Medium)**: Abstract reports "n=45" but Results section reports "n=43" for Experiment 1

## 2.2 正文-表格
- **Flag (High)**: Results state "M=2.45, SD=0.89" but Table 2 reports "M=2.45, SD=1.12" for Group A

# 3. 实验逻辑

## 3.1 样本量一致性
- **Flag (Medium)**: Methods states "N=120" but Table 3 shows total N=115

## 3.2 对照组
- **Pass**: Control group clearly defined in Methods and consistent across all tables

# 4. 建议与风险分级

## 高风险（需立即修正）
1. **Table 2, F(2,65)=3.02**：p-value 重算为 0.056，原报告为 p<.05，显著性结论可能翻转
2. **Results para 2, Mean=3.51**：GRIM 测试失败，整数量表上 N=30 时不可能得到均值 3.51

## 中风险（需核实）
1. Abstract 与 Results 样本量不一致（45 vs 43）
2. Table 2 Group A 的 SD 与正文描述不一致（0.89 vs 1.12）

## 低风险（建议优化）
1. 图 4 未被正文引用
2. Table 5 的 p-value 缺少 exact value（仅报告 "p<.05"）
```

### 4.6 高风险问题分级标准

| 级别 | 标准 | 示例 | 建议操作 |
|------|------|------|---------|
| **🔴 高** | 统计结论可能翻转；数学上不可能的值；关键数据矛盾 | p-value 重算后显著性改变；GRIM 失败；正文与表格的 mean 相差>10% | 必须修正后投稿 |
| **🟡 中** | 数据不一致但可能不影响结论；信息缺失但不影响理解 | 样本量小差异；SD 四舍五入不一致；摘要与正文数值微差 | 需作者核实并说明 |
| **🟢 低** | 报告不规范；可能影响可读性但不影响科学性 | 图表未引用；p-value 未报告 exact value；格式不统一 | 建议优化 |

### 4.7 误报风险与人工复核建议

| 风险类型 | 说明 | 缓解策略 |
|---------|------|---------|
| **校正后 p-value** | Bonferroni/FDR 校正后的 p 与原始 test statistic 不一致 | 检测 footnote 中的校正声明，自动跳过此类检查 |
| **APA 格式变异** | 非标准报告格式导致提取失败 | 使用 LLM 辅助提取作为补充 |
| **PDF 转换错误** | PDF 转文本时格式丢失 | 优先使用 DOCX/XML 输入；对 PDF 结果标注置信度 |
| **方向性检验** | 单尾检验被误判为不一致 | 扫描文本中的 "one-tailed"/"directional" 关键词 |
| **四舍五入边界** | 报告值恰好在四舍五入边界 |  scrutiny 和 statcheck 都内置 rounding tolerance |
| **分组 vs 总体** | 子群统计量与总体不一致是合理的 | 标注上下文，由人工判断 |

---

## 五、最终建议

### 5.1 是否值得新建 Skill？

**值得**。理由：
1. 没有任何现有 skill（包括 AIPOCH 的 550+ skill、Claude Code marketplace skill）专门覆盖"论文稿件实验数据统计一致性审查"这一完整需求
2. 后端工具链成熟（statcheck、JATSdecoder、tableParser、scrutiny 都是经过验证的工具）
3. 组合方案比单一工具更有价值：整合提取 + 检查 + 跨位置比对 + 报告生成
4. 有明确的学术和出版市场需求（期刊编辑、审稿人、元分析研究者）

### 5.2 推荐的最小可行产品（MVP）

**第一阶段**：
- 输入：DOCX / PDF / 粘贴文本
- 后端：`JATSdecoder` (提取) + `statcheck` (p-value 检查) + `scrutiny` (GRIM/GRIMMER)
- 输出：结构化文本报告

**第二阶段**：
- 增加 TEX 支持
- 增加 `tableParser` (表格统计提取)
- 增加跨位置一致性检查（摘要 vs 正文 vs 表格 vs 图注）

**第三阶段**：
- 增加实验逻辑检查（样本量、对照组、单位一致性）
- 增加可疑模式检测（终端数字、过度整齐、p-hacking 信号）
- 输出可视化报告（HTML/PDF）

### 5.3 与现有工具的关系

| 现有工具 | 在本 Skill 中的角色 |
|---------|-------------------|
| statcheck | p-value 重算核心引擎 |
| JATSdecoder | 正文统计提取（比 statcheck 更广） |
| tableParser | 表格统计提取 |
| scrutiny | GRIM/GRIMMER/DEBIT/SPRITE 测试 |
| rsprite2 | SPRITE 分布重建 |
| Manusights Audit | 参考其 LLM + 确定性检查的架构设计 |
| ReviewerZero AI | 参考其综合报告格式和风险分级 |

---

## 参考文献

1. Nuijten, M. B., et al. (2016). The prevalence of statistical reporting errors in psychology. *Behavior Research Methods*, 48(4), 1205-1226.
2. Brown, N. J. L., & Heathers, J. A. J. (2017). The GRIM test. *Social Psychological and Personality Science*, 8(4), 363-369.
3. Anaya, J. (2017). The GRIMMER test. *PeerJ Preprints*, 5:e2400v1.
4. Heathers, J. A. J., et al. (2018). SPRITE. https://github.com/JordanAnaya/sprtite
5. Böschen, I. (2021). Evaluation of JATSdecoder. *Scientific Reports*, 11.
6. Böschen, I. (2026). Extraction of tabulated statistical results with tableParser. arXiv:2603.19756v1.
7. Nuijten, M. B., & Epskamp, S. (2024). statcheck: Extract statistics from articles and recompute p-values. R package version 1.5.0.
8. Jung, L. (2024). scrutiny: Error detection in science. R package. https://lhdjung.github.io/scrutiny/
9. Wallrich, L. (2024). rsprite2: Identify Distributions that Match Reported Sample Parameters. R package.
10. Carlisle, J. B. (2017). Data fabrication and other reasons for non-random sampling in 5087 randomised, controlled trials in anaesthetic and general medical journals. *Anaesthesia*, 72(8), 944-956.
