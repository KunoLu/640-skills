# Validation And Script Lessons

本 topic 保存一次性验证脚本、Markdown 解析、shell quoting、Node / Python 脚本和结构化断言相关 lessons。

## LESSON-20260701-skill-enumeration-filter-directories: Skill Enumeration Filter Directories

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, skills, filesystem
- 适用场景：枚举 `skills/**/SKILL.md` 或写验证脚本
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：验证脚本枚举 Skill 时必须过滤目录
- 问题：每日版本检查的 Node 验证脚本直接遍历 `skills/` 并拼接 `SKILL.md`，把 macOS 产生的 `.DS_Store` 当成目录读取，导致验证脚本自身失败。
- 根因：验证脚本假设 `skills/` 下只有 Skill 目录，没有使用 `Dirent.isDirectory()` 或等价方式过滤文件。
- 修复：重新运行验证时只枚举目录，并保留 `.gitignore` 三行校验，确认 `.DS_Store` 仍被忽略。
- 预防：后续所有针对 `skills/**/SKILL.md` 的自动化检查都应先过滤目录或直接使用 `rg --files skills -g SKILL.md`，不要手写无类型的路径拼接。

## LESSON-20260701-markdown-section-parse-headings: Markdown Section Parse Headings

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, markdown, parsing
- 适用场景：解析 Markdown 章节或表格
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：解析 Markdown 章节不得按裸分隔线切割
- 问题：每日版本检查的 Node 验证脚本用 `split("---")` 截取 `ENTRYPOINT.md` 版本监控章节，误把 Markdown 表格的 `|---|` 分隔行当作章节边界，导致脚本自身误报启用工具为空。
- 根因：验证脚本使用了过宽的字符串分隔，没有按 Markdown 标题层级或行首完整分隔线解析。
- 修复：改为按下一个二级标题截取章节，再解析表格行。
- 预防：后续解析 Markdown 章节时优先按标题层级、行首锚点或 Markdown parser 处理；不要用裸 `---` 这类会命中表格分隔行的字符串切割。

## LESSON-20260701-node-regex-anchor: Node Regex Anchor

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, node, regex
- 适用场景：写 Node / JavaScript 一次性验证脚本
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Node 验证脚本不要使用非 JS 正则锚点
- 问题：每日版本检查的 Node 验证脚本用 `\z` 作为文末锚点，JavaScript 正则不支持该语义，导致最后一个 Markdown 章节匹配失败；随后用 `^...|$` 搭配 `m` 模式时，`$` 又匹配到行尾，导致章节被截成空段。
- 根因：把其他正则方言中的文末锚点直接移植到 Node.js，且没有意识到 JavaScript 正则 `m` 模式会改变 `$` 的匹配语义。
- 修复：校验脚本改用行扫描和标题索引截取 Markdown 章节，避免依赖跨行 lookahead 的文末锚点。
- 预防：后续一次性 Node 校验脚本只使用 JavaScript 正则明确支持的语法；复杂章节解析优先用行扫描或标题索引，避免跨语言正则习惯迁移。

## LESSON-20260701-rtk-wrapper-native-recheck: RTK Wrapper Native Recheck

- 日期：历史记录迁移，原始日期未记录
- 标签：rtk, shell, validation
- 适用场景：`rtk` 输出疑似包装器参数解析错误
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：rtk 包装器失败后必须原生命令复验
- 问题：每日版本检查中，`rtk git diff -- AGENTS.md ...` 会把 pathspec 误解析成 revision，`rtk test -d` / `rtk test -f` 也会输出 shell usage 并失败，容易被误读成仓库文件或目录状态异常。
- 根因：`rtk` 包装器对部分带 `--` pathspec 或 POSIX `test` 参数的命令解析不等价于原生命令；失败来自包装器参数处理，而不一定来自 Git 或文件系统事实。
- 修复：保持先尝试 `rtk` 的仓库规则；当 `rtk` 输出明显是包装器/参数解析错误时，立即用对应原生命令复验同一事实，并在最终输出说明 fallback。
- 预防：后续验证脚本和自动化总结中，要区分“rtk 包装器失败”和“底层验证失败”；只有原生命令或结构化脚本也失败时，才判定验证事实未通过。

## LESSON-20260701-markdown-backtick-shell-quoting: Markdown Backtick Shell Quoting

