---
schema_version: 1
id: v2.1.0-rc.5-external-skills-repin
workflow_mode: strict
mode_source: user
mode_note: 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
status: checking
branch: chore/rc5-external-skills-repin
created_at: '2026-11-12T00:05:01+08:00'
updated_at: '2026-11-12T00:27:58+08:00'
completed_at: null
---

# rc.5 外部 Skills 重新锁版本

## 目标与本轮边界

本 PR 将 19 个 required external Skills 的 stable 集从 `2026-10-28.1` 按官方晋升流程锁到各上游主线最新 HEAD，沿用 #197 的定义，不改为追随 tag／Release。本项补做 rc.4 明确留到后续的 stable 晋升，其余已移动的主线仓库一并纳入。

第 1 轮只建立本 task.md，以及正式生成器更新的 `ai/tasks/index.md`。晋升、实现测试和双语 CHANGELOG 实现条目留待后续轮次；不改生产代码、快照、测试、catalog、契约或旧任务。不提交、不推送、不开 PR，不运行 Git 写命令；提交由编排方稍后处理。不建立 active、handoff、developer 或其他工作流记录。保持 checking，completed_at 为 null。

未完整调用 grill-with-docs：边界与既有晋升契约明确，源码可回答本轮问题，不新增领域决定。

第 2 轮：按下述授权投票结果开始晋升与实现；第 1 轮的“尚未执行”、计划及待选择描述保留为历史。本轮仅经官方晋升器更新既有六仓库与 19 项集合，stableSet 使用 `2026-11-11.1`，promotedAt 由命令实际生成。禁止手改镜像、扩展 source 合同或登记新 Skill；拒绝即停止。继续 strict、checking、completed_at=null；独立安全评审、CI 与合入不在本地通过声明内。只使用会话内 todo 清单，不调用 task 工具、子代理或 find，不运行 Git 写命令。

## 决策来源

- 用户 2026-11-11 15:10 群内确认（rc.5 全程用 strict），Lord 记录。
- 用户 2026-11-11 15:08 群内确认（graft 甲：保持 pin 0.28.0，graft 仍为可选；graft 文档放最终文档 PR，不放本项），Lord 记录。
- 用户 2026-11-11 23:55 群内确认合入 #213（快照内存最多留 8 份，最久没用的先踢出），Lord 记录。Lord 将 #213 squash 合入 main，合并提交 `a2a3aa72281e9127de821f19fb5056ad76306d16`，提交时间 `2026-11-11T23:55:48+08:00`，并删除远端开发分支；不把提交秒数当作群内确认的秒数。
- 在上述合入提交时间之后，Lord 群内调度：清掉本地 #213 分支与工作区，然后开始 rc.5 下一项「外部 skills 重新锁版本」，graft 保持可选的 0.28.0 不动；先照常写 task.md，把范围和要改的文件报到群里。这是 Lord 的调度；本会话未执行或核验该清理。
- 群内事实及远端合并经过采用本轮提供的已核实背景，不冒充本会话访问群聊或远端所得。本轮计划由主模型对照仓库定义与源码整理；下列上游目标采用编排方核查，不冒充本轮重新联网实测。
- 按 640 2026-11-11 23:59 授权的群内投票结果：授权规定需要拍板的选择交由群成员投票，按推荐最多的选项执行。640-skills 群在 2026-11-12 00:11 至 00:12（北京时间）完成三项投票；Lord、Reviewy、Researchy、CodeX、OMP 共 5 票，三项各为 5 票同意推荐、0 票反对。结果：各仓库锁主线最新 HEAD，不锁 Release／semver tag；shadcn-ui 与 ponytail 即使受管子路径内容不变仍锁仓库 HEAD，使六仓库对齐同一核查日；mattpocock 新出现而尚未登记的 Skill 不加入本 PR，以后另开 PR。此为提供的已核实事实，不冒充本会话读取群聊所得。

## 范围与非目标

范围：6 个已登记上游仓库的 pin、对应 19 个 Skill 快照、manifest digest 与许可证文件；因 live pin 断言而必须调整的测试；本 PR 双语 CHANGELOG 在 rc.5 未发布标题下的 Changed／变更追加条目，不改已有条目；README×2／automation prompt 的维护判断，有本项造成的漂移才改。

非目标：graft 0.28.0 及其文档（留最终文档 PR）；caveman pin（当前 `v4.0.1`／`d262ab3882952a59312ff3537cd86d894523c5ab`）；ENTRYPOINT 工具监控表及其他宿主／CLI pin；上游未登记新 Skill；catalog 布局；契约／schema／PRD／ADR／OpenAPI／数据字典；晋升器本身；旧契约／文档任务；运行时／前端／安装逻辑；同步到本机生效路径；发布或 tag。历史 CHANGELOG 与 `ai/tasks/external-skills-stable-upgrade-2026-10/task.md` 原样保留。

## 当前源码依据

只读基准：`a2a3aa72281e9127de821f19fb5056ad76306d16`，分支与 front matter 一致，起始工作区干净。以下行号均来自本轮读取；静态观察不代表晋升或安装通过。

