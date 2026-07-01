# BDD And E2E Report Lessons

本 topic 保存 BDD 语言、Web UI 测试资产、Playwright / Maestro 报告与 E2E 运行汇总相关 lessons。

## LESSON-20260701-bdd-first-feature-language-gate: BDD First Feature Language Gate

- 日期：历史记录迁移，原始日期未记录
- 标签：bdd, gherkin, validation
- 适用场景：新增首个 `.feature` 或修改 BDD 语言规则
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：BDD 首个 .feature 语言规则必须有写入前和验证门
- 问题：项目规则和 `gherkin-bdd` Skill 已写明“无既有 `.feature` 时，场景文案默认中文、Gherkin 结构关键词用英语”，但实际新建 `.feature` 时仍生成了全英文文案。
- 根因：语言要求只作为描述性规则存在，没有在 `gherkin-bdd` 写入流程、Trellis BDD overlay 和 `project-validation` 检查中形成必须报告和验证的 gate；英文 PRD、design、代码标识符和英语 Gherkin 关键词容易把输出带向全英文。
- 修复：在 `gherkin-bdd` 增加写入前语言决策门，在 `trellis-workflow` 纳入 BDD overlay 阶段要求，并在 `project-validation` 增加 `.feature` 语言一致性检查和 blocked 条件。
- 预防：后续把“默认规则”沉淀为 Skill 时，必须同时覆盖生成前决策、生成后验证和最终输出状态；特别是语言、路径、source of truth 这类容易被上下文漂移覆盖的规则，不能只写成静态说明。

## LESSON-20260701-web-ui-test-assets-path-gate: Web UI Test Assets Path Gate

- 日期：历史记录迁移，原始日期未记录
- 标签：e2e, web-ui, assets
- 适用场景：生成 Web UI 测试资产或 selector audit
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Web UI 测试资产路径规则必须有参数和验证门
- 问题：项目规则只写明 `web-ui-autotest-generator` 的 JSON 测试资产应整理到 `tests/e2e/manifest/`，但 Skill 示例脚本默认仍会把 `ui-test-manifest.json`、`ui-selector-audit.json`、`ui-test-coverage.json` 输出到项目根目录。
- 根因：只把目标路径写成项目约定，不能保证后续 agent 或人工执行脚本时自动带上 `--out`、`--manifest`、`--selector-audit` 等参数；缺少收尾检查时，根目录残留也可能被误认为完成。
- 修复：在全局 / 项目 AGENTS 模板中固化 `tests/e2e/manifest/` 目标路径和必须加载 `project-validation` 的路由，在 `project-validation` Skill 中固化完整脚本参数，在 `trellis-workflow`、README 和模板 `.gitignore` 中固化路径契约引用、repair plan 忽略路径和根目录残留检查。
- 预防：后续沉淀工具输出路径、source of truth 或测试资产目录时，必须同时覆盖脚本调用参数、生成后存在性检查、根目录 / 旧路径残留检查和最终状态报告；不要只写“推荐放到某目录”。

## LESSON-20260701-e2e-report-artifact-status-separation: E2E Report Artifact Status Separation

- 日期：历史记录迁移，原始日期未记录
- 标签：e2e, reports, playwright
- 适用场景：Playwright / Maestro 运行产生报告产物但测试未全绿
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：E2E 报告文件生成与测试通过状态必须解耦
- 问题：Playwright 已生成 `index.html`、`results.json` 和 `junit.xml` 时，Agent 因最终全量 rerun 未全绿而报告“未生成正式报告”，没有把 HTML 重命名为模板要求的 `playwright-report-{feature_file_name}-{stamp}.html`，也没有生成同 stem 的 Markdown 汇总。
- 根因：模板规则把“最终全量通过后才能生成正式报告”和“最后一次运行必须留下命名报告产物”混在一起，导致失败运行已有 runner 产物时仍可能跳过报告归档；同时没有强制 Markdown 汇总使用中文。
- 修复：将 `Final Test Report` 定义为报告文件是否实际生成，将 `Final Full Rerun` 定义为最终全量是否通过；只要 Playwright 或 Maestro 产生原生 runner 报告，就必须生成命名报告和同 stem 中文 Markdown 汇总，失败状态写入汇总而不是跳过文件。
- 预防：后续修改测试报告规则时，必须分别检查“报告产物存在性”和“测试结论状态”，最终输出前用文件存在性校验确认命名报告和同 stem `.md` 都存在；不要把 `Run Summary MD` 标记为 `not-needed` 来绕过失败运行的汇总。

## LESSON-20260701-playwright-summary-html-stem: Playwright Summary HTML Stem

- 日期：历史记录迁移，原始日期未记录
- 标签：e2e, playwright, reports
- 适用场景：生成 Playwright HTML / JSON / JUnit 报告汇总
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Playwright Markdown 汇总不得以 results.json 为 stem
- 问题：在会话 `019f1628-6776-77f0-9d32-3a867477eb96` 中，Playwright 已生成 `tests/e2e/reports/html/index.html`、`tests/e2e/reports/results.json` 和 `junit.xml`，但最终只围绕 `results.json` 生成了 `results.md`，没有把 `index.html` 提升 / 复制为带时间戳的 `playwright-report-*.html`，也没有生成同 stem 的 `playwright-report-*.md`。
- 根因：模板虽然要求“命名 HTML + 同 stem Markdown”，但没有明确排除 `results.json` / `junit.xml` 这类 reporter 产物作为 Markdown stem；Agent 把“同 stem”错误绑定到 JSON reporter，而不是绑定到正式 HTML 报告。
- 修复：在全局 / 项目 AGENTS 模板、`project-validation`、`trellis-workflow` 和 README 中明确 Playwright 的 canonical stem 只能来自命名后的 HTML 报告；`results.md`、`result.md`、`junit.md` 或 `index.md` 不能满足 `Run Summary MD: generated`。
- 预防：以后只要 Playwright 产生 runner 原生报告，收尾 gate 必须检查 `tests/e2e/reports/html/playwright-report-*.html` 与同名 `.md` 成对存在；`results.json`、`junit.xml` 和默认 `index.html` 只能作为辅助产物或复制源，不能替代正式报告。
