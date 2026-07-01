# Lessons

本文件是当前配置摘录仓库的 lessons 必读短入口，不再保存完整历史库。每次执行本仓库操作前仍必须先读取本文件，再按当前任务主题、错误信息、工具名或 tags 读取命中的详情。

完整 lessons 结构：

- `docs/lessons/index.md`：按 `id`、tags、适用场景和详情路径维护索引。
- `docs/lessons/topics/<topic>.md`：保存分主题完整 lesson 详情。
- `docs/lessons/archive/YYYY-QN.md`：低频历史归档；默认不读，只有 index 明确指向或用户要求追溯时再读。

写入新 lesson 时：

1. 先判断是否属于长期 lesson；普通任务总结和临时调研不要写入。
2. 将完整记录写入对应 `docs/lessons/topics/<topic>.md`。
3. 同步更新 `docs/lessons/index.md`。
4. 只有跨任务高频、缺失会反复导致错误的规则，才把一句话摘要补到本短入口。
5. 不要把完整 lesson 历史重新堆回本文件。

## 高频摘要

- 当前仓库是 Codex 配置文件与 Skill 的摘录 / 同步源，不是真实业务项目；修改时先区分“配置源文件”和“真实项目模板”。
- 每日版本检查自动化只能读取 `ENTRYPOINT.md` 当前版本作为比对基线，不能自动写回版本号；只有用户手动输入 `更新` / `update` 才执行写回和归档。
- 普通修改任务不得同步到本机生效路径；只有用户主动输入 `同步` / `sync` 才执行本地同步。
- 自动化专用规则只能写入本仓库根 `AGENTS.md` 或相关自动化说明，不要污染可复用的全局 / 项目 AGENTS 模板。
- 展示型或文档型任务中的参考配置，默认先视为展示内容；只有用户明确要求修改当前仓库配置时才落地到仓库根。
- 使用 `rtk` 后遇到明显包装器参数解析异常时，必须用原生命令复验同一事实。
- 编写一次性验证脚本前，先对照本入口和命中的 topic，避免重复使用已记录的问题写法；Markdown 解析优先按标题层级和表头语义，不要按裸 `---` 或脆弱正则切割。
- 校验脚本必须按目标文件职责断言，先确认实际 schema；不要用同一 expected 列表无差别扫描所有文件。
- Web UI 测试资产和 Playwright 报告路径必须有参数和验证门；Playwright 正式报告以命名 HTML 为主轴，`results.json` / `junit.xml` / 默认 `index.html` 不能决定最终 Markdown stem。
- 新增或修改用户可见 BDD `.feature` 场景时，首个 `.feature` 默认中文场景文案 + 英文 Gherkin 关键词，并在写入前和验证阶段确认语言规则。

## Topic 路由

| topic | read_when | detail |
|---|---|---|
| repository-workflow | 版本检查、同步、配置摘录仓库定位、AGENTS / ENTRYPOINT / README 规则、GitHub release 依据、合并远程分支或展示型任务 | `docs/lessons/topics/repository-workflow.md` |
| validation-scripts | 一次性校验脚本、Markdown 解析、shell quoting、Node / Python 脚本、动态导入、结构化断言、schema 检查 | `docs/lessons/topics/validation-scripts.md` |
| bdd-e2e-reports | BDD 语言、Web UI 测试资产、Playwright / Maestro 报告、E2E 报告与测试状态解耦 | `docs/lessons/topics/bdd-e2e-reports.md` |

完整索引见 `docs/lessons/index.md`。