| 事实 | 当前依据 |
|---|---|
| #197 定义是 6 个仓库升到「各自主线最新 HEAD」，不是最高 semver；从 2026-09-14.6 升到 2026-10-28.1 | `ai/tasks/external-skills-stable-upgrade-2026-10/task.md:15-34`：逐仓库 diff／许可证审查、整组事务晋升、全集合校验、strict-stable 19/19、测试与 README×2／automation prompt／CHANGELOG×2 维护判断 |
| rc.3 固定到各自 2026-10-28 主线 revision；rc.4 已明确三个上游 HEAD 移动，stable 晋升是独立评审流程 | `CHANGELOG.md:43,61`、`CHANGELOG.zh.md:43,61`；本项承接后续晋升，不重写历史 |
| rc.5 已有未发布区与 Changed／变更栏目 | `CHANGELOG.md:10-28`、`CHANGELOG.zh.md:10-28`；后续追加新条目，已有 #213 等事实保持 |
| stable 是未经修改的上游原样镜像，不是 fork；manifest 是事实源 | `sbtd-workflow-onboard/SKILL.md:198-200`、`sbtd-workflow-onboard/REFERENCE.md:279-304`；只经官方命令，禁止手改快照 |
| 当前 stableSet／promotedAt 为 2026-10-28.1／2026-10-28；6 仓库、19 个 sourceSubpath／stablePath／treeSha256 | `sbtd-workflow-onboard/assets/external-skills/stable/MANIFEST.json:1-193`；impeccable 为 Apache-2.0，含 LICENSE 与 NOTICE.md；其余为 MIT，shadcn 的源许可证为 LICENSE.md |
| catalog 的 19 条 external-skill 只登记 repo／subpath／aliases，没有 revision | `sbtd-workflow-onboard/catalog.json` 的全部 external-skill 条目；`sbtd-workflow-onboard/scripts/onboard.py:182-209,245-253`；无须为 re-pin 修改 catalog |
| 已登记集合是 mattpocock 11、impeccable 1、ui-ux-pro-max 1、shadcn 1、ponytail 4、i-have-adhd 1 | manifest 与 catalog 对照；mattpocock 为 diagnosing-bugs、tdd、grill-me、grill-with-docs、grilling、domain-modeling、codebase-design、handoff、writing-for-agents、to-spec、to-tickets；ponytail 四项为 ponytail、ponytail-review、ponytail-audit、ponytail-debt |
| 每次晋升一个仓库全部受管 Skill；完整候选集通过后才事务替换，失败尝试恢复 | `sbtd-workflow-onboard/scripts/onboard.py:4091-4340`，尤其 4157-4161、4230-4276、4301-4338；不是六仓库总事务，后一个失败不意味着前几个自动撤回 |
| 既有仓库不能借 --license／--license-file 重写元数据；名称／subpath／license 路径改变不能猜测 | `sbtd-workflow-onboard/REFERENCE.md:304-319`、`sbtd-workflow-onboard/scripts/onboard.py:4137-4148`；本 PR 不扩展 source 合同 |
| stableSet 由参数指定，promotedAt 由执行环境当日生成 | `sbtd-workflow-onboard/scripts/onboard.py:4301-4306`；不是各仓库独立日期字段，也不从 stableSet 截日期 |
| Ponytail live 断言同时固定 stableSet、promotedAt、revision | `tests/test_onboard_ponytail_integration.py:28-31,75-113`；`PONYTAIL_STABLE_SET = "2026-08-27.1"` 仅供模拟晋升（172-184、211-250），不能跟着替换 |
| ADHD 固定 revision、SKILL.md 与许可证摘要，没有固定 stableSet | `tests/test_onboard_i_have_adhd.py:24-31,69-98`；本次 revision 不变，预计测试无需编辑，晋升后复核 |
| 全集合真实字节摘要和离线 stable 安装已有回归入口 | `tests/test_onboard_external_skills.py:241-276,1006-1025`；另有 source containment、事务失败恢复、缓存排除与 raw-byte 换行边界用例；不自造摘要算法 |
| 普通发现新版本不授权 stable promotion | `prompts/automations/references/version-check-scope.md:71-84`；主 prompt 的 tag 监控不替代本项主线 pin 定义 |
| README 已把精确 pin 指向 manifest，automation 保留独立权限边界 | `README.md:385-400`、`README.zh.md:376-391`、`prompts/automations/sbtd-workflow-tools-version-check.md:22-26,108-114`；本轮未见 re-pin 必然造成文字漂移，后续仍作维护判断 |

### 技能／仓库 pin 表

核查来源说明：当前 pin 已由本轮读取 manifest 复核；目标 SHA、提交时间与路径变化来自编排方在北京时间 2026-11-11 23:58 至 2026-11-12 00:02 的 `git ls-remote`、`gh api` compare／commits／releases 核查。全部 ls-remote 结果在跨入 00:02 前取得。本轮未再次联网抽查；实现轮若复测不同，记录精确核查时间、差异并重新审阅目标，不悄悄换 SHA。

| 仓库 id／上游 | 当前 pin | 计划目标 | 受管子路径变化 | 核查来源 |
|---|---|---|---|---|
| mattpocock-skills／https://github.com/mattpocock/skills.git | `59db609eb1e18aaf59b63284d0e52255aff0c63c` | `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` | 有：`skills/engineering/codebase-design/DESIGN-IT-TWICE.md`、`skills/productivity/grilling/SKILL.md`；已登记共 11 项，其余 9 项未见变化 | 本轮 manifest＋编排方 ls-remote／compare；pin 2026-10-27 15:44:12 → HEAD 2026-10-31 22:23:30（北京时间） |
| impeccable／https://github.com/pbakaus/impeccable.git | `3e3a9179e01a60265000ce239c0a99803ec1e60d` | `c1e0e5492fbb524f5df84d635ecfae7dc438ec45` | 有：`plugin/skills/impeccable` 多次更新，含 4.8.1／4.8.2 及之后生成输出同步；路径最晚核查到 b856e5010f2d（2026-11-11 02:30:40）；编排方记录当前 scripts/VERSION 为 0.1.18 | 本轮 manifest＋编排方 ls-remote／commits／compare；pin 2026-10-28 14:05:26 → HEAD 2026-11-11 11:56:37（北京时间） |
| ui-ux-pro-max-skill／https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git | `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03` | `6ae86f61f520d6ca229d2f40e070410638c908c5` | 有：`.claude/skills/ui-ux-pro-max` 至少 15 文件，含 SKILL.md、数据、脚本、测试 | 本轮 manifest＋编排方 ls-remote／compare；pin 2026-10-26 18:07:27 → HEAD 2026-11-10 21:03:57（北京时间） |
| shadcn-ui／https://github.com/shadcn-ui/ui.git | `96da9cc7f1aa10580a3741664e2a77c721206c00` | `dd41d19e2f80ff6891951f7ced74c2c9a650b065` | 无：`skills/shadcn` 最近提交 4233ed1caded（2026-10-14 23:56:28）早于 pin；仍升仓库 revision，treeSha256 可能不变 | 本轮 manifest＋编排方 ls-remote／commits；pin 2026-10-27 20:30:19 → HEAD 2026-11-11 17:04:13（北京时间） |
| ponytail／https://github.com/DietrichGebert/ponytail.git | `09c434ab73ca43761c5d8b0c5d341926c2fba710` | `96608e078b2d5ea607c5c3b8b5a54d1c1fba6846` | 无：`skills/ponytail*` 未变；仓库 19 文件差异属 plugin／文档／i18n／资源；仍升 revision，treeSha256 可能不变 | 本轮 manifest＋编排方 ls-remote／compare；pin 2026-10-18 09:55:14 → HEAD 2026-10-29 19:59:31（北京时间） |
| i-have-adhd／https://github.com/ayghri/i-have-adhd.git | `1ecea1993b7fce257ffbd686c070948b5e07eda6` | `1ecea1993b7fce257ffbd686c070948b5e07eda6` | 无：pin／HEAD／v0.4.1 相同；revision 保持，整组晋升后的顶层 stableSet／promotedAt 更新 | 本轮 manifest＋编排方 ls-remote／releases；提交时间均为 2026-10-12 00:03:54（北京时间） |

建议 stableSet 用 `2026-11-11.1`，对应本次上游核查日，而非写记录时的日期；不改用 `2026-11-12.1`。`promotedAt` 让官方命令按实际执行环境日期生成，后续记录时区与实值，不伪造为核查日；i-have-adhd 没有单独 promotedAt，顶层字段随整体集合变化。

### 实现时必须小心的点与开放问题

