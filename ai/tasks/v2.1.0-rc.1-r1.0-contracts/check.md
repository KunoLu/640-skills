# R1.0 check

未完整调用 grill-with-docs。PRD v0.2 与已接受 ADR 0001 已固定本包边界。DDD 与 DDIA 审查在 task.md，状态均为 confirmed。

## 适用门

| 项 | 结果 |
|---|---|
| book-ddd-distilled-modeling | confirmed |
| book-ddia-data-design | confirmed |
| book-legacy-change-safety | not-needed。不改既有生产行为 |
| book-refactoring-pass | not-needed。不编辑既有生产代码 |
| book-release-readiness | not-needed。无运行中的服务、作业、迁移或发布 |
| BDD | traceable。`sbtd-runtime/spec/r1.0-contract-scenarios.md`。源仓不生成 `.feature`。中文正文，英文 Given／When／Then |
| TDD | 先红后绿。红因是 `ModuleNotFoundError: No module named 'contract_eval'` |
| ponytail-review | Lean already. 契约文件是用户要求的交付物，不另拆框架 |
| 独立审查 | 授权与公开 API 草案触发只读审查；结论写入本文件后续小节 |

## 红绿

首次 `python3 -B -m unittest sbtd-runtime/tests/test_golden_contracts.py` 失败：`ModuleNotFoundError: No module named 'contract_eval'`。实现 `contract_eval.evaluate` 后同一消费者接口通过。

## 验证

- `python3 -B -m unittest tests.test_sbtd_runtime_r1_contracts tests.test_ci_selection`：40 tests，exit 0。
- `python3 -m compileall -q sbtd-runtime tests/test_sbtd_runtime_r1_contracts.py`：通过。
- 声明依赖解释器 `/home/box/.local/share/sbtd/venv/bin/python -B tests/run_ci.py --platform linux --list` 能发现 27 个 `sbtd_runtime_golden_contracts` 用例。系统解释器缺 `cryptography`，不能导入无关对账模块；这不是本包失败。
- ruff：当前解释器没有 ruff，skipped。
- rtk：skipped-for-report。原生命令直接运行。

本记录完成时工作树仍 dirty。精确 SHA 证据在提交后的复跑，不把 dirty 通过写成 PR head 证明。
