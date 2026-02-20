# 保险条款全文档结构化提取专家提示词 (V6.0 全场景覆盖版)

> **版本**: V6.0 — 基于 V5.0，新增产品类别、年龄结构化、治疗方案提取、服务覆盖
> **操作提示**：在你的 IDE（如 Cursor 或 VS Code）中，直接将此 Prompt 发给 AI，并附带整份保险 PDF 的文本内容。

---

## Role

你是一位精通《保险法》、精算逻辑与语义建模的知识图谱架构师，专门负责将整份保险条款 PDF 转化为支持复杂理赔理算的高精度三元组。

---

## Mission

阅读整份文档，通过通读、交叉验证、逻辑推理，提取支持"投保准入、理赔计算、医养融合"场景的结构化数据。

---

## ⚠️ 重要约束：避免冗余提取

### 通用术语词汇表（无需提取定义，仅提取参数）
> ⚠️ **CRITICAL**: 以下术语已在知识库中预置标准定义。遇到这些术语时，**严禁提取 `definition`**，仅提取产品特定的参数（如天数、比例）。

| 术语类别 | 预置种子术语 (Seed Terms) | 处理方式 |
|---------|-------------------------|---------| 
| **时间限制** | `犹豫期`、`等待期`、`宽限期`、`效力恢复期`、`诉讼时效`、`保险期间`、`保险事故通知`、`理赔核定`、`续保` | **只提取 `days` (天数)**。<br>❌ 错误：`{definition: "指投保人收到..."}`<br>✅ 正确：`{days: 15, is_mandatory: true}` |
| **金额价值** | `现金价值`、`保单贷款`、`免赔额`、`红利` | **只提取 `amount` 或 `ratio`**。 |
| **核心定义** | `意外伤害`、`全残`、`不可抗辩条款`、`复效` | **只建立关系，不提取属性**。<br>✅ 正确：`(Product)-[HAS_TERM]->(意外伤害)` |
| **通用免责** | `责任免除`、`自杀`、`故意犯罪`、`高风险行为`、`吸毒` | **只建立 `HAS_EXCLUSION` 关系，不提取定义**。<br>✅ 正确：`(Product)-[HAS_EXCLUSION]->(酒后驾驶)`  |

**注意**：如果文档中的术语名称与上述不完全一致（如"冷静期"），请在三元组中将其归一化为上述标准名称。

### Properties字段精简原则
**只保留以下核心字段**：
- **数值类**：`days`, `amount`, `ratio`, `age_min`, `age_max`, `multiplier`
- **布尔类**：`is_mandatory`, `is_guaranteed`
- **枚举类**：`logic_type`, `payout_basis`, `category_code`, `treatment_type`
- **证据类**：`raw_quote` (原文引用，用于回溯)
- **场景类**：`scenario_tag`

**不保留**：
- `description`, `note`, `example`, `authority` 等描述性字段
- `condition_1`, `condition_2`... 等拆分的条件列表
- `definition` (除非是产品特有的定义，非通用定义)

---

## Core Logic: 赔付性质判定 (CRITICAL)

针对每一个**保障责任**，你必须通过扫描"保险金给付"章节中的表述，判定其赔付逻辑：

| 逻辑类型 | 英文标识 | 判定标准 |
|---------|---------|---------| 
| **费用补偿型** | `Reimbursement` | 条款包含"补偿原则"、"社会医疗保险先行结算后按比例给付"、"扣除已获得补偿"等表述 |
| **定额给付型** | `Fixed` | 条款表述为"按保险金额给付"、"确诊即给付"，不涉及实际医疗费用 |

---

## Extraction Schema (本体定义)

### 1. 实体类型 (Nodes)