1. 只经 `promote-external-skills-stable --repository <id> --revision <完整 40 位 SHA> --stable-set <yyyy-mm-dd.index> --yes` 晋升；每仓库整组、完整 19 项校验后再替换。禁止手改快照、绕过摘要、改换行凑摘要，或改晋升器过门。
2. shadcn／ponytail 受管子路径无内容 diff，不等于仓库 HEAD 没移动；仍按上表锁主线 revision，不能用目录摘要不变跳过 pin 维护。
3. mattpocock 上游的新 Skill（如 `skills/in-progress/software-factory`、`chief-of-staff` 及其他 engineering Skill）不加入 catalog；现有 11 项之外不复制。编排方材料中“其余已登记 11 个”的表述按本轮 manifest 纠正为已登记共 11 个、两项变化、其余 9 个，不扩充集合。
4. 上游规范名称、subpath、许可证路径或许可合同变化时，停止该部分晋升并记录开放问题；先另开 source 合同／catalog 决策 PR，等用户决定。本项不擅改 manifest 的来源布局或 schema。原路径上的许可证内容更新须审查并由晋升流程同步；发现许可条款风险不能只复制后宣称通过。
5. 不能把最新 tag／Latest Release 当目标：编排方核查的 mattpocock v1.3.2（2026-10-29 18:27:41，北京时间）剥开为 `d1478fcb140db0b93c0c8df17bcfd311844749d0`，HEAD 在后；impeccable skill-v4.8.2 剥开为 `035c8f319edd019936525a062fe99e83ca8d12c6`，之后仍有受管路径同步，cli-v4.8.2／engine-v0.1.22／预发布 loop-v0.1.0 不是 pin 单位。ui-ux-pro-max Latest Release v2.15.0（2026-08-13，`a38d04c3d5c298c851dbe5e6ee1965ee3de42cb5`）已落后当前 pin 71 提交、落后 HEAD 82 提交；v2.9.0（2026-06-27）更旧。ponytail v5.3.3（2026-10-29 11:11:08，北京时间）指向 `7801d061243d7b753bad0e0b3c057cd250b11755`，HEAD 还有后续文档提交。i-have-adhd v0.4.1 与 pin／HEAD 相同。
6. `CHANGELOG.zh.md:461` 的 v1.0.15 impeccable 本地补丁早于 #197。按已核实背景，live-browser.js 此后只在 #197 晋升更新，当前快照按干净上游 pin 对待；不把旧补丁当本轮重打补丁授权。实现轮审查新 HEAD 的 live-poll 文案、已删除模块注释、Svelte reset 范围、Windows 下载地址校验与暂存文件并发问题；若仍在且上游未修，列开放问题等用户决定，不本地修补镜像。
7. 晋升按仓库事务，不是跨六仓库的总事务。每次保留真实结果；中途失败停止，不把部分升级称为最终集合；恢复只沿既有保留目录与独立授权，不清理未知内容。

对照后未发现必须改契约／schema／PRD／ADR 的开放问题。以上 layout／license／历史问题是实现轮的条件停止门，不是已发现的分歧；本轮未声称完成全部上游 diff／许可证审查。后续若出现分歧，记为开放问题并停止扩展范围，不把合同调整偷偷并入本 PR。

### 需要 640 选择的项

| 项目 | 选项 | 推荐与理由 |
|---|---|---|
| 目标版本口径 | A：各自主线 HEAD；B：最新 tag／Release | 推荐 A，与 #197 和 rc.4 延后项定义一致；若选 B，需先另行明确口径，部分 Release 已落后当前 pin，不能直接回退 |
| shadcn／ponytail 子路径无变化 | A：仍锁仓库 HEAD；B：保留旧 revision | 推荐 A，保持“6 个仓库都是核查日主线”的一致定义，Ponytail live revision 断言随之更新；B 会成为需说明的例外 |
| mattpocock 新 Skill | A：本 PR 不登记；B：另开产品／catalog 决策 PR，经用户决定后登记 | 推荐 A，本项只重锁已有 19 个；B 不并入本 PR，不借上游新增扩大范围 |

这些是待选择项，不冒充已经得到新的实现批准；本轮只记录推荐，不执行晋升。

## 后续实现计划与预期将改的文件

以下都是后续预期，不是本轮已改。先完成待选择项与适用 Gate，再逐仓库审查当前 pin→目标 SHA 的受管子路径、完整目录与许可证；按上表逐仓库调用官方命令，复核每次候选验证／事务结果；最后完成全集合验证、隔离安装、相关测试、维护判断及独立评审。i-have-adhd 可用同 SHA 复验晋升，最终 revision 与载荷仍应不变。

命令模板（后续轮次，仓库根执行；本轮只运行过 --help）：

```sh
python3 -B sbtd-workflow-onboard/scripts/onboard.py promote-external-skills-stable --repository <id> --revision <完整40位SHA> --stable-set 2026-11-11.1 --yes --json
```

| 相对仓库路径 | 后续预期 |
|---|---|
| `sbtd-workflow-onboard/assets/external-skills/stable/MANIFEST.json` | 官方命令更新五个已移动 revision、stableSet／实际 promotedAt、受影响 treeSha256；i-have-adhd revision 不变 |
| `sbtd-workflow-onboard/assets/external-skills/stable/skills/impeccable/**`、`sbtd-workflow-onboard/assets/external-skills/stable/skills/ui-ux-pro-max/**` | 预计有快照内容变化；包括受管子树自带脚本／数据／测试，均按上游原样生成，不手改 |
| `sbtd-workflow-onboard/assets/external-skills/stable/skills/grilling/SKILL.md`、`sbtd-workflow-onboard/assets/external-skills/stable/skills/codebase-design/DESIGN-IT-TWICE.md` | mattpocock 预计变化路径；实际文件以已审查目标的官方晋升结果为准，不据此预设新增 Skill |
| `sbtd-workflow-onboard/assets/external-skills/stable/skills/**` 的其余已登记子树 | 整组流程会复制与验证；当前预计 shadcn、ponytail 四项、i-have-adhd 及 mattpocock 其余 9 项无内容 diff；有额外 diff 先查明来源 |
| `sbtd-workflow-onboard/assets/external-skills/stable/licenses/**`、`sbtd-workflow-onboard/assets/external-skills/stable/THIRD_PARTY_NOTICES.md` | 必要时同步许可证／归属；既有仓库命令会复制 license，但只在首次登记自动 upsert notices。当前不新增仓库，预计 notices 不变；如需改 source／许可合同则停止另行决策，不手修镜像绕过 |
| `tests/test_onboard_ponytail_integration.py` | live stableSet、实际 promotedAt、PONYTAIL_REVISION 跟新集合；保留模拟夹具 PONYTAIL_STABLE_SET=2026-08-27.1 |
| `tests/test_onboard_i_have_adhd.py` | 已复核：revision 和两个摘要目标不变，预计无需编辑；作为回归入口，不机械改常量 |
| `tests/test_onboard_external_skills.py` | 现有全量摘要／离线安装／拒绝与恢复用例为验证入口，预计无需编辑；仅有真实行为覆盖缺口才另列最小测试调整，不修改 digest 算法 |
| `CHANGELOG.md`、`CHANGELOG.zh.md` | 后续验证后，在 rc.5 未发布 Changed／变更各追加对应条目；旧条目及 rc.4／rc.3 历史不改 |
| `README.md`、`README.zh.md`、`prompts/automations/sbtd-workflow-tools-version-check.md` | 仅维护判断发现本项漂移才改；目前预计不改，不扩展监控／自动晋升权限 |
| `ai/tasks/v2.1.0-rc.5-external-skills-repin/task.md`、`ai/tasks/index.md` | 本任务持续记录真实轮次与证据；index 仅正式生成器维护 |

