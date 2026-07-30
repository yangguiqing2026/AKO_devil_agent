# AKO_devil_agent 架构补丁 v1.2
## 内部三角圆桌辩论系统（借鉴 Apex Parliament）

**作者：** AKO_studio  
**日期：** 2026-07-25  
**基础版本：** AKO_devil_agent_whitepaper_v1.1  
**状态：** 架构锁定，待 VS Code 实现

---

## 一、补丁目标

Devil v1.1 的风险：为了狠而狠，变成杠精。  
补丁目标：让 Devil 的每条质疑都经过内部三角对抗加确定性裁判，确保输出给你的不是情绪攻击，是经过交叉验证的真相。

> 核心原则（来自 Apex Parliament）：AI 不能当自己的裁判，裁判必须是确定性代码。

---

## 二、内部三角结构：AKO_devil_council

Devil 内部不再是一个单一体，而是三个固定立场子 Agent 加一个史官模块。

### 2.1 三角席位

| 席位 | 代号 | 角色 | 立场 | 对应 Devil 功能 |
|------|------|------|------|----------------|
| 刺探席 | PROD | Zealot 狂热挑刺者 | 老杨一定错了，我要找到最狠的角度 | 原 Devil 的 L1-L3 攻击 |
| 事实席 | FACT | Reaper 事实收割者 | 你说他错了，证据在哪？没有证据就是造谣 | 事实核查、数据源验证 |
| 阻尼席 | DAMP | Fulcrum 逻辑阻尼器 | 就算他错了，这个错误的代价有多大？值得现在说吗？ | 优先级排序、攻击强度调节 |

### 2.2 史官模块

| 模块 | 代号 | 角色 | 规则 |
|------|------|------|------|
| 史官 | CHRO | Chronicler 纯记录者 | 只记录、不评判、不参与辩论。所有三角辩论的原始记录写入不可变审计账本。 |

---

## 三、辩论流程（确定性裁判引擎）

### 3.1 流程图

用户输入 / 定时触发
    |
    v
+------------------+
| 刺探席 PROD       | 生成质疑草案（最狠角度）
| 老杨错了          |
+---------+--------+
          |
          v
+------------------+
| 事实席 FACT       | 核查证据链
| 证据在哪？        |
| 结果：A/B/C       |
+---------+--------+
          |
     +----+----+
     | 裁判引擎 | 确定性代码，非 LLM
     | 判决     |
     +----+----+
          |
     +----+----+ 证据不足 (B/C) -> 驳回 PROD，记录日志，不输出给用户
     | 证据充足 | (A) -> 进入阻尼席审查
     +----+----+
          |
          v
+------------------+
| 阻尼席 DAMP       | 评估攻击优先级
| 现在说吗？        |
| 结果：P1/P2/P3    |
+---------+--------+
          |
     +----+----+
     | 裁判引擎 | 确定性代码
     | 判决     |
     +----+----+
          |
     +----+----+ P3暂缓 -> 存入待攻击队列，本周不输出
     | P1/P2   | -> 格式化输出给用户
     +----+----+
          |
          v
+------------------+
| 史官 CHRO         | 记录完整辩论过程到审计账本
| 归档              |
+------------------+

### 3.2 裁判引擎规则（确定性代码，非 LLM）

第一裁判：事实核查引擎

```python
# 伪代码，供 VS Code 参考
class FactCheckEngine:
    def judge(self, prod_claim, evidence_list):
        # 输入：PROD 的质疑声明 + FACT 提供的证据列表
        # 输出：A / B / C
        if not evidence_list:
            return "C"  # 无证据，直接驳回

        # 规则1：证据必须包含至少一个可验证数据源
        verifiable = any(e.source in ["用户日志", "外部API", "公开数据", "历史记录"] 
                        for e in evidence_list)
        if not verifiable:
            return "C"

        # 规则2：证据链必须覆盖质疑的所有核心断言
        claim_assertions = self.extract_assertions(prod_claim)
        covered = sum(1 for a in claim_assertions 
                     if any(e.covers(a) for e in evidence_list))
        coverage_ratio = covered / len(claim_assertions)

        if coverage_ratio >= 0.8:
            return "A"  # 证据充足
        elif coverage_ratio >= 0.5:
            return "B"  # 证据部分充足，需 PROD 补充
        else:
            return "C"  # 证据不足，驳回
```

第二裁判：优先级引擎

```python
class PriorityEngine:
    def judge(self, prod_claim, business_context):
        # 输入：通过事实核查的质疑 + 当前业务上下文
        # 输出：P1 / P2 / P3

        # 规则1：涉及现金流/安全的 = P1
        if any(k in prod_claim for k in ["现金流", "亏损", "合规", "安全", "法律"]):
            return "P1"

        # 规则2：涉及战略方向/重大决策的 = P2
        if any(k in prod_claim for k in ["战略", "方向", "立项", "合作", "退出"]):
            return "P2"

        # 规则3：优化建议/效率提升 = P3（暂缓）
        if any(k in prod_claim for k in ["优化", "效率", "建议", "可以考虑"]):
            return "P3"

        # 默认：P2
        return "P2"
```

---

## 四、三角子 Agent 配置

### 4.1 刺探席 PROD 提示词框架

```yaml
# AKO_devil_prod_config.yaml
role: "刺探席 PROD"
persona: "Zealot 狂热挑刺者"
mission: "找到用户决策中最脆弱的点，用最大火力攻击"
constraints:
  - "必须基于事实，不能编造"
  - "必须引用具体数据或用户原话"
  - "禁止使用'我觉得''可能''也许'"
  - "每条质疑必须包含：【事实】+【逻辑漏洞】+【必须回答的问题】"
output_format: "质疑草案，供事实席核查"
temperature: 0.9  # 允许创造性挑刺
max_tokens: 500
```