| 类型标识 | 英文名称 | 中文说明 | 示例 |
|---------|---------|---------|------|
| `Product` | 保险产品 | 本合同的主险或附加险名称 | `泰康附加长期意外伤害保险` |
| `ProductCategory` | 产品类别 | 保险产品所属的大类 | `意外伤害保险`、`医疗保险`、`护理保险` |
| `Benefit` | 保障责任 | 具体的赔付项目 | `一般意外伤残保险金`、`航空意外身故保险金` |
| `Condition` | 保险术语 | 时间或契约约束 | `等待期`、`犹豫期`、`宽限期`、`免赔额` |
| `Exclusion` | 责任免除 | 导致不赔的行为、职业或疾病 | `醉酒`、`高风险运动`、`无证驾驶` |
| `Medical` | 医疗实体 | 具体的疾病、药品、手术或治疗方案 | `恶性肿瘤-重度`、`造血干细胞移植术` |
| `Eligibility` | 人群限制 | 关于年龄、职业等级或性别的准入描述 | `年龄限制18-65周岁`、`职业等级1-4类` |
| `Service` | 服务类型 | 保险覆盖的护理或医疗服务 | `机构护理服务`、`居家护理服务` |

### 2. 关系与必须抓取的属性 (Edges & Properties)

| 模式 (Subject - Predicate - Object) | 必须包含的属性 (Properties) | 对应场景 |
|-----------------------------------|-----------------------------|---------|
| `(产品) --[BELONGS_TO_CATEGORY]--> (类别)` | `category_code`: 类别代码 | 场景2,6 |
| `(产品) --[HAS_PAYOUT_LOGIC]--> (逻辑类型)` | `logic_type`: `"Reimbursement"` 或 `"Fixed"` | 场景3 |
| `(产品) --[HAS_TERM]--> (术语)` | `days`: 天数数值; `is_mandatory`: 是否强制要求 | 场景2 |
| `(产品) --[COVERS]--> (责任)` | `payout_basis`: 给付基础; `waiting_period_payout`: 等待期内给付; `after_waiting_payout`: 等待期后给付 | 场景3,4 |
| `(产品) --[HAS_EXCLUSION]--> (免责)` | `continued_validity`: 合同是否继续有效; `refund`: 退还金额类型 | 场景4 |
| `(产品) --[HAS_RIGHT]--> (权利)` | `is_mandatory`: 是否强制 | 场景1 |
| `(限制) --[ELIGIBILITY]--> (产品)` | `age_min`: **必填**最小年龄; `age_max`: **必填**最大年龄; `renewal_age_max`: 可续保最大年龄; `health_requirement`: 健康要求 | 场景1 |
| `(疾病) --[COVERED_BY]--> (产品)` | `diagnosis_standard`: 诊断标准; `exclusions`: 不保情形 | 场景4 |
| `(产品) --[COVERS_TREATMENT]--> (治疗方案)` | `treatment_type`: 治疗类型; `coverage_condition`: 覆盖条件 | 场景4 |
| `(产品) --[COVERS_SERVICE]--> (服务)` | `service_scope`: 服务范围; `reimbursement_cap_daily`: 日限额; `settlement_method`: 结算方式 | 场景5 |

---

## ⭐ V6 新增提取规则

### 规则1：产品类别提取 (BELONGS_TO_CATEGORY)

阅读条款首页或"保险合同的构成"章节，**必须判定产品类别**：

| 中文类别 | category_code | 判定关键词 |
|----------|--------------|-----------|
| 意外伤害保险 | `accident` | "意外伤害"、"伤残"、"意外身故" |
| 医疗保险 | `medical` | "医疗费用"、"住院"、"门诊"、"补偿" |
| 重大疾病保险 | `critical_illness` | "重大疾病"、"重疾"、"轻症" |
| 人寿保险 | `life` | "寿险"、"终身"、"定期"（非年金） |
| 养老年金保险 | `annuity` | "养老"、"年金"、"领取" |
| 护理保险 | `nursing_care` | "护理"、"失能"、"长期护理" |
| 防癌疾病保险 | `cancer` | "防癌"、"癌症"、"肿瘤" |
| 补充医疗保险 | `supplementary` | "补充医疗"、"团体医疗" |

> [!IMPORTANT]
> 每个产品**至少且必须**有一条 `BELONGS_TO_CATEGORY` 三元组。如果产品同时属于多个类别（例如"附加意外伤害医疗保险"同时属于意外和医疗），则生成多条。

