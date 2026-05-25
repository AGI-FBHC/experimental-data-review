# 审查清单 (Audit Checklist)

## 目录
1. [统计数值一致性](#1-统计数值一致性)
2. [Summary Statistics 完整性](#2-summary-statistics-完整性)
3. [论文内部一致性](#3-论文内部一致性)
4. [实验逻辑与设计](#4-实验逻辑与设计)
5. [可疑模式检测](#5-可疑模式检测)
6. [大模型/智能体论文专项检查](#6-大模型智能体论文专项检查)
7. [生物信息学+ML专项检查](#7-生物信息学ml专项检查)
8. [误报风险缓解](#8-误报风险缓解)

---

## 1. 统计数值一致性

### 1.1 P值重算与决策检查
- [ ] 提取所有NHST统计量: t, F, chi2, r, z, Q, W
- [ ] 从test statistic + df重算p值
- [ ] **优先检查决策一致性**: reported significant vs computed significant
- [ ] 决策翻转=HIGH（无论数值容差多少）
- [ ] 其次检查数值一致性（仅对p=x）

**区分处理规则**:
| 报告格式 | 检查方式 | 容差 |
|---------|---------|------|
| p = .04 | 数值对比 | ±0.01 |
| p < .05 | 检查computed p是否真<.05 | 不允许computed > .05 |
| p > .05 | 检查computed p是否真>.05 | 不允许computed < .05 |
| ns | 检查computed p >= .05 | 默认 |

### 1.2 相关系数r(df)公式
- [ ] APA格式: r(48) = 0.31中的48即为df
- [ ] 公式: t = r * sqrt(df / (1-r^2)), 双尾p from t(df)
- [ ] **不要**再减2！r(48)的48已经是df

---

## 2. Summary Statistics 完整性

### 2.1 GRIM测试 (仅整数/离散量表)
**适用条件**: Likert 1-5, 1-7, 计数数据, 整数评分
**不适用**: VAS 0-100, 反应时, 年龄, 连续生理指标 → 自动SKIP

检查: mean * N 是否为整数?
- 量表未知时 → SKIP (不是FAIL)
- 连续量表 → SKIP

### 2.2 GRIMMER测试 (启发式)
**注意**: 内置GRIMMER为轻量级启发式
**正式forensic判断**: 使用 R scrutiny::grimmer_map()

三子测试:
1. GRIM通过
2. SD variance <= 量表理论最大值
3. SD monotonicity: 均值接近边界时SD受限

### 2.3 DEBIT测试 (仅当有reported binary SD)
**无reported SD时 → SKIP** (不自动计算SD自证)
检查: reported SD是否匹配理论binary SD = sqrt(p(1-p))

---

## 3. 论文内部一致性

### 3.1 跨章节N一致性
- [ ] Abstract N vs Methods N vs Results N
- [ ] 同一实验的df-based N与explicit N对比

### 3.2 正文-表格一致性
- [ ] 均值差异 > 容差(考虑四舍五入)
- [ ] SD差异
- [ ] 样本量一致

### 3.3 SD/SEM混淆检测
**仅在以下条件flag**:
- 同一指标同时出现SD和SEM标签
- 同一指标在不同位置的spread值相差约sqrt(N)倍

**不单独根据数值大小判断**

### 3.4 图表引用完整性
- [ ] 区分declaration (caption)与citation (in-text)
- [ ] 每个figure/table至少在正文中引用一次

---

## 4. 实验逻辑与设计

### 4.1 对照组
- [ ] 对照组定义清晰
- [ ] 阳性/阴性对照适当

### 4.2 样本量追踪
- [ ] 各阶段N报告完整
- [ ] 排除标准一致应用

### 4.3 剂量-反应与时间序列
- [ ] 剂量-反应关系生理合理
- [ ] 时间趋势内部一致

---

## 5. 可疑模式检测

- [ ] 终端数字分布均匀性
- [ ] 过度精度(p值>3位小数)
- [ ] 四舍五入不一致(同一数据不同精度)
- [ ] p-hacking信号: p值聚集在0.05附近
- [ ] 选择性报告: 只报告显著结果

---

## 6. 大模型/智能体论文专项检查

### 6.1 数据与Benchmark
- [ ] 数据集版本明确
- [ ] 测试集无公开污染
- [ ] 无train-test contamination
- [ ] benchmark dev/test使用正确

### 6.2 Baseline公平性
- [ ] 相同模型规模
- [ ] 相同检索库/工具权限
- [ ] 相同budget/prompt数量
- [ ] 相同decoding参数

### 6.3 Ablation完整性
- [ ] 关键ablation是否齐全
- [ ] 无agent memory, 无tools, 无RAG, 无planning, 无reflection, 无verifier

### 6.4 多随机种子与方差
- [ ] 非单次结果
- [ ] 报告mean ± std / CI
- [ ] 不同seed/template/evaluator的方差合理

### 6.5 评估指标
- [ ] accuracy, F1, pass@k, win rate前后一致
- [ ] 表格和正文同向

### 6.6 Agent任务设置
- [ ] 工具调用次数、环境reset、最大步数一致
- [ ] 失败重试、timeout一致报告

### 6.7 LLM-as-judge
- [ ] judge model, prompt, temperature报告
- [ ] pairwise/order bias检查
- [ ] human agreement报告

### 6.8 成本与效率
- [ ] token cost/latency/API调用次数报告

### 6.9 统计显著性
- [ ] 多重比较校正
- [ ] CI或bootstrap报告

---

## 7. 生物信息学+ML专项检查

### 7.1 数据泄漏
- [ ] 同一patient/sample/cell line不同时在train/test
- [ ] 预处理在全数据上进行 → 泄漏风险

### 7.2 切分策略
- [ ] patient-wise / batch-wise / study-wise切分
- [ ] 非随机row-wise split

### 7.3 Batch Effect
- [ ] 批次、平台、测序中心报告
- [ ] 在正确范围内拟合batch correction

### 7.4 多重检验
- [ ] FDR/q-value报告

### 7.5 类别不平衡
- [ ] AUROC/AUPRC/balanced accuracy选择合理

### 7.6 外部验证
- [ ] 独立cohort验证

### 7.7 生物重复vs技术重复
- [ ] 不混淆
- [ ] N按独立样本数计算

---

## 8. 误报风险缓解

| 场景 | 操作 | 理由 |
|------|------|------|
| 校正p值(Bonferroni/FDR/Holm) | 跳过p值重算 | 校正p != 原始computed p |
| 单尾检验 | 扫描"one-tailed"/"directional" | 单尾p = 双尾p/2 |
| 非APA格式 | LLM辅助提取 | 正则可能遗漏变体 |
| PDF复杂表格 | 标记提取置信度LOW | PDF→文本丢失结构 |
| 子群分析 | 标注"子群"非"错误" | 子群均值合理不同 |
| 缺失值填补 | 检查Methods是否提及 | 填补改变summary stats |
| 稳健SE/bootstrap | 跳过SEM一致性 | 稳健SE != 经典SD/sqrt(N) |
