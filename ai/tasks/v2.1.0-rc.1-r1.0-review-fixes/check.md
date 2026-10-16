# R1.0 review-fix check

未完整调用 grill-with-docs。三项修复的可观察语义已由 ADR 0001 第 166 行、PRD v0.2 第 1355 行与 PRD §10.2／AC-56 固定。本文件只记录已发生的证据，不把补录时间写成历史前置门通过时间。

## 补录边界

上一会话在 2026-10-16T14:54:10+08:00 写出 Book Gate 正文，但 TaskStore 缺 `markdown-it-py`，任务记录未落盘。本次只用已安装的 TaskStore 补记。状态事件的 `at` 是落盘时钟，不是工作发生时间。

## 实现与测试

- 修复提交：`11804fbb1f2130607c23df2a5fe5ae3cf5bd8af9`，AuthorDate `2026-10-16T15:05:16+08:00`。新 commit，未 amend。
- 红因：提交前 `python3 -B -m unittest discover -s sbtd-runtime/tests -v` 为 6 error，`KeyError: completion_gate`／`x-sbtd-release`／`Forbidden`。
- 提交后精确 SHA 复跑，raw 时间 `2026-10-16T15:05:59+08:00`：
  - `python3 -B -m unittest discover -s sbtd-runtime/tests -v`：41 tests，OK，exit 0。
  - `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts -v`：41 tests，OK，exit 0。
- raw 与同 stem 中文汇总：`reports/unit-report-sbtd-runtime-r1-contracts-2026_10_16-15_00_00.txt` 与 `.md`。该目录受 `/ai/tasks/**/reports` 保护，不入库。

## 独立复核

ContractReview 只读复核提交前工作树，五项检查均为 confirmed，无发现：

1. `completion_gate` 对照 ADR 0001 第 166 行。
2. `/api/v1/exports*` 的 rc.2 标注对照 PRD §15.0。
3. `components.responses.Forbidden` 覆盖 Host／Origin 与 CSRF，并被全部 28 个 operation 引用。
4. 三个新测试与 `sbtd-runtime/spec/r1.0-contract-scenarios.md` 的场景断言真实语义。
5. 当时 diff 只触及 capability-matrix、openapi、data-dictionary、场景与 golden 测试；未改 `contract_eval.py`、event schema、指标目录、golden、ADR、PRD。

该复核不覆盖随后写入的 `CHANGELOG.md`／`CHANGELOG.zh.md`。提交说明中的 “no findings on all five checks” 指这五项，不表示复核了 changelog。

## Book Gate

正文见 `task.md`。结论来自上一会话、契约编辑前写出的审查，本次补记不重跑 reviewer：

| Reviewer | 结果 |
|---|---|
| book-ddd-distilled-modeling | confirmed |
| book-ddia-data-design | confirmed |
| book-legacy-change-safety | not-needed。契约字段缺失，非既有运行时行为缺陷 |
| book-refactoring-pass | not-needed。未改 `contract_eval.py` |
| book-release-readiness | not-needed。无服务、作业、迁移或发布 |

## 未执行

- R1.2b 真实宿主 smoke 不在本任务；`smoke_status` 保持 `not-run`。
- 三平台 CI 不以本机 41／41 代替。
- rtk：skipped-for-report。ruff／ty：当时环境没有项目 CI 配置，未运行。
