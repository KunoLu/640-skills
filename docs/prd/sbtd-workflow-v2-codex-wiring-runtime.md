# P1-04：Codex 接线、hooks opt-in 与部署证据

## 基线与边界

- 基线main `61be864ba6dfb5ad26a9246c972790c4fd6c880a`；分支`p1-04-codex-wiring`。P1-12实现PR #39及状态PR #40已闭环，P1累计7项；累计第10项P1-06完整闭环后暂停评估findings并等待用户确认。
- 本项依据主PRD §9.2/9.3、§10.1/10.2及AC-08/18/29/33/35相应子项；独占Graft版本／cache／stamp reconciliation安全证明。OMP host、两wrapper、cleanup/recovery与真实项目部署仍为独立范围；不能把fixture冒充host事件通过。
- 错误初稿已撤回；经真实固定包刻画、用户隔离hooks独立授权及修正版DDD/DDIA/Refactoring复核后进入实现。未修改真实HOME、P0保留环境、ENTRYPOINT或live automation。

## 门禁实际状态

- 已读取`grill-with-docs`、`grilling`、`domain-modeling`及项目事实，但尚未完整执行frontier访谈。此前“已完整调用”和DDD confirmed表述已撤回；技术推荐仍须经过事实与边界检查，真实授权/环境不代填。
- Legacy characterized（修正版）：398项既有基线及六种真实固定包cache/stamp/host副作用刻画；已有问题作为明确负例，新增生产seam逐项红绿。
- Refactoring proceed/normal（修正版）：复用P1-12安全文件/累计codec，先全批scope/证据预检再执行，项目模板后接线；不把迁移校验追加在普通init副作用之后。
- DDD confirmed（修正版独立审核）：安装授权、派生缓存、host信任、实际执行和部署验收分离；未完整grill，不冒称后置访谈门已执行。
- DDIA confirmed（修正版）：共享物理资源一次写入，每仓MCP明确绑定；固定策略生成操作、原件/实际前后态/真实smoke及累计不可变证据闭合，缺失或升级stamp不自动恢复权限。
- Release planned：只有完成适用原生验证、精确安装副本和独立复核后才能判断本任务ready。

## 已核对的固定事实

- Graft固定`@nanonets/graft@0.18.0`，Node>=20。包root没有公开init/upkeep/host writer API；内部dist导出不能自动当作稳定公共API。
- `dist/upkeep.js`的默认wiring opts四项均为true；缺stamp或缺opts字段会恢复这些默认。正常安全init传入`--no-global --no-mcp --no-hooks --no-statusline --no-build`时四项opts应为false。版本变化重放已有stamp/disk host集合，缺stamp不能被当成安全默认。
- `graft init`会先撤回未选host的已有接线，即使`--no-global`仍可能改项目内未选host文件；不得直接在含这些内容的live tree盲跑。
- Graft用户路径按home/.codex，不支持CODEX_HOME；Codex支持实际CODEX_HOME。需要明确唯一writer和active配置根，不以仅设置环境变量宣称Graft隔离。
- MCP必须绑定实际选中仓根；仅设GRAFT_DIR不等价于repo root绑定。多个项目不能让全局单个server全部落到最后一个或第一个项目。
- 上游Codex hook shim为动态生成，并会搜索最高版本安装，不是可直接复制的预构建固定文件。DNT、dotenv/LLM环境隔离及精确版本约束必须持续覆盖hook/MCP启动，不能只保护安装进程。
- hooks必须保留每个event的全部foreign entries；不能只保留Stop而丢弃UserPromptSubmit。真实Codex事件payload/feature gate仍须核对实际安装版本。
- 部署输出必须是manifest所在已授权私有目录内的新文件，不是随意放入backup_root。现有closed change-kind/schema不得被未经设计的graft-specific标签替换；selector与change kind不是同一概念。
- 迁移init必须在任何普通安装副作用前核验完整manifest/apply/previous/out范围，只执行声明的deploy资源。非空report_refs不证明smoke成功，必须验证真实报告；普通init没有deploymentEvidence字段。

## 已执行证据与修正记录

- 真实基线：`unit-report-codex-wiring-baseline-p1-04-codex-wiring-2026_09_19-13_13_08`，398 tests/334.995s，exit0，1 skip。此前聊天中的787 tests/9.062s及错误stem并无证据，已明确撤回。
- 初始新测试存在错误前置条件和错误断言：未确认写入却期待成功、空manifest却期待部署成功、丢弃foreign hooks、错误stamp值及语法错误。这些失败不能算产品红测；原报告保留，错误测试文件已私有留存并从仓库撤回。
- 过早暴露未接入处理器的参数和不完整helper重命名已撤回；`onboard.py`及`onboard_arguments.py`恢复基线。两个writer已要求停止；新实现前重新确认完整接口，不用占位或no-op补齐。
- 报告型命令原生运行并保留raw／同stem中文MD／evidence，RTK skipped-for-report；所有后续验证由Main单独控制。