## 验收标准（后续实现轮，尚未执行）

1. 6 个仓库 pin 与上表完整目标 SHA 一致，i-have-adhd 保持原 SHA；stableSet 更新为经确认的新编号，promotedAt 为官方命令实际产出。
2. 19 个 Skill 的 treeSha256 与完整快照原始字节一致；采用安装器自己的 `stable_external_skill_source()` 做全集合校验，不使用第二套摘要算法。
3. 所有晋升只经官方 `promote-external-skills-stable`；每个仓库整组、候选全集验证后事务替换；快照保持上游原样，不手改、不打本地补丁、不改晋升器。
4. 隔离 HOME／目标 Skill 根，显式 `--source stable` 安装 19/19，结果为 committed、全部 sourceUsed 为 stable，安装后内容与新 manifest 一致，不访问本机生效路径。
5. 必要的 live pin 测试调整后相关测试通过，Ponytail 模拟 stableSet 保持；ADHD 未变的 revision／摘要不机械更新。许可证内容若变须审查并同步，归属完整。
6. 未登记新 Skill 不进入 catalog；总集合仍为 19，原 repo／subpath 合同保持。若 subpath／license 布局变化导致晋升拒绝，停止等用户决定，不绕过晋升器。
7. graft 0.28.0 文件字节不变；caveman pin、ENTRYPOINT 监控表、宿主／CLI pin、契约、schema、PRD、ADR、旧任务不改；双语 CHANGELOG 只追加本项条目。
8. 独立安全评审与适用 strict Gate 完成后才能称实现完成；本地测试、CI、合入与发布分别记录，不以本轮记录校验代替它们。

## 计划中的测试证据

本轮尚未执行晋升或实现测试，下表全部为后续计划，不沿用 #197 的历史通过结论。

| 范围 | 计划证据／映射 |
|---|---|
| 晋升完整性与安全边界 | 每次官方命令的 status、promotedSkills、完整候选验证及事务结果；最终 manifest 六 pin／19 treeSha256／许可证全集核对；复用 stable_external_skill_source() |
| 离线 strict-stable 19/19 | `tests/test_onboard_external_skills.py` 的 test_complete_vendored_stable_set_installs_without_network；另作隔离真实 CLI 安装，明确 HOME／目标根隔离，验证 committed 与 19 项完整性，不把 mock clone 当上游证据 |
| digest／拒绝／恢复 | 同文件 test_every_stable_skill_matches_its_manifest_digest、raw-byte checkout、缓存排除、source／license containment、失败恢复相关用例 |
| Ponytail | `tests/test_onboard_ponytail_integration.py`：live pin／集合日期、模拟晋升、注册／拒绝、provider 冲突边界；revision 改而子树不变仍需回归 |
| ADHD | `tests/test_onboard_i_have_adhd.py`：原 revision／SKILL.md／license 摘要与 required membership 保留 |
| 上游受管脚本 | 新 impeccable、ui-ux-pro-max 受管子树可独立运行子集；仓库根开发测试只在完整上游 checkout 跑，不能把缺根资源的 M15 环境不匹配伪装为产品通过或失败 |
| 全量与维护范围 | 先三模块定向回归，再按实际快照 diff 与仓库既有 CI 选择必要全量／相关子集；README×2／automation prompt／CHANGELOG×2 维护判断、保护文件字节检查；保留真实失败与平台缺口 |

后续定向命令：

```sh
python3 -B -m unittest tests.test_onboard_external_skills tests.test_onboard_ponytail_integration tests.test_onboard_i_have_adhd
```

隔离安装沿 `install-external-skills --all --source stable --global-skills-dir <隔离目标> --yes --json`，同时隔离 HOME，不使用正常 init／reset 改本机。正式实现报告需原生/raw 与同 stem 中文汇总，绑定当轮真实 SHA／worktree／环境；本轮不生成实现报告。

## Strict Book Gate Plan

实现尚未开始改生产代码，本轮以记录和计划为主。计划不等于执行，自审不等于独立批准。

| Gate | 客观触发条件／阶段 | 本轮状态与后续动作 |
|---|---|---|
| DDD | 完整 grill 或新增领域边界，需求稳定前 | not-needed：未完整调用 grill-with-docs，沿用 #197 和现有晋升定义；后续有领域分歧先停 |
| DDIA | 新 schema／迁移／共享状态／恢复设计，设计稳定前 | not-needed：本轮不设计新机制，只核对既有 manifest 与单仓库事务；若需要改持久合同则停止扩展、单独决策 |
| Legacy safety | 既有高风险行为／上游脚本变化，首次生产变更前 | pending：实现轮先审查差异、许可证及旧 impeccable 问题，建立现有安装／拒绝／恢复安全网 |
| Refactoring／ponytail | strict 首次生产编辑前 | pending：实现轮审查最小变更；vendored 子树不重构、不手改，不引入新抽象 |
| BDD／TDD | 用户可见行为或高风险回归覆盖缺口，实施前 | planned：沿既有安装／事务场景与上述测试；本轮只计划，未新增场景或测试，不为 pin 常量复制新测试 |
| Project validation | 本轮记录与后续实现各自的校验 | 本轮运行指定工作流测试、index 生成／预览及文字／范围检查；晋升、摘要、strict-stable 19/19 与实现回归 pending |
| 独立安全评审 | 第三方脚本、安装载荷与许可证变化，合入前 | pending：后续独立人工或获准 reviewer；本轮不调用子代理 |
| Release readiness | 分发快照／安装行为受影响，测试门后、完成／发布前 | pending：本轮不是实现完成或发布就绪 |
| CI／合入 | 后续实现 PR 的最终提交 | pending：本轮不提交、不推送、不开 PR，旧 HEAD 不证明未来变更 |

## 验证证据

Evidence Source：developer-local；Source Revision：dirty（新增任务记录）；Evidence Publication：local-only；Environment Alignment：not-needed（本轮不部署）。基准 SHA 与分支见上文；Linux x64。rtk：skipped-for-report，按本轮明确命令使用 native 输出，不以缓存替代执行。本节是本地证据表，不是 CI 或正式 PR-head 报告。

已执行定义／manifest／catalog 19 条／测试断言／晋升源码与帮助的只读核对。目标 task 不存在，父路径与 index 无链接，index 已跟踪、两个目标均无 ignore 匹配。已用 write 亲手建立本 task。使用会话内 todo 清单，未调用 task 状态写 API、子代理或 find，未运行 Git 写命令；仓库持久化只允许本 task 与生成式 index。