- 日期：历史记录迁移，原始日期未记录
- 标签：shell, markdown, rg
- 适用场景：搜索含反引号、`$`、`!` 等 Markdown 文本
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Markdown 反引号搜索必须安全引用
- 问题：验证模板是否残留旧文案时，`rg` 搜索模式包含 Markdown inline code 反引号，命令用双引号包裹后被 zsh 当成命令替换，出现 `command not found`，导致验证命令自身失败。
- 根因：双引号不会阻止 shell 对反引号执行命令替换；包含 `` `code` ``、`$` 等 shell 元字符的 Markdown 搜索模式不能直接放在双引号里。
- 修复：改用单引号包裹 `rg` 搜索模式，并用结构化 Node 断言补充验证，区分“命令引用失败”和“模板内容失败”。
- 预防：后续验证 Markdown 文档中含反引号、`$`、`!` 等 shell 元字符的文本时，优先使用单引号、转义字符或 Node 结构化检查；最终报告中说明失败来自命令写法还是内容事实。

## LESSON-20260701-validation-script-check-lessons: Validation Script Check Lessons

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, lessons, scripts
- 适用场景：写一次性验证脚本前
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：一次性验证脚本必须对照已读 Lessons
- 问题：每日版本检查已经读取 `docs/lessons.md`，但结构化 Node 验证脚本仍重复使用了 JavaScript 不支持的 `\z` 文末锚点，导致验证脚本自身失败。
- 根因：读取 lessons 后没有把其中的脚本编写禁忌转化为当次验证脚本约束，只在事后依赖 rerun 纠正。
- 修复：改用行扫描和标题索引截取 Markdown 章节，避免跨语言正则锚点；重新执行结构化验证确认内容事实通过。
- 预防：后续编写一次性验证脚本前，先把已读 lessons 中与脚本、shell quoting、Markdown 解析相关的条目作为 checklist 核对；不要重复使用已明确记录为失败原因的写法。

## LESSON-20260701-node-one-liner-complexity: Node One Liner Complexity

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, node, scripts
- 适用场景：Node one-liner 逻辑较复杂时
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：复杂 Node one-liner 校验必须降低语法风险
- 问题：每日版本检查的结构化 Node 校验脚本写成过长 one-liner，手工嵌套 `for` / `if` 块时多写了一个闭合大括号，导致验证脚本先于内容检查失败。
- 根因：为了避免临时文件，把多段 Markdown 解析、表格解析和断言逻辑压缩进单条 `node -e`，缺少缩进和局部函数边界，语法错误不易肉眼发现。
- 修复：将脚本拆成更小的函数和更少的嵌套，重新运行结构化校验，区分“验证脚本语法失败”和“仓库内容事实失败”。
- 预防：后续一次性 Node 校验脚本应优先使用短函数、行扫描和早返回；如果逻辑超过几段断言，先拆成多个命令或清晰的多行脚本字符串，不要把复杂控制流压成不可审查的一行。

## LESSON-20260701-python-fstring-one-liner: Python FString One Liner

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, python, scripts
- 适用场景：Python one-liner 包含 f-string、嵌套引号或分支
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Python one-liner 校验避免嵌套 f-string 转义
- 问题：一次性 Python 结构化断言脚本在 shell `python -c` 中嵌套 f-string、引号和反斜杠转义，导致脚本先发生 `SyntaxError`，没有执行到内容校验。
- 根因：为了把多分支断言压成一条命令，在 f-string 表达式里继续嵌套带转义的字符串字面量，触发 Python 对 f-string 表达式的语法限制。
- 修复：将嵌套表达式拆成普通变量赋值和字符串拼接，重新运行结构化断言并确认内容事实通过。
- 预防：后续 Python one-liner 校验只保留简单表达式；涉及条件分支、嵌套引号或多段断言时，先拆成局部变量和多行脚本字符串，不要在 f-string 表达式内继续写转义字符串。

## LESSON-20260701-importlib-dataclass-sys-modules: Importlib Dataclass Sys Modules

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, python, importlib
- 适用场景：动态导入含 dataclass / 运行时反射的模块
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：importlib 动态导入 dataclass 模块需先注册 sys.modules
- 问题：一次性 Python 校验脚本用 `importlib.util.module_from_spec()` 动态导入包含 `@dataclass` 的模块时，没有先写入 `sys.modules`，导致 dataclasses 处理类型注解时取不到模块命名空间并抛出 `AttributeError`。
- 根因：动态导入流程只创建了模块对象并执行 `exec_module()`，但没有模拟正常 import 机制中的 `sys.modules[name] = module` 注册步骤。
- 修复：在 `spec.loader.exec_module(module)` 前先执行 `sys.modules[name] = module`，重新运行外部 Skill 覆盖安装断言并确认通过。
- 预防：后续用 `importlib` 在一次性校验中加载带 dataclass、枚举注册、运行时注解或模块级反射的文件时，先注册到 `sys.modules`；如果只验证 CLI 行为，优先通过子进程调用脚本入口，减少动态导入差异。

