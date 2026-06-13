---
name: lessons-record
description: Use when a durable lesson should be recorded after bug fixes, rollbacks, tool misjudgments, workflow errors, failed validation, GitNexus mismatch, or multi-agent context loss.
---

# Lessons 记录 Skill

当需要记录长期经验教训时，使用本 Skill。

## 默认记录结构

Trellis 项目默认采用分层 lessons 结构：

- `.trellis/spec/lessons.md`：必读短入口，只保存高优先级摘要、读取协议和索引指引。
- `.trellis/lessons/index.md`：按 `id`、tags、适用场景和详情路径维护索引。
- `.trellis/lessons/topics/<topic>.md`：保存分主题 lesson 详情。
- `.trellis/lessons/archive/YYYY-QN.md`：保存低频历史归档，默认不读。

记录 lesson 时，默认写入 `.trellis/lessons/topics/<topic>.md` 并更新 `.trellis/lessons/index.md`；只有跨任务高频、缺失会反复导致错误的摘要才同步到 `.trellis/spec/lessons.md`。不要把完整 lesson 历史长期堆在 `.trellis/spec/lessons.md`。

除非用户明确指定其他路径，否则不写入其他位置。只有确认项目没有使用 Trellis 时，才默认写入到 `docs/lessons.md`。

## 必须记录的场景

出现以下情况时，需要记录 lesson：

- bug 修复
- 回滚
- 工具判断错误
- 模式切换错误
- Trellis 阶段错误
- parent / child task 拆分不合理
- child task 无法独立验证
- check 阶段遗漏任务产物
- 任务产物与 `.trellis/spec` 冲突
- GitNexus 影响分析不匹配
- Channel / 多 Agent 上下文丢失
- 递归派发问题
- worker 异常退出

---

## 记录格式

topic 文件中的每条 lesson 使用以下格式：

```md
## LESSON-YYYYMMDD-<slug>: <简短标题>

- 日期：
- 标签：
- 适用场景：
- 严重级别：
- 来源：
- 问题：
- 根因：
- 修复：
- 预防：
```

`index.md` 使用以下格式：

```md
| id | tags | read_when | summary | detail |
|---|---|---|---|---|
| LESSON-YYYYMMDD-<slug> | tag-a, tag-b | 何时需要读取详情 | 一句话摘要 | topics/<topic>.md#lesson-yyyymmdd-slug-简短标题 |
```

`.trellis/spec/lessons.md` 只保存短摘要和读取协议，建议保持在 150-200 行以内。超过该范围时，先把低频内容移入 topic 或 archive，再保留索引指引。

## 写入流程

1. 判断是否真的属于长期 lesson；普通任务总结、一次性实现细节和临时调研不要记录。
2. 选择 topic，例如 `workflow`、`validation`、`shell`、`markdown`、`gitnexus`、`trellis-channel`、`ui` 或项目领域名。
3. 将完整 lesson 追加到 `.trellis/lessons/topics/<topic>.md`。
4. 在 `.trellis/lessons/index.md` 增加或更新索引行，保证 tags、`read_when` 和 detail 路径可检索。
5. 只有 lesson 属于跨任务高频风险时，才把一句话预防规则同步到 `.trellis/spec/lessons.md`。
6. 当 topic 文件过长或内容低频时，保留摘要和索引，将旧详情移入 `.trellis/lessons/archive/YYYY-QN.md`。

## 读取边界

- 开始普通 Trellis 工作时，只默认读取 `.trellis/spec/lessons.md`。
- 不要默认全文读取 `.trellis/lessons/**`。
- 根据当前任务、错误信息、工具名、语言、tags 或 `read_when` 命中后，再读取对应 topic 或 archive。
- `archive/` 默认不读；只有复发问题、排障失败、用户要求追溯或 index 明确指向时才读取。
