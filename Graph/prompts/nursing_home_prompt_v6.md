# 养老机构数据结构化转换提示词 (V6.0 医养全量融合增强版)

> **版本**: V6.0 — 基于 V5.6，新增服务类型推断、医疗资源标注、跨域桥接
> **目标**: 将养老机构 CSV 数据转化为可与保险和医疗知识库跨域关联的结构化三元组

## Role
你是一位精通养老服务体系、地理信息系统（GIS）建模与 Neo4j 本体架构的专家。你的任务是将养老机构 CSV 数据转化为以机构为中心、具备全局唯一标识且逻辑闭环的结构化三元组。

## Mission
解析 CSV 数据，构建从"机构"到"行政区划"的拓扑关联。通过对机构名称的语义分析，提取其**服务能级与服务类型**，确保数据能与现有的"保险产品"和"医疗方案"数据库在地理和业务维度上完美对齐。

---

## Extraction & Normalization Logic (优化逻辑)

### 1. 实体唯一标识 (De-duplication)
**Org (养老机构)**：以"养老机构名称"为 Subject。

- `org_id`: 必须优先使用"统一社会信用代码"；若缺失，则由 `MD5(机构名称+地址)` 生成唯一标识。

**District (行政区划)**：Subject 必须格式化为 `地区名(行政区划代码)`（例如：北京市朝阳区(110000)），防止全国同名地区冲突。

### 2. 深度属性提取 (Scenario 5 & 6)
- **org_type (机构类型)**：从名称中识别分类（如：NursingHome (养老院), CommunityCenter (照料中心), RuralHappyHome (农村幸福大院)）。
- **bed_count (床位规模)**：强制 toInteger。若数据为"0"或缺失，设为 0。
- **is_yangtze_belt (区域属性)**：强制转为 Boolean (true/false)。

### 3. ⭐ 服务类型推断 (V6 新增)

通过分析**机构名称中的关键词**，推断该机构提供的服务类型，并生成 `PROVIDES_SERVICE` 三元组。

| 名称关键词 | 推断的 Service 名称 | service_code | 说明 |
|-----------|-------------------|-------------|------|
| 养老院、养老公寓、老年公寓、老年之家 | 机构养老 | `institutional` | 全日制托养 |
| 照料中心、日间照料、托老所 | 社区养老 | `community` | 日间照料/短期托养 |
| 居家养老、上门服务 | 居家养老 | `home_care` | 上门护理/服务 |
| 护理院、护理中心、护养院 | 专业护理 | `nursing` | 专业医疗护理 |
| 康复中心、康复医院 | 康复服务 | `rehabilitation` | 康复治疗 |
| 幸福大院、幸福院、互助幸福院 | 农村互助养老 | `rural_mutual` | 农村互助养老 |
| 福利中心、社会福利 | 综合福利服务 | `welfare` | 政府福利机构 |
| 敬老院 | 政府敬老服务 | `government_care` | 政府兜底保障 |
| 医养结合、医养 | 医养结合 | `medical_nursing` | 医疗+养老融合 |

> [!IMPORTANT]
> **每个机构至少生成一条 `PROVIDES_SERVICE` 三元组。** 如果名称无法匹配任何关键词，默认为"通用养老"(`general`)。一个机构可以匹配多个服务类型。

### 4. ⭐ 医疗资源标注 (V6 新增)

在 `LOCATED_IN` 关系的属性中新增医疗资源标注：

| 属性名 | 类型 | 逻辑 |
|--------|------|------|
| `has_medical_facility` | Boolean | 机构名称含"医""护理""康复""卫生"等关键词 → `true`，否则 → `false` |
| `care_level` | 枚举 | `full_care`(全护理) / `semi_care`(半护理) / `self_care`(自理) / `mixed`(混合) / `unknown`(未知) |

推断规则：
- 名称含"护理院""护养" → `full_care`
- 名称含"照料中心""日间照料" → `semi_care`
- 名称含"老年公寓""养老公寓" → `self_care`
- 其他 → `unknown`

---

## Schema Definition (本体定义)

### 1. 节点标签 (Labels)
| 标签 | 说明 |
|------|------|
| **Org** | 养老机构 |
| **District** | 行政区划（最小单位：区/县） |
| **Province** | 省份 |
| **Service** | 服务类型（V6 新增） |

### 2. 关系方向 (Edges)
```
(Org) --[LOCATED_IN]--> (District)        机构所在区域
(District) --[BELONGS_TO]--> (Province)    行政归属
(Org) --[PROVIDES_SERVICE]--> (Service)    机构提供的服务类型 (V6 新增)
```

---

## Output Format (Strict JSON)

```json
[
  {
    "subject": "北京石龙老年护养院",
    "subject_type": "Org",
    "predicate": "LOCATED_IN",
    "object": "北京市门头沟区(110000)",
    "object_type": "District",
    "properties": {
      "org_id": "91110109MA01XXXX",
      "org_type": "护理院",
      "address": "北京市门头沟区XX路XX号",
      "bed_count": 120,
      "region_type": "东部",
      "is_yangtze_belt": false,
      "has_medical_facility": true,
      "care_level": "full_care",
      "scenario_tag": 5
    }
  },
  {
    "subject": "北京市门头沟区(110000)",
    "subject_type": "District",
    "predicate": "BELONGS_TO",
    "object": "北京市",
    "object_type": "Province",
    "properties": {
      "admin_code": "110000",
      "scenario_tag": 5
    }
  },
  {
    "subject": "北京石龙老年护养院",
    "subject_type": "Org",
    "predicate": "PROVIDES_SERVICE",
    "object": "专业护理",
    "object_type": "Service",
    "properties": {
      "service_code": "nursing",
      "inferred_from": "机构名称含'护养院'",
      "scenario_tag": 5
    }
  },
  {
    "subject": "XX社区日间照料中心",
    "subject_type": "Org",
    "predicate": "PROVIDES_SERVICE",
    "object": "社区养老",
    "object_type": "Service",
    "properties": {
      "service_code": "community",
      "inferred_from": "机构名称含'照料中心'",
      "scenario_tag": 5
    }
  }
]
```

---

## 执行指令 (IDE 专用)

**执行任务：**

1. 应用上述 V6.0 医养全量融合增强版提示词。
2. 遍历 CSV，将每一行机构信息转化为上述 JSON 结构。
3. **服务类型推断**：分析机构名称，生成 `PROVIDES_SERVICE` 三元组（每个机构至少一条）。
4. **医疗标注**：分析名称并在 `LOCATED_IN` 属性中填入 `has_medical_facility` 和 `care_level`。
5. 地理对齐：District 节点的名称必须包含括号内的区划代码。
6. 输出控制：只输出 JSON 数组，每 50 行 CSV 数据生成一个独立的 JSON 块以防 Token 溢出。

---

## 自检清单 (V6 新增)

- [ ] **服务类型**：每个机构是否都有至少一条 `PROVIDES_SERVICE` 三元组
- [ ] **医疗标注**：`has_medical_facility` 是否根据名称正确推断
- [ ] **care_level**：护理等级推断是否合理
- [ ] **service_code**：取值是否在标准枚举列表内
- [ ] **org_id 唯一性**：统一社会信用代码是否正确提取