| 命令／检查 | 实际结果 | 退出码 |
|---|---|---|
| `git status --short --branch`、`git rev-parse --show-toplevel HEAD` | 起始干净；分支与基准 SHA 匹配，根已核对但不在共享记录写本机路径 | 0 |
| `namei -l`（两个目标路径）、`git ls-files --stage --`、`git check-ignore -v --no-index --` | 父路径无链接，目标新目录尚不存在；index 为普通文件 100644；无 ignore 匹配 | 1（新目录不存在）／0／1（无匹配） |
| `TZ=Asia/Shanghai date --iso-8601=seconds` | 开始写记录时为 2026-11-12T00:05:01+08:00，用于 created_at／updated_at 与 started 事件 | 0 |
| `python3 -B sbtd-workflow-onboard/scripts/onboard.py promote-external-skills-stable --help` | 成功列出 repository／完整 SHA／stable-set／yes 及注册限定参数；只读 help，没有执行晋升 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); Path('ai/tasks/index.md').write_bytes(a); print('INDEX_REGEN', 'changed=%s' % (b!=a), 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_REGEN changed=True rows=84`；83→84，只新增本任务一行；既有“旧格式事件，不追溯”提示保留 | 0 |
| `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'sbtd-workflow-onboard/scripts'); from sbtd_task_state import TaskStore; s=TaskStore(Path.cwd(), read_only=True); r=s._catalog(); b,a=s._index_candidate(r,r); print('INDEX_PREVIEW_SAME', Path('ai/tasks/index.md').read_bytes()==a, 'rows=%d' % len(s._index_rows(r)))"` | `INDEX_PREVIEW_SAME True rows=84`；逐字节一致，既有旧格式提示不是失败 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts` | 99 项通过，失败 0、跳过 0；`OK`，43.675 秒 | 0 |
| `git diff --check`、`git status --short --untracked-files=all`、`git diff --stat`、`git diff -- ai/tasks/index.md` | 空白检查无输出；只有 index 修改与本 task 未跟踪；tracked stat 为 index 一行新增，diff 证实只加本任务。未跟踪 task 不进入普通 diff --stat，未为此修改 Git index | 0 |
| 专用 grep：新写内容的本机路径、禁用归因措辞、非“契约”目标用字 | 新 task 无匹配；不将禁用字面量写入仓库；index 新增行仅任务 id 与相对链接 | 工具成功，无 shell 退出码 |

本轮跳过 stable 晋升、实现测试、真实安装、上游完整测试、全仓测试、运行时／前端 lint／build 与 CI：只改记录，尚未获得后续实现轮执行。BDD：skipped（只列计划，无场景文件变化）；Cross-repo context：not-needed；API Contract：not-needed（未改 API，已核对晋升契约）；Mock Strategy：none（本轮不新增 mock）。Final Test Report／Run Summary MD：not-needed（仅本地记录验证，不生成正式报告）。独立安全评审、CI、合入仍待后续；新 HEAD 的完整 diff／许可审查与旧 impeccable 问题复核仍待实现轮，不能据本轮计划称风险已消除。

Final Full Rerun：passed（仅本轮指定的 99 项工作流测试，不是安装／运行时全量）；Targeted Rerun：not-needed。证据回填后只复查新文字与空白；最终计数 edit 仅补模型表和推算说明，不再运行工具，不把计数回填称为重新验证。实际改动仅本 task 与正式生成的 index；未改生产文件、快照、测试、CHANGELOG、catalog、契约或旧任务。

## 第 2 轮晋升前审查

- 本轮在 `2026-11-12T00:16:54+08:00` 对六仓库逐一执行 `git ls-remote <manifest URL> refs/heads/main`，以 `gh api repos/<owner>/<repo>/commits/<SHA>` 取得旧／新 commit 的 author 与 committer 时间；六个目标均与第 1 轮计划相同，两种提交时间也分别相同。正式晋升前还会立即复测，若变化先重审而非静默换 pin。
- 从 GitHub codeload 按完整 SHA 获取 archive，保留全仓目录清单；仅在隔离证据目录展开全部受管子树及声明的许可证，逐 Skill 用 `diff -ru <当前 stablePath> <上游 sourceSubpath>` 比较原始文件。19 项路径均存在，未遇到受管链接／特殊文件、名称或许可证路径迁移。mattpocock 仅 grilling 与 codebase-design 各一处 fresh-context 文案变更；其余 9 项不变。impeccable 主要为 4.8.2 文档、launcher 校验／诊断及 live browser；ui-ux-pro-max 为 RTL 搜索、IME 指引、Apple Native style、Nuxt UI 4.12.0 数据与测试。shadcn、ponytail 四项及 ADHD 内容均无 diff。
- 七份声明文件（六仓 LICENSE，另含 impeccable NOTICE.md）与现有副本逐字节一致；Apache-2.0／MIT 条款、保留版权及 NOTICE 义务无新增差异，不需修改 source 合同或第三方归属。未登记的 mattpocock Skill 不进入受管复制集合。
- 第 1 轮记录的 impeccable `scripts/VERSION` 为编排方观察；本轮在相同目标 `c1e0e5492fbb524f5df84d635ecfae7dc438ec45` 实测为 `0.1.22`，旧 pin 为 `0.1.18`，不改写第 1 轮历史。

### impeccable 旧问题复核与开放问题

以下是目标 SHA 的静态源码证据，不冒充 Windows 或完整浏览器运行。当前副本仍按干净上游 pin 对待；保留上游原样，不重打 v1.0.15 本地补丁。

| 旧问题 | 本轮结论与源码证据 |
|---|---|
| 用户可见 live-poll 文案 | 再现：`scripts/live-browser.js:8025,10617,11208` 仍提示运行 `live-poll.mjs`，不是 `impeccable live-poll`。 |
| 已删除模块维护注释 | 再现：`live-browser.js:106,119,125,157,215,1731` 仍引用旧 vocabulary／ui-surfaces／live-server／live-accept／insert-ui 模块；完整 archive 目录清单未见这些运行模块，仅有同名 live-accept 测试文件。 |
| Svelte reset 范围 | 再现：`resetSvelteComponentSession` 的 6465 行调用无参 `clearHandled()`；`live-browser-session.js` 无 id 时删除整个 handled key，非仅当前会话。 |
| Windows 下载基址校验 | 再现：`impeccable.cmd:128,155,163,194` 将 `IMPECCABLE_DOWNLOAD_BASE` 直接展开为 URL 并传入 curl，未见旧补丁的 delayed-expansion URL 字符校验。静态风险保留，未在 Windows 复现利用。 |
| 下载／摘要暂存并发 | 原固定暂存名模式未再现：`impeccable.cmd:133-174` 用时间＋双 RANDOM 命名目录，mkdir 原子占用并冲突重试；载荷与 hash.txt 在本次独占目录内。POSIX 使用 `.impeccable.part.$$`；不把静态审查称为 Windows 并发实测。 |

以上四类再现问题保持开放，供独立安全评审与上游处理；不是绕过晋升器或修镜像的授权。

### 第 2 轮适用 Gate（晋升前）