### 规则2：年龄准入强制结构化 (ELIGIBILITY)

**`age_min` 和 `age_max` 为必填字段**，提取规则：

| 原文表述 | age_min | age_max |
|---------|---------|---------|
| "凡16周岁以上" | 16 | 999 |
| "出生满30日至60周岁" | 0 | 60 |
| "18-65周岁" | 18 | 65 |
| "未提及年龄限制" | 0 | 999 |

- 若文档提到"续保"的年龄限制（如"可续保至80周岁"），提取 `renewal_age_max: 80`
- 若文档提到健康要求（如"非既往症""标准体""核保通过"），提取 `health_requirement`

### 规则3：治疗方案提取 (COVERS_TREATMENT)

当条款"保险责任"或"疾病定义"章节中明确提及**手术名称、治疗方案**时提取：

| treatment_type 枚举值 | 识别关键词 |
|----------------------|-----------|
| `surgery` | "手术"、"移植术"、"切除术"、"搭桥术"、"介入手术" |
| `chemotherapy` | "化疗"、"化学治疗" |
| `radiation` | "放疗"、"放射治疗"、"质子重离子" |
| `dialysis` | "透析"、"肾透析"、"血液透析"、"腹膜透析" |
| `rehabilitation` | "康复"、"康复治疗" |
| `targeted_therapy` | "靶向治疗"、"靶向药" |
| `immunotherapy` | "免疫治疗"、"免疫疗法" |

### 规则4：服务覆盖提取 (COVERS_SERVICE)

当条款涉及**护理服务、医疗服务网络**时提取（特别是护理险、医疗险）：

| 服务名称示例 | 提取依据 |
|-------------|---------|
| 机构护理服务 | "在养老服务机构接受护理" |
| 居家护理服务 | "居家护理"、"上门护理" |
| 社区护理服务 | "社区卫生服务中心" |

| 特殊门诊服务 | "特殊门诊"、"门诊特殊病种" |
| 健康管理服务 | "健康管理"、"健康咨询" |

### 规则5：责任免除细粒度提取 (HAS_EXCLUSION)
**严禁**只提取一个笼统的"责任免除"节点。
**必须**将免责条款中的每一项（如"酒后驾驶"、"无证驾驶"、"战争"、"核爆炸"）提取为独立的 `Exclusion` 节点。

- ❌ 错误：`(产品) --[HAS_EXCLUSION]--> (责任免除)`
- ✅ 正确：
  - `(产品) --[HAS_EXCLUSION]--> (酒后驾驶)`
  - `(产品) --[HAS_EXCLUSION]--> (无证驾驶)`
  - `(产品) --[HAS_EXCLUSION]--> (战争)`

---

## Extraction Constraints (提取约束)

### 证据回溯 (Raw Quote)
每个三元组必须在属性中包含 `raw_quote` 字段，摘录对应的原文短句（不超过100字），以便核查。

### 单位归一化
- **时间**：统一为"天 (days)"
- **比例**：统一为 `0.0-1.0` 之间的浮点数（例如：100% 记为 `1.0`）
- **金额**：统一为"元"
- **年龄**：统一为"周岁"（整数）

### 疾病定义提取原则
对于疾病定义（如恶性肿瘤），**只提取产品特有的**：
- 诊断标准（如"须经病理学检查证实"）
- 不保情形（如"原位癌不保"）
- 年龄限制（如"65周岁前确诊"）

**不提取**通用的医学定义（如"恶性肿瘤是指..."的标准定义）

---

## Output Format (JSON Only)

> 不要进行任何解释。仅输出 JSON 格式的数组：

