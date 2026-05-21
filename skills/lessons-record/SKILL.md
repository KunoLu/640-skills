---
name: lessons-record
description: Use when a durable lesson should be recorded after bug fixes, rollbacks, tool misjudgments, workflow errors, failed validation, GitNexus mismatch, or multi-agent context loss.
---

# Lessons 记录 Skill

当需要记录长期经验教训时，使用本 Skill。

## 优先记录路径

1. `.trellis/spec/lessons.md`
2. `docs/lessons.md`
3. `.codex/lessons.md`

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

每条 lesson 使用以下格式：

```md
## <简短标题>

- 问题：
- 根因：
- 修复：
- 预防：
```