- Legacy Change Safety Review：`characterized`，normal。安装器 `load_external_stable_manifest()` 与逐项 `stable_external_skill_source()` 对旧集合实跑，输出 `BASELINE_STABLE_VALID 19 2026-10-28.1 2026-10-28`，退出 0。保留离线 stable、raw-byte 摘要、路径 containment、整组事务及失败保留／恢复；现有三模块测试和隔离真实安装是安全网，不新增 seam。
- Refactoring Review：`proceed`，normal，`no refactor needed`。只用已有晋升接口；不改晋升器、摘要算法、source、catalog，不重构第三方原样载荷。
- Ponytail：复用现有命令及验证入口，无新生产抽象。BDD／TDD：沿用既有安装／拒绝／恢复场景，本项无安装行为设计变化，不增场景文件或为 pin 复制测试；未声称执行新的 red-green 回路。
- DDD／DDIA：not-needed，未完整 grill，无新增领域／持久化设计；不把上游镜像内部数据更新当成本仓 schema 调整授权。独立安全评审、Release readiness、CI／合入保持待验证。

## 本轮锁定结果（第 2 轮／PR 事实表）

以下为本轮实测，供 PR 正文直接引用。时间均为北京时间（UTC+08:00）；表中提交时间同时是 GitHub commit 的 author／committer 时间。本轮目标与第 1 轮计划全部一致，无静默换 SHA。第二次 HEAD 核查紧接正式晋升之前，六个 `ls-remote` 均退出 0；不是 tag／Latest Release 选择。

| 仓库 | 完整旧 SHA → 完整新 SHA | 旧提交时间 → 新提交时间 | 晋升前 HEAD 复测时间 | 受管内容／treeSha256 |
|---|---|---|---|---|
| mattpocock-skills | `59db609eb1e18aaf59b63284d0e52255aff0c63c` → `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` | `2026-10-27T15:44:12+08:00` → `2026-10-31T22:23:30+08:00` | `2026-11-12T00:20:39+08:00` | grilling、codebase-design 内容及摘要变化；其余 9 项不变 |
| impeccable | `3e3a9179e01a60265000ce239c0a99803ec1e60d` → `c1e0e5492fbb524f5df84d635ecfae7dc438ec45` | `2026-10-28T14:05:26+08:00` → `2026-11-11T11:56:37+08:00` | `2026-11-12T00:20:41+08:00` | 1 项内容及摘要变化 |
| ui-ux-pro-max-skill | `28b3b8dee8c976df4fa3e94aed4e092ad43fcb03` → `6ae86f61f520d6ca229d2f40e070410638c908c5` | `2026-10-26T18:07:27+08:00` → `2026-11-10T21:03:57+08:00` | `2026-11-12T00:20:45+08:00` | 1 项内容及摘要变化 |
| shadcn-ui | `96da9cc7f1aa10580a3741664e2a77c721206c00` → `dd41d19e2f80ff6891951f7ced74c2c9a650b065` | `2026-10-27T20:30:19+08:00` → `2026-11-11T17:04:13+08:00` | `2026-11-12T00:20:47+08:00` | 内容与摘要不变，仅仓库 revision 变化 |
| ponytail | `09c434ab73ca43761c5d8b0c5d341926c2fba710` → `96608e078b2d5ea607c5c3b8b5a54d1c1fba6846` | `2026-10-18T09:55:14+08:00` → `2026-10-29T19:59:31+08:00` | `2026-11-12T00:20:50+08:00` | 四项内容与摘要不变，仅仓库 revision 变化 |
| i-have-adhd | `1ecea1993b7fce257ffbd686c070948b5e07eda6` → `1ecea1993b7fce257ffbd686c070948b5e07eda6` | `2026-10-12T00:03:54+08:00` → `2026-10-12T00:03:54+08:00` | `2026-11-12T00:20:53+08:00` | revision、载荷及摘要均不变，同 SHA 官方复验晋升 |

最终顶层 `stableSet=2026-11-11.1`、`promotedAt=2026-11-12`。编号沿第 1 轮核查日；执行环境时区为 +08:00，promotedAt 由官方命令按实际当日生成，没有手改。集合仍为六仓库／19 项；所有 repo URL、sourceSubpath、stablePath、license／licenseFiles 元数据保持，只有五个仓库 revision、四个 Skill treeSha256 及顶层日期字段变化。七份许可证／NOTICE 与 THIRD_PARTY_NOTICES.md 未变。

### shadcn／ponytail 逐字节证据与测试维护

以完整 SHA 的 codeload archive 受管子树为上游证据，不使用 mock clone。对全部 19 项执行 `diff -rq <晋升后 stablePath> <锁定 SHA 的上游 sourceSubpath>`，退出码全部为 0；该命令直接比较文件原始字节及完整目录，不做换行规范化。重点五项如下（stable 根均为 `sbtd-workflow-onboard/assets/external-skills/stable`）：

| stable 相对子树 | 上游相对子树 | 比较结果 |
|---|---|---|
| `skills/shadcn` | shadcn-ui：`skills/shadcn` | `diff -rq` 退出 0，无输出 |
| `skills/ponytail` | ponytail：`skills/ponytail` | `diff -rq` 退出 0，无输出 |
| `skills/ponytail-review` | ponytail：`skills/ponytail-review` | `diff -rq` 退出 0，无输出 |
| `skills/ponytail-audit` | ponytail：`skills/ponytail-audit` | `diff -rq` 退出 0，无输出 |
| `skills/ponytail-debt` | ponytail：`skills/ponytail-debt` | `diff -rq` 退出 0，无输出 |

另对上述五项、ADHD 子树、licenses 与 THIRD_PARTY_NOTICES.md 执行 `git diff --exit-code -- <各路径>`，退出 0、无输出，证明相对旧集合也无内容变化。结合 manifest diff，shadcn／ponytail 仅更新 MANIFEST 中的 revision（以及集合共享的 stableSet／promotedAt），未修改它们的快照或摘要。完整 19 项 digest 与比较结果保留在 `reports/r2-integrity-install.json`。

`tests/test_onboard_ponytail_integration.py` 只改三个 live 值：`PONYTAIL_REVISION` 跟随上表、live stableSet 为 `2026-11-11.1`、live promotedAt 为 `2026-11-12`。修改 revision 断言的原因就是第 2 项投票结果：受管子路径无内容变化仍锁仓库 HEAD，live 断言含 revision，故必须跟随新 revision。模拟晋升夹具 `PONYTAIL_STABLE_SET = "2026-08-27.1"` 保持不变；ADHD revision 与两个摘要常量不变。`tests/test_onboard_external_skills.py` 无编辑，不改 digest 算法、不删除或削弱无关测试。

## 第 2 轮本地验证

Evidence Source：developer-local；Source Revision：dirty；Evidence Publication：local-only。基准 SHA 为 `57c2baa4b738a63fc0fcf09e8b71e897ee53e379`，分支 `chore/rc5-external-skills-repin`，Linux x64、Python 3.13.5、Node v22.20.0。rtk：skipped-for-report，使用 native 命令。下表只记本轮执行，不继承第 1 轮通过结论。晋升、安装、测试和补充诊断的原生 stdout／stderr、退出码、精确时间及命令参数保存在本任务 ignored `reports/r2-*.json`，各有同 stem 中文 `.md`；本地原始报告不自动发布，非未来 PR-head／CI 证据。