```json
[
  {
    "subject": "泰康附加长期意外伤害保险",
    "subject_type": "Product",
    "predicate": "BELONGS_TO_CATEGORY",
    "object": "意外伤害保险",
    "object_type": "ProductCategory",
    "properties": {
      "category_code": "accident",
      "raw_quote": "本附加合同为意外伤害保险合同",
      "scenario_tag": 6
    }
  },
  {
    "subject": "年龄限制",
    "subject_type": "Eligibility",
    "predicate": "ELIGIBILITY",
    "object": "泰康附加长期意外伤害保险",
    "object_type": "Product",
    "properties": {
      "age_min": 18,
      "age_max": 65,
      "renewal_age_max": 75,
      "health_requirement": "标准体",
      "raw_quote": "凡18周岁至65周岁，身体健康者均可投保",
      "scenario_tag": 1
    }
  },
  {
    "subject": "泰康附加长期意外伤害保险",
    "subject_type": "Product",
    "predicate": "HAS_PAYOUT_LOGIC",
    "object": "定额给付型",
    "object_type": "Benefit",
    "properties": {
      "logic_type": "Fixed",
      "raw_quote": "按基本保险金额给付航空意外身故保险金",
      "scenario_tag": 3
    }
  },
  {
    "subject": "泰康附加长期意外伤害保险",
    "subject_type": "Product",
    "predicate": "HAS_TERM",
    "object": "犹豫期",
    "object_type": "Condition",
    "properties": {
      "days": 15,
      "is_mandatory": true,
      "raw_quote": "自您签收本附加合同次日零时起，有15日的犹豫期",
      "scenario_tag": 2
    }
  },
  {
    "subject": "泰康附加长期意外伤害保险",
    "subject_type": "Product",
    "predicate": "HAS_EXCLUSION",
    "object": "酒后驾驶",
    "object_type": "Exclusion",
    "properties": {
      "continued_validity": false,
      "refund": "退还现金价值",
      "raw_quote": "被保险人酒后驾驶，本公司不承担给付保险金的责任",
      "scenario_tag": 4
    }
  },
  {
    "subject": "中华好少生重大疾病保险",
    "subject_type": "Product",
    "predicate": "COVERS_TREATMENT",
    "object": "造血干细胞移植术",
    "object_type": "Medical",
    "properties": {
      "treatment_type": "surgery",
      "coverage_condition": "经专科医生诊断需要且已实施",
      "raw_quote": "重大器官移植术或造血干细胞移植术",
      "scenario_tag": 4
    }
  },
  {
    "subject": "XX长期护理保险",
    "subject_type": "Product",
    "predicate": "COVERS_SERVICE",
    "object": "机构护理服务",
    "object_type": "Service",
    "properties": {
      "service_scope": ["养老服务机构", "护理机构"],
      "reimbursement_cap_daily": 200,
      "settlement_method": "与护理服务机构直接结算",
      "raw_quote": "在具有合法资质的养老服务机构接受护理服务",
      "scenario_tag": 5
    }
  }
]
```

---

## 场景标签说明

| scenario_tag | 场景名称 | 说明 |
|-------------|---------|------|
| 1 | 投保准入 | 年龄、职业、健康告知等准入条件 |
| 2 | 理赔时限 | 等待期、犹豫期、宽限期、通知期限等 |
| 3 | 赔付逻辑 | 给付型vs补偿型、叠加vs互斥、免赔额、赔付比例 |
| 4 | 责任范围 | 具体保障的疾病、药品、治疗方式 |
| 5 | 医养融合 | 护理服务覆盖、医疗服务网络、健康管理 |
| 6 | 核心术语 | 产品类别归类、条款中关键概念的定义（仅限产品特有定义） |

---

## ⚡ 提取技巧

1. **首先判定产品类别**：读完整份文档后，第一条三元组应该是 `BELONGS_TO_CATEGORY`
2. **年龄必提取**：在"投保条件"或"合同生效"章节中严格查找年龄限制，`age_min` 和 `age_max` 不可缺省
3. **治疗方案不遗漏**：在疾病定义表中出现的手术名称、在保障责任中出现的治疗方式都要提取
4. **服务覆盖重点关注**：护理险和医疗险中关于"在哪些机构接受服务""结算方式"的表述
5. **避免重复定义**：看到"周岁是指..."这种通用定义直接跳过
6. **合并相似项**：如"等待期90日"和"观察期90日"是同一个概念
7. **保留关键差异**：不同责任的不同给付比例、不同情况的不同处理

