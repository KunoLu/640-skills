# SBTD 项目规则

项目实际代码、测试、配置、README、CI和更深层AGENTS优先；不为模板重排目录或引入第二套约定。已安装全局规则与sbtd-task可见时继承共同路由，只按需加载references。public bootstrap／project-only不等于安装全部全局Skill或激活完整环境。

## 所有模式的项目入口

先核对根、任务、分支与只读范围。模式为当前明确选择 > 同任务有效记录 > 新任务default；旧模式缺失／多候选询问，不凭mtime、旧handoff或输出样式推断。推荐升／降模式须先解释并暂停，用户保持原模式就继续，无新实质风险不重复劝说。正常“继续”继承模式；跨分支写入另取明确决定。

需求已清楚先读事实，不重复grill；说明未完整调用原因。完整grill-with-docs后，所有模式必须调用book-ddd-distilled-modeling，输出独立DDD Boundary Review并按其门禁通过；缺失、不可读或证据不足均blocked，不能用fallback确认需求或进入设计／实现。

有写权限、分支匹配且路径／ignore已保护时尽早保存确认模式；没有onboard不等于不能开展普通任务。只读三模式均不写task、active、handoff、developer、ignore或会写缓存的工具状态。明确产物、项目已有测试／BDD和必要安全不按模式省略。

## 无全局 Skill 的最小 fallback

default按需调查／实现／聚焦验证；lite用目标、步骤、验证、记录、交付短清单；strict保留完整适用before-dev/check/finish-work，必需Skill／证据缺失不得报通过。先锁定bug和保留行为，再改根因；避免无关重构，验证真实变化，报告不能执行的检查和风险。

strict仍按客观触发识别Book门禁：既有生产代码修改用book-refactoring-pass；bug／弱测试／不清行为用book-legacy-change-safety；领域歧义或完整grill后用book-ddd-distilled-modeling；持久／共享数据、schema、异步流、所有权或恢复用book-ddia-data-design；运行时／部署／外部集成变更在验证后用book-release-readiness。遵守对应Skill的结果与修正回路，必需Skill或证据不可用就blocked，不凭fallback伪造通过。未命中的门禁不强制执行。

可安全处理时，普通default任务记录于`.sbtd/tasks/<id>/task.md`，lite/strict或明确共享任务于`ai/tasks/<id>/task.md`。模式与存储独立。最小frontmatter为schema_version整数1、稳定id、workflow_mode、mode_source（新隐式default用default，明确选择用user）、mode_note、status、branch、created_at、updated_at、completed_at；parent按需。新时间必须真实带时区，非Git branch为null，未完成completed_at为null。正文只保留真实目标、进度、证据、下一步及必要事件；不生成整套文件占位。

task唯一拥有mode/status；`.sbtd/active-task.json`只存schema_version/task_id/安全相对task_path，index仅导航。安全解析完整记录并保留其他内容；未知schema、无效旧模式、引用逃逸／symlink、父子冲突或双副本不得猜测覆盖。无法可靠验证／原子更新时不写，明确未持久化，不捏造格式或恢复成功；default/lite可继续不依赖它的安全工作。

状态正常沿planned→in-progress→checking→done；checking发现问题可回in-progress，done重开先回planned。只有验收证据成立才记done与真实completed_at。进入blocked必须写非空blocked_reason，解除时清空；不保存blocked_from字段。完成／阻塞／重开／归档或明确重绑定事件放在同一task.md的`## 状态事件`表（at/from/to/reason/evidence），与字段一次原子更新。重开先保留旧完成证据再清空当前completed_at；持续blocked只改原因，不重写恢复前态。恢复取最近未解除的真实入阻塞前态；未知／冲突则用户选择planned/in-progress/checking，记录真实解除事件和历史未知原因，不能直接done或伪造ingress。完整细节以可用sbtd-task/state reference为准；缺安全能力不强行写入。

首次写本地状态／身份／handoff前检查ignore和tracked；缺保护只请求窄授权，不自动init、改旧规则或清理数据。保存失败保留当前会话选择并说明恢复不可靠。归档、共享提升、清理和发布需要各自确认，Git tag不代替ignored数据/HOME备份。

## 路径与工具边界

- 任务：本地`.sbtd/tasks`或共享`ai/tasks`；长期规范`docs/spec`；lesson短入口默认`docs/spec/lessons.md`，已有明确入口则沿用，完整库为`docs/lessons/{index,topics,archive}`。
- handoff：仅真实暂停／上下文切换／续接需要时写受保护的`docs/handoffs`，完整task ID安全编码，无信息变化不重写；不是3/5次计数触发，不覆盖task模式。只读仅对话。
- BDD：沿用项目路径／语言，默认中文场景+英文关键词；本配置源仓库的no-.feature例外不复制到业务项目。按模式/风险及明确交付使用方法，既有项目强制规范仍有效。
- 测试与报告：沿用项目命令和project-validation；CLI是真实回归执行器，MCP诊断不冒充CI。正式命名报告和同stem中文汇总必须保留，runner current目录不是归档；mock/旧SHA/dirty local不冒充当前full-stack。具体路径与状态词表按实际适用Skill，不为无关工具输出整表。
- Graft只作可降级结构证据；不对共父目录联邦，不启用LLM/cloud或上传代码，不用空图/exit0证明无影响；未证明只读副作用前不运行其查询。影响结论回到源码/LSP/contract。
- UI语境使用已有design system，ui-ux-pro-max初稿、可用impeccable塑形/polish、shadcn处理已用组件；上下文默认docs/PRODUCT.md与docs/DESIGN.md。React Bits仅明确需要时按已确认tier／registry／许可执行，不打印key、不把全局Skill复制进项目。

## 身份、输出和交付

只在需要写lesson时解析`.sbtd/developer`的合法name；本地缺失且linked worktree才只读主checkout，否则问用户，不猜名字或改历史ID。首次建立只写必要身份且先满足保护授权；不顺带初始化。只写自己的marker块，完整读取命中主题的所有作者块。

没有全局输出协议时不猜测caveman自动状态机；手动样式按可用Skill和用户选择，不影响执行模式。normal mode只退出输出样式。最终交付完整列出结论、文件、验证、跳过及原因、风险／恢复限制；账号、密钥、PII、生产数据不进入任务／报告。

一项职责一个writer，一个环境一个controller。原生独立review不等于启动持久协作runtime。旧目录／旧工具只作为显式迁移输入，不因其存在自动初始化或接回旧运行路由。