官方晋升每行均执行以下原生命令，`<id>`／`<SHA>` 对应上表；没有传 `--license`／`--license-file`，六次均 `registration=false`、`prunedStableSkills=[]`。源码在每次替换前执行完整候选集合元数据及 19 项 `stable_external_skill_source()` 验证；成功 JSON 是真实宿主调用结果。

```sh
python3 -B sbtd-workflow-onboard/scripts/onboard.py promote-external-skills-stable --repository <id> --revision <SHA> --stable-set 2026-11-11.1 --yes --json
```

| 命令／证据 | 实际结果 | 退出码 |
|---|---|---|
| `TZ=Asia/Shanghai date --iso-8601=seconds`；六仓 `git ls-remote`；`gh api` 旧／新 commits 与 compare | 首次核查 00:16:54；晋升前复测精确到秒见上表，全部与计划一致；12 个 commit 请求的 author／committer 时间完成北京时间换算 | 全部 0 |
| 官方晋升 mattpocock-skills；`reports/r2-promote-mattpocock-skills.json` | promoted，11 项；3.543 秒 | 0 |
| 官方晋升 impeccable；`reports/r2-promote-impeccable.json` | promoted，1 项；6.976 秒 | 0 |
| 官方晋升 ui-ux-pro-max-skill；`reports/r2-promote-ui-ux-pro-max-skill.json` | promoted，1 项；4.209 秒 | 0 |
| 官方晋升 shadcn-ui；`reports/r2-promote-shadcn-ui.json` | promoted，1 项；7.040 秒 | 0 |
| 官方晋升 ponytail；`reports/r2-promote-ponytail.json` | promoted，4 项；5.964 秒 | 0 |
| 官方晋升 i-have-adhd；`reports/r2-promote-i-have-adhd.json` | promoted，1 项；4.190 秒 | 0 |
| `load_external_stable_manifest()`＋逐项 `stable_external_skill_source()`；19 次 `diff -rq`；许可证原始字节比较 | 六 pin 正确；19/19 摘要正确且与上游原始字节一致；四摘要变化、十五不变；七份许可证／NOTICE 未变，集合没有新增 Skill | 0 |
| `install-external-skills --all --source stable --global-skills-dir <隔离目标> --yes --json`；`reports/r2-isolated-install.json` | 同时隔离 HOME／USERPROFILE／XDG 目录，未调用 init／reset；真实 CLI transaction=committed，19/19 phase=commit、sourceUsed=stable，安装后 19 个原生摘要及 revision／stableSet 均匹配 manifest；1.375 秒 | 0 |
| `python3 -B -m unittest tests.test_onboard_external_skills tests.test_onboard_ponytail_integration tests.test_onboard_i_have_adhd`；`reports/r2-external-tests.json` | 67 项通过，失败 0、跳过 0；47.011 秒 | 0 |
| `python3 -B -m unittest tests.test_sbtd_task_state tests.test_workflow_contracts`；`reports/r2-workflow-tests.json` | 99 项通过，失败 0、跳过 0；39.559 秒 | 0 |
| `python3 -B -m unittest tests.test_onboard_arguments tests.test_onboard_contracts tests.test_onboard_multi_projects tests.test_onboard_windows_platform`；`reports/r2-onboard-adjacent-tests.json` | 373 项，370 通过、3 跳过、失败 0；87.685 秒。原生输出未逐项列 skip 名；源码包含大小写不敏感文件系统及 Windows batch shim 平台条件，不冒充 Windows 原生通过 | 0 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B <stable>/skills/ui-ux-pro-max/scripts/tests/test_rtl_support.py`；`reports/r2-upstream-rtl.json` | 12 项通过；含真实 search.py CLI，0.371 秒 | 0 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B <stable>/skills/ui-ux-pro-max/scripts/tests/test_ime_composition.py`；`reports/r2-upstream-ime.json` | 3 项中 2 通过、1 跳过；0.047 秒。跳过上游根文档同步检查，因为安装子树不携带根 docs；CSV 中实际 JavaScript 的 IME／Enter 行为已执行，不是原生 OS IME 或 Safari 证明 | 0 |
| `sh -n <stable>/skills/impeccable/scripts/impeccable`；`node --check <stable>/skills/impeccable/scripts/live-browser.js` | 均通过；只证明语法，不证明 engine 下载、浏览器 UI 或 Windows 运行 | 各 0 |
| `git diff --check` | 失败：只命中上游 impeccable.cmd 的 CRLF 行。新文件 354 个 LF 全为 CRLF，旧文件 278 个 LF 也全为 CRLF；与上游字节完全一致，换行前空格／Tab 数为 0。未改镜像或换行消除检查结果 | 2 |
| `git -c core.whitespace=cr-at-eol diff --check`；`reports/r2-crlf-diagnostic.json` | 通过；仅作 CRLF 原因诊断，不替代前一行失败、不写 Git 配置 | 0 |
| `git status --short --untracked-files=all`、`git diff --stat`、manifest／测试／CHANGELOG 的 `git diff` | 42 个 tracked 修改、2 个上游原样新测试；index 未变；测试只有三个 live 值调整，CHANGELOG 双语各追加一条；未 staging | 0 |
| 正式 TaskStore 生成器写入＋只读预览（与第 1 轮两条 `python3 -B -c` 命令完全相同）；`reports/r2-index-regen.json`／`r2-index-preview.json` | `INDEX_REGEN changed=False rows=84`；`INDEX_PREVIEW_SAME True rows=84`，既有旧格式事件提示保留。未手改 index | 各 0 |
| 一次性范围验证脚本，原始 `reports/r2-scope-check.json` | 检查器首次错误地在整份中文 CHANGELOG 匹配通用前缀，连历史 #197 一并计入，断言失败；不是产品或历史被改。只修证据脚本为检查新增 diff 行，原失败报告保留 | 1 |
| 修正范围验证；`reports/r2-scope-check-corrected.json` | 42 tracked 修改＋2 个上游新测试，staged=0；白名单以外所有 tracked 文件不变。删除双语新增条目后与原文件逐字节一致；测试文件仅三个已批准 live 值变化，其余字节一致；task 历史仅 updated_at 被替换，其余原文保留 | 0 |
| 对新增 diff 行及两个上游新文件使用专用 grep 检查本机路径、禁用归因措辞与目标用字 | 本轮手写文字无匹配；全体新增文字只命中 impeccable/reference/hooks.md 三行上游通用 HOME 示例，不是本机路径，不修改原样镜像消除匹配。禁止归因措辞与非契约目标用字均无匹配 | 工具成功，无 shell 退出码 |

隔离安装附带 postCheck 会报告隔离根缺少 bundled Skills／caveman，以及未安装 Java／未检查 Maestro；本项只安装 external Skills，不将它宣称为完整宿主初始化通过，也不按这些提示扩大安装权限。19 项 external transaction 与内容验收均通过。