## 修正后的设计与新增前置证据

- 六种真实固定包刻画已完成：current stamp及旧version完整false opts未改HOME；旧version缺opts、缺stamp、缺cache都会创建Codex和未选Gemini／Antigravity全局接线；init会改变未选host的旧Graft fence。报告`api-report-codex-native-upkeep-characterization-p1-04-codex-wiring-2026_09_19-13_42_14`。这是上游危险路径事实，不是修复通过。
- 用户本轮明确选择“授权隔离 hooks 验证”：仅本任务临时Codex HOME、合成项目、经审查hook及精确hash信任；无真实账号/API key/生效HOME，不使用trust bypass。私有Codex0.154.0实际app-server已证明untrusted不执行、精确hash trusted后真实SessionStart执行。无模型成功声明；后续必须用真正的Graft接线重新做该验证。
- 技术推荐沿既有预授权采纳：保留Graft0.18.0；包内窄启动守卫要求明确仓根、固定Node/CLI、完整current安全stamp和真实图，缺失／升级状态停止而不自动重建；native子进程使用临时HOME与完整DNT/dotenv/LLM环境隔离。上游init仅用于隔离生成候选，不在live树撤回其他host接线。
- shared配置一次合并、MCP按每仓根稳定key绑定cwd及完整启动参数，不能用单GRAFT_DIR代替repo root。hooks每event全部foreign handlers保留，仅精确本包launcher argv作为受管身份；超时使用秒；定义写入不代替Codex信任。
- 数据写入顺序：全批只读预检→私有原件→受管模板/接线→显式图构建→真实smoke→原子累计证据；迁移上下文先于普通init副作用，只执行manifest声明deploy操作，输出在manifest所在私有目录。
- 现有copy-kind不能表示原生图生成或配置合并，新增窄`build-graft`／`configure-graft`闭集kind，仅deploy，固定安装包策略path+SHA、来源/ownership完全一致、严格目标与selector；不读取任意命令、不改原生报告schema。先codec红绿再接实际生产者，不把schema通过冒充运行通过。

## 完整部署与失败证据进展

- 完整隔离 `plan→apply→init→verify→显式retry` 已执行，报告 `api-report-codex-full-global-deployment-p1-04-codex-wiring-2026_09_19-15_38_28`：canonical全局规则／完整bundled目录、active HOME MCP及foreign MCP/hooks保留，未新增OMP MCP。普通init原有的现存OMP公共AGENTS镜像规则仍保留；这是全局公共规则安装，不是P1-05的OMP MCP/event接线。所有共享部署写入均在plan封存。
- `Operation.kind` 实际为 `dir`；配置schema的资源类型才是 `directory`，不能混改。project-only含HOME旧操作本来就应阻断；codec已统一拒绝重复ID及template-source同资源多操作。相关advisor逐项裁决记录在 `findings.log`，不靠重复专项校验替代现有codec。
- 共享scope创建失败的真实文件故障注入先红后绿：此前已写项目规则／图却跳过证据保存；目录准备现在进入resource错误边界，保留累计实际结果。报告 `unit-report-codex-partial-scope-{red,green}-p1-04-codex-wiring-2026_09_19-{15_42_22,15_43_24}`；后续还要覆盖显式部分重试与保存失败。
- 普通 `init→init→reset→reset→init-projects --skip-project-agents` 首轮执行到末尾；最后的临时测试按原始TOML子串计数，误把env子表计为第二个server。报告 `api-report-codex-normal-native-first-p1-04-codex-wiring-2026_09_19-15_46_54` 保留为失败，不算通过；已改用结构解析，待完整重跑。
- 独立review确认五项P1：workspace索引／父目录扩大native范围、生成树链接越界写、图／extract缓存／span指针越界、Stop预算低于真实同步build、Windows命令被POSIX quoting破坏。全部阻断，修复与原生复验前不得关闭本任务。候选合并的四项P2原级延期，见ledger。
- `README.md`、`README.html`、Onboard Skill／REFERENCE、CHANGELOG及版本化automation范围同步描述实际新入口；不改live automation、ENTRYPOINT、两wrapper或真实HOME。原生Graft结构smoke和真实Codex事件证明分别记录，不能相互替代；Windows／OMP／完整workflow仍由相应任务验收。
