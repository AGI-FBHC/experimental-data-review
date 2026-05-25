# 风险分级标准与误报缓解

## 严重级别

### 🔴 高 — 投稿前必须处理

| 问题 | 检测方法 | 示例 |
|------|---------|------|
| 显著性结论翻转 | p值重算 vs 报告 | 报告p<.05但重算p=.056 |
| GRIM失败（整数量表） | grim_test() | Likert量表mean=3.51, N=30（不可能）|
| 均值差异>5% | 跨位置比较 | 正文M=2.45，表格M=2.89 |
| Feature selection leakage | 关键词扫描 | 在全数据上选特征再split |
| 多重检验未校正 | 关键词扫描 | 差异表达/GWAS未报告FDR |

### 🟡 中 — 需作者核实

| 问题 | 检测方法 | 示例 |
|------|---------|------|
| p值数值偏差（无翻转） | statcheck重算 | 报告p=.04，重算p=.042 |
| 样本量不一致 | N提取比较 | Methods N=120，Results N=115 |
| SD/SEM标签冲突 | 同一指标SD≠SEM且差~√N | 表格标SD=0.5，正文标SEM=0.5 |
| Random split（生物数据） | 关键词扫描 | 生物医学数据用random split |
| 无外部验证 | 关键词扫描 | 仅CV无独立cohort |
| 未报告seed/variance | 关键词扫描 | LLM论文无multi-seed结果 |

### 🟢 低 — 建议优化

| 问题 | 检测方法 | 示例 |
|------|---------|------|
| 图表未引用 | caption vs citation | Figure 3未在正文引用 |
| 四舍五入不一致 | 数值比较 | "2.45"正文 vs "2.4"表格 |
| Cost/latency未报告 | 关键词扫描 | Agent论文无token cost |
| Ablation不完整 | 关键词扫描 | 缺少关键ablation |

## 误报风险矩阵

| 场景 | 标记类型 | 误报概率 | 缓解措施 |
|------|---------|---------|---------|
| 校正p值(Bonferroni/FDR) | p_mismatch | **高(~80%)** | 扫描脚注"corrected"/"adjusted" |
| 单尾检验 | p_mismatch | **高(~70%)** | 扫描"one-tailed"/"directional" |
| 连续量表GRIM | grim_skip | 零 | 自动SKIP，不标记 |
| 子群分析 | mean_mismatch | **高(~50%)** | 上下文标注"子群" |
| PDF表格 | extraction_error | **高(~60%)** | 标记置信度LOW |
| VAS/连续量表 | grim_skip | 零 | 自动SKIP |
| 无reported binary SD | debit_skip | 零 | 自动SKIP |
| mean超出scale范围 | grimmer_skip | 低 | 自动SKIP+提示scale推断错误 |

## SD/SEM混淆检测规则（当前版本）

**仅在以下条件触发flag：**
1. 同一指标同时出现SD和SEM两种标签
2. 同一指标在不同位置的spread值相差约√N倍

**不单独根据数值大小判断。**

## 检查类型标注

| 类型 | 说明 | 示例 |
|------|------|------|
| **数学确定** | 基于数学公式的确定性判断 | p值重算、GRIM |
| **启发式** | 基于统计经验的关键词/规则 | SD/SEM混淆、presence/absence |
| **LLM辅助** | 需大语言模型语义判断 | 非标准格式提取 |