## LESSON-20260701-skill-markdown-frontmatter: Skill Markdown Frontmatter

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, markdown, skills
- 适用场景：校验 `SKILL.md` Markdown 结构
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：Skill Markdown 校验必须允许 frontmatter
- 问题：每日版本检查的结构化 Node 校验脚本要求所有 Markdown 文件必须以 H1 开头，误判带 YAML frontmatter 的 `SKILL.md` 不可读。
- 根因：验证脚本把普通文档规则套用到 Skill 入口文件，忽略了 Skill 文件标准格式通常先包含 `---` frontmatter，再进入正文标题。
- 修复：将 Markdown 可读性校验改为同时接受 H1 开头和 YAML frontmatter 开头，并继续检查非空内容与代码围栏配对。
- 预防：后续校验 `SKILL.md` 时先识别文件类型；对 Skill 入口校验 frontmatter + 正文结构，不要强制套用普通项目文档的 H1 起始规则。

## LESSON-20260701-ast-literal-eval-expression-config: AST Literal Eval Expression Config

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, python, ast
- 适用场景：解析 Python 配置常量或表达式
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：ast.literal_eval 不适合解析含调用表达式的配置常量
- 问题：结构化校验 `onboard.py` 中 `SKILL_SOURCES` 时，用 `ast.literal_eval()` 直接解析包含 `TEMPLATE_DIR / "skills" / ...` 表达式的字典，验证脚本先抛出 `ValueError`，没有执行到内容一致性检查。
- 根因：`ast.literal_eval()` 只接受纯 Python 字面量；当字典值包含变量名、路径拼接、函数调用或其他表达式时，应改用 AST 遍历提取 key，或用源码文本 / 运行时导入的方式校验。
- 修复：改为遍历 AST 字典键，只提取字符串 key 来确认 Skill 名称登记情况，再用文件系统和 manifest 做交叉校验。
- 预防：后续一次性 Python 结构化校验中，只有目标表达式确认为纯字面量时才使用 `ast.literal_eval()`；否则优先做 AST 节点级提取、受控导入或直接文本/JSON 校验。

## LESSON-20260701-structured-validation-by-file-role: Structured Validation By File Role

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, templates, responsibilities
- 适用场景：写跨文件结构化校验
- 严重级别：high
- 来源：迁移自 `docs/lessons.md`
- 原始标题：结构化校验必须按目标文件职责断言
- 问题：校验 5 个 book-derived Skill 接入时，脚本要求每个 Skill 名称都必须出现在 `project-validation/SKILL.md`，但该文件只负责修改后验证策略，合理范围只需要提到验证后相关的 `book-release-readiness` / `book-ddia-data-design`。
- 根因：一致性校验把“全局登记文件”和“阶段性职责文件”混为一类，过度要求所有目标文件都完整枚举全部 Skill。
- 修复：按文件职责拆分断言：manifest、安装脚本、全局 / 项目 AGENTS、onboard 文档和展示页必须覆盖全部新增 Skill；`trellis-workflow` 覆盖阶段编排；`project-validation` 只校验验证后相关 Skill。
- 预防：后续编写结构化校验时，先定义每个文件的责任面，再为不同责任面设置不同断言，不要用同一个 expected 列表无差别扫描所有文件。

## LESSON-20260701-config-schema-confirmation: Config Schema Confirmation

- 日期：历史记录迁移，原始日期未记录
- 标签：validation, schema, config
- 适用场景：校验 JSON / TOML / YAML 配置前
- 严重级别：medium
- 来源：迁移自 `docs/lessons.md`
- 原始标题：结构化配置校验前必须确认实际 schema
- 问题：校验 `templates/MANIFEST.json` 时，断言脚本凭记忆读取顶层 `files` 字段，但实际 schema 使用 `templates` 字段，导致脚本抛出 `KeyError`，没有执行到内容事实校验。
- 根因：编写一次性结构化校验时没有先读取目标配置的实际结构，把其他 manifest 习惯迁移到了当前仓库。
- 修复：先读取 `templates/MANIFEST.json`，确认顶层字段后，将断言脚本改为读取 `manifest["templates"]`。
- 预防：后续校验 JSON / TOML / YAML 配置前，先查看目标文件 schema 或用受控解析打印顶层 key；不要在未确认字段名时直接写断言。