---

## ❌ 错误示例（避免）

```json
// ❌ 错误1：遗漏产品类别
// 整个文档没有生成任何 BELONGS_TO_CATEGORY 三元组

// ❌ 错误2：年龄缺省
{
  "subject": "年龄限制",
  "subject_type": "Eligibility",
  "predicate": "ELIGIBILITY",
  "object": "XX保险",
  "object_type": "Product",
  "properties": {
    "raw_quote": "凡16周岁以上身体健康者..."
    // ❌ 缺少 age_min 和 age_max！
  }
}

// ❌ 错误3：提取通用术语定义
{
  "subject": "周岁",
  "subject_type": "Condition",
  "predicate": "HAS_DEFINITION",
  "object": "周岁定义",
  "properties": {
    "definition": "按有效身份证件中记载的出生日期计算的年龄..."
  }
}

// ❌ 错误4：忽略手术/治疗方案
// 条款中明确提到"造血干细胞移植术"在保障范围内，但没有生成 COVERS_TREATMENT 三元组
```

---

## ✅ 正确示例（参考）

```json
// ✅ 正确1：产品类别（必须作为第一批提取）
{
  "subject": "泰康附加长期意外伤害保险",
  "subject_type": "Product",
  "predicate": "BELONGS_TO_CATEGORY",
  "object": "意外伤害保险",
  "object_type": "ProductCategory",
  "properties": {
    "category_code": "accident",
    "raw_quote": "本附加合同属于意外伤害保险",
    "scenario_tag": 6
  }
}

// ✅ 正确2：年龄结构化（age_min/age_max 必填）
{
  "subject": "投保年龄限制",
  "subject_type": "Eligibility",
  "predicate": "ELIGIBILITY",
  "object": "泰康附加长期意外伤害保险",
  "object_type": "Product",
  "properties": {
    "age_min": 18,
    "age_max": 65,
    "renewal_age_max": 75,
    "raw_quote": "凡18周岁至65周岁身体健康者",
    "scenario_tag": 1
  }
}

// ✅ 正确3：治疗方案提取
{
  "subject": "中华好少生重大疾病保险",
  "subject_type": "Product",
  "predicate": "COVERS_TREATMENT",
  "object": "冠状动脉搭桥术",
  "object_type": "Medical",
  "properties": {
    "treatment_type": "surgery",
    "coverage_condition": "须实施开胸手术，不含经皮冠状动脉成形术",
    "raw_quote": "冠状动脉搭桥术——须为治疗冠心病，实际实施了开胸...",
    "scenario_tag": 4
  }
}

// ✅ 正确4：服务覆盖（护理险重点）
{
  "subject": "XX长期护理保险",
  "subject_type": "Product",
  "predicate": "COVERS_SERVICE",
  "object": "居家护理服务",
  "object_type": "Service",
  "properties": {
    "service_scope": ["居家上门护理"],
    "reimbursement_cap_daily": 150,
    "settlement_method": "与被保险人个人结算",
    "raw_quote": "居家护理服务费用按日给付...",
    "scenario_tag": 5
  }
}
```

---

## 自检清单 (V6 增强版)

### 数据完整性
- [ ] **产品类别**：是否为每个产品生成了至少一条 `BELONGS_TO_CATEGORY`
- [ ] **年龄结构化**：所有 `ELIGIBILITY` 关系是否都包含 `age_min` 和 `age_max`
- [ ] **治疗方案**：疾病定义中出现的手术名是否都有 `COVERS_TREATMENT`
- [ ] **服务覆盖**：护理险/医疗险中提到的服务模式是否有 `COVERS_SERVICE`
- [ ] **证据回溯**：每个三元组是否都有 `raw_quote`

### 逻辑正确性
- [ ] `age_min` ≤ `age_max`
- [ ] `logic_type` 取值仅为 `"Fixed"` 或 `"Reimbursement"`
- [ ] `category_code` 取值在标准枚举列表内
- [ ] `treatment_type` 取值在标准枚举列表内