### 第 2 轮维护判断与剩余 Gate

- README×2 仍将精确 pin 指向 MANIFEST；automation 的版本监控与独立晋升权限边界无文字漂移，三文件不改。双语 CHANGELOG 只在现有唯一 rc.5 Changed／变更尾部新增一条，无 PR 号；历史条目保持。
- Ponytail-review／Code Readability Review：本仓手写实现无新增抽象，测试仅三值更新，可读性与已有形式一致；镜像不做本地删改。新增两个上游测试是完整目录复制结果，不是本轮另写测试。
- Release Readiness Review：`blocked`。分发载荷与外部 engine 相关风险存在；集合摘要、真实隔离安装、安装拒绝／恢复回归通过，但四类 impeccable 旧问题及原生空白检查失败仍开放，独立安全评审、跨平台 CI、合入未完成。容量／队列／服务监控不适用；恢复仍沿既有事务保留目录及独立授权，不运行回滚或未知目录清理。
- BDD：traceable（沿既有稳定安装／拒绝／恢复测试，不改持久化场景）；语言不适用。Cross-repo context：complete（六仓目标与完整受管子树已核查）；API Contract：not-needed；Mock Strategy：既有单测 fixture 与真实上游／真实隔离 CLI 分开，不新增 mock。
- Final Test Report／Run Summary MD：generated（本地 raw＋同 stem 中文）；Targeted Rerun：not-needed，测试没有失败；Final Full Rerun：passed 仅指上述计划 unittest 范围，共 554 项、550 通过、4 跳过，非全仓或 CI。原生 `git diff --check` 仍 failed，不能称全部验证通过。
- 跳过全仓其余分片、完整上游开发测试、完整浏览器／Windows 原生运行及 engine 下载：本轮执行限定回归和可独立运行子集，无正常宿主安装或额外依赖安装授权。未部署、未发布、未提交；status 保持 checking、completed_at=null。

修改文件范围：`MANIFEST.json`；grilling／codebase-design 两处上游文案；impeccable 的 SKILL／reference／scripts；ui-ux-pro-max 的 SKILL／data／references／scripts（含两个上游原样新测试 `test_ime_composition.py` 111 行、`test_rtl_support.py` 166 行）；本仓 Ponytail 测试三值；双语 CHANGELOG；本 task。42 个 tracked 修改之外的 2 个新文件不会进入未 staging 的 `git diff --stat`，不能遗漏。没有仓库内临时脚本；本轮辅助脚本与上游审查材料在独立本地证据位置，隔离安装临时目标已随本次拥有的 TemporaryDirectory 释放。未清理未知内容或恢复目录；未运行 Git 写命令，官方晋升器内部临时 clone／checkout 不涉及本工作树的索引或分支。

## 模型记录

| 轮次 | 模型 | 用途 | 模型调用 | 工具调用 |
|---|---|---|---|---|
| 第 1 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 只读核对、编写本任务、生成 index 与本地校验 | 14（推算） | 54（推算） |
| 第 2 轮 | `openai-codex/gpt-6-astra`（thinking high，主模型） | 六仓上游复测与审查、官方晋升、隔离安装、回归验证、双语 CHANGELOG 与本任务证据 | 45（推算） | 140（推算） |

计数方法：在 omp 会话日志中筛选 `role=assistant`、`provider=openai-codex`、`model=gpt-6-astra` 的消息计模型调用，同一记录内 `toolCall` 条目计工具调用。本轮只读 count.py 对 sessions 输出 `astra_assistant=12 astra_toolcalls=53 other_assistant={} model_usage={}`，退出码 0，未写仓库。统计后只有本次 edit 和一次纯文本收尾，因此模型调用按 A+2=12+2=14、工具调用按 T+1=53+1=54 推算。日志没有其他模型，不另列模型行；find 未列入本轮工具，调用为 0。本次 edit 为最后一次工具调用，仅回填模型表与推算说明；之前新文字 grep 无匹配、git diff --check 退出 0，之后不再运行工具，不把计数回填冒充重新测试。

第 2 轮计数：指定只读 count.py 对 sessions-r2 实际输出 `astra_assistant=43 astra_toolcalls=139 other_assistant={} model_usage={}`，退出 0，未写仓库。沿上文日志筛选方法，统计后只执行一次计数回填 edit 与一次纯文本收尾，故模型调用 A+2=43+2=45（推算），工具调用 T+1=139+1=140（推算）。没有其他模型，不另列；find 未列入本轮工具，调用为 0。本次 edit 是最后一次工具调用，仅增加本轮模型行及说明。计数前最终范围／手写文件空白检查退出 0，新增手写文字 grep 无匹配，20 对 raw／同 stem 中文报告核对通过；原生全范围 diff --check 的退出 2 与检查器首次退出 1 均保留，不把计数回填称为再次验证。

## 状态事件

| at | from | to | reason | evidence |
|---|---|---|---|---|
| 2026-11-12T00:05:01+08:00 | planned | checking | started：Lord 在合入 #213（合并提交 a2a3aa72281e9127de821f19fb5056ad76306d16，提交时间 2026-11-11T23:55:48+08:00）之后群内调度开始外部 skills 重新锁版本，本轮只写 task.md 及生成式 index，不开始实现 | 已核对分支、HEAD、路径安全、既有定义、manifest／catalog、测试断言、晋升源码与帮助；INDEX_REGEN changed=True rows=84，INDEX_PREVIEW_SAME True rows=84，指定 unittest 99 项通过，diff 空白与范围检查通过，新写文字 grep 无匹配；developer-local，非 CI，详见验证证据。 |
| 2026-11-12T00:15:48+08:00 | checking | checking | 按 640 2026-11-11 23:59 授权的群内投票结果，三项全票同意推荐（各 5 票同意、0 票反对；投票人 Lord、Reviewy、Researchy、CodeX、OMP；投票时间 2026-11-12 00:11 至 00:12 北京时间）：锁主线 HEAD、shadcn／ponytail 无内容变化仍升 revision、不登记 mattpocock 新 Skill；开始第 2 轮实现 | 起始 HEAD 57c2baa4b738a63fc0fcf09e8b71e897ee53e379，分支匹配，工作区干净；完整读取 task、官方晋升流程及 strict 方法，路径普通且报告目录已有 ignore 保护。 |
| 2026-11-12T00:27:58+08:00 | checking | checking | 第 2 轮完成六仓官方晋升、必要 live pin 测试维护、双语 CHANGELOG 追加及 index／范围核对；原生空白检查因上游 CRLF 失败，保留原始镜像并记录四类 impeccable 旧问题，不声称发布就绪 | 六次 promoted／退出 0；19/19 manifest 摘要及上游逐字节一致，strict-stable 隔离安装 19/19 committed；必跑 unittest 67＋99 通过，补充 373 项跳过 3，RTL 12 通过，IME 3 项跳过 1；index changed=False／84、preview=True／84；范围检查器误匹配历史的失败保留，修正后退出 0；手写文字 grep 无匹配；原生 diff --check 退出 2，CRLF 诊断退出 0。 |