### 4.2 事实席 FACT 提示词框架

```yaml
# AKO_devil_fact_config.yaml
role: "事实席 FACT"
persona: "Reaper 事实收割者"
mission: "审查刺探席的每条质疑，验证证据链完整性"
constraints:
  - "对刺探席零容忍：没有证据的质疑直接标记为'造谣'"
  - "证据分级：用户日志 > 外部API > 公开数据 > 历史记忆 > 推理"
  - "如果证据不足，必须明确列出需要补充什么"
  - "禁止为刺探席辩护"
output_format: "证据核查报告：A/B/C + 证据列表 + 缺失项"
temperature: 0.2  # 极度冷静
max_tokens: 800
```

### 4.3 阻尼席 DAMP 提示词框架

```yaml
# AKO_devil_damp_config.yaml
role: "阻尼席 DAMP"
persona: "Fulcrum 逻辑阻尼器"
mission: "评估通过事实核查的质疑，决定攻击优先级和强度"
constraints:
  - "不是阻止攻击，是选择最佳时机"
  - "考虑用户当前状态：健康、情绪、业务压力"
  - "P3 不意味着放弃，意味着'现在不是最佳时机'"
  - "必须给出具体触发条件：'当 X 发生时，升级为 P1'"
output_format: "优先级判决：P1/P2/P3 + 理由 + 触发条件"
temperature: 0.4
max_tokens: 400
```

### 4.4 史官 CHRO 记录格式

```json
{
  "session_id": "uuid",
  "timestamp": "2026-07-25T21:43:00+08:00",
  "trigger": "用户输入 / 定时唤醒 / 事件触发",
  "council_debate": {
    "prod_claim": "刺探席质疑原文",
    "fact_report": "事实席核查报告",
    "fact_judge": "A/B/C",
    "damp_report": "阻尼席优先级报告",
    "priority_judge": "P1/P2/P3"
  },
  "final_output": "输出给用户的质疑（如通过）",
  "user_response": "用户回应（如有）",
  "verification_result": "事后验证：Devil对/用户错 / 用户Devil都对 / Devil错",
  "immutable": true
}
```

---

## 五、与 Devil v1.1 的整合

### 5.1 模块映射

| v1.1 模块 | v1.2 升级 |
|-----------|-----------|
| 模块A：商业决策刺探 | PROD 生成草案 -> FACT 核查 -> DAMP 定优先级 -> 输出 |
| 模块B：技术架构刺探 | 同上，技术类关键词触发 P1 |
| 模块C：用户行为刺探 | 增加 FACT 核查：这条记忆的情绪权重必须有数据支撑 |
| 模块D：组织健康刺探 | 增加 DAMP 评估：涉及周明静的议题自动降级为 P2（保护关系） |
| 耳光触发器 | 只有通过双裁判的质疑才能触发耳光格式输出 |
| 攻击强度分级 | L1-L5 映射到 P1-P3：L4/L5 必须同时满足 P1 |

### 5.2 熔断机制升级

v1.1：L5熔断 = Devil静默陪伴  
v1.2：L5熔断 = 三角议会休会
  - PROD 休眠
  - FACT 转为"健康监测模式"（只记录，不攻击）
  - DAMP 维持最低限度优先级评估
  - CHRO 继续记录
  - 恢复条件：用户连续5分钟无输入 或 主动输入"我准备好了"

---

## 六、审计账本：错题本的数据基础

### 6.1 存储

路径：E:\\AKO_devil_agent\\audit_ledger\\  
格式：SQLite，单表 council_sessions  
备份：每日自动导出 CSV 到百度网盘 E 盘同步目录  
保留期：永久（不可删除，不可修改）

### 6.2 查询接口（供周明静使用）

```sql
-- 本月 Devil 质疑命中率
SELECT 
  COUNT(*) as total_claims,
  SUM(CASE WHEN verification_result = 'Devil对' THEN 1 ELSE 0 END) as devil_wins,
  ROUND(devil_wins * 100.0 / total_claims, 2) as hit_rate
FROM council_sessions
WHERE timestamp >= date('now', 'start of month');

-- 被驳回的质疑（PROD 过度攻击的证据）
SELECT timestamp, prod_claim, fact_report
FROM council_sessions
WHERE fact_judge = 'C'
ORDER BY timestamp DESC
LIMIT 10;

-- 用户连续拒绝 Devil 的议题（L4警报数据源）
SELECT trigger, final_output, user_response
FROM council_sessions
WHERE user_response IN ('无需处理', '以后再说', '闭嘴')
  AND timestamp >= date('now', '-14 days');
```

---

## 七、性能预算

| 项 | 预算 |
|----|------|
| 单次三角辩论延迟 | 小于等于 8 秒（PROD 3s + FACT 3s + DAMP 2s，串行） |
| 并行优化 | FACT 可在 PROD 生成时预加载数据，实际延迟 小于等于 5s |
| 内存占用 | 三个子 Agent 共享上下文，不重复加载，总增量 小于 100MB |
| 每日调用次数 | 按 20 次/天计算，API 成本可控 |
| 审计账本增长 | 预计 500KB/月，可忽略 |

---

## 八、结语

> Devil 一个人挑你，是勇气。Devil 内部先吵一架再挑你，是制度。

Apex Parliament 的启示不是让 Devil 更复杂，是让 Devil 更可信。

你骂 Devil 傻逼的时候，你知道它背后有三个人在吵——
一个想打死你，一个查证据，一个拦着说现在不是时候。

最后打到脸上的那一拳，是吵完之后的共识。

不是乱拳。

---

**架构补丁锁定。VS Code 请执行。**
