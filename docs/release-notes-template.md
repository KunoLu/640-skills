# Bilingual release / tag notes template · 双语发布／标签说明模板

In-repo human-readable copy of the **bilingual-release-notes** skill for this repository (`640-skills`). Cross-repo OMP work still uses the skill; keep facts aligned with that skill and with the canonical GitHub Release body for [`v2.0.2`](https://github.com/KunoLu/640-skills/releases/tag/v2.0.2).

本仓库内可读副本，对应 skill `bilingual-release-notes`。跨仓库 OMP 仍使用该 skill；事实须与 skill 及 [`v2.0.2`](https://github.com/KunoLu/640-skills/releases/tag/v2.0.2) Release 正文一致。

## Rules · 规则

| Topic · 主题 | Rule · 规则 |
|---|---|
| RC vs stable | Same template. RC → GitHub Release marked **prerelease**; tag like `vX.Y.Z-rc.N`.／同一模板。RC → GitHub Release 标为 **prerelease**；标签形如 `vX.Y.Z-rc.N`。 |
| Tag-only | Annotated tag with the **full** bilingual body below. Never lightweight. Never English-only.／仅打标签时：annotated tag 注解必须含下方**完整**双语正文。禁止 lightweight；禁止仅英文。 |
| Tag + GitHub Release | Full bilingual body on the **Release**. Annotated tag may be the same full text **or** a short bilingual pointer such as `See GitHub Release / 见 GitHub Release` (with one-line EN+ZH summary and full commit SHA).／同时发 Release 时：完整正文放在 **Release**；annotated tag 可以是全文，或短双语指针（含一行中英摘要与完整提交 SHA）。 |
| CHANGELOG | Keep each repo’s usual CHANGELOG convention; facts must match. Do **not** paste the full bilingual Release body into CHANGELOG.／CHANGELOG 按各仓库惯例更新，事实一致；**不要**把完整双语 Release 正文粘进 CHANGELOG。 |
| Skill vs this file | Cross-repo OMP still uses the skill. This file is the in-repo human-readable copy for `640-skills`.／跨仓库 OMP 仍用 skill；本文件是 `640-skills` 仓库内可读副本。 |

## Template · 模板

Copy and fill. Omit empty Added/Changed/Fixed/Removed (新增／变更／修复／移除) subsections. Prefer Keep-a-Changelog verbs.／复制后填写。省略空的小节。优先 Keep-a-Changelog 动词。

```markdown
## Release identity / 发布身份

- Annotated tag / 标注标签: `vX.Y.Z` (or `vX.Y.Z-rc.N`)
- Commit / 提交: `<full 40-char SHA>`
- Exact-commit CI / 精确提交 CI: <URL or "n/a" with reason>
- Native scope verified / 原生范围核验: <platforms, counts, pass/fail notes>

## English

### Added
### Changed
### Fixed
### Removed

(Omit empty subsections. Prefer Keep-a-Changelog verbs.)

## 简体中文

### 新增
### 变更
### 修复
### 移除

(与英文条目一一对应；事实与英文一致。)

## Deployment boundary / 部署边界

<What this publication does **not** do on existing hosts — in English, then the same in 简体中文. If none, say so in both languages.>

Full comparison / 完整对比: https://github.com/<owner>/<repo>/compare/<prev>...<tag>
```

### Short bilingual tag pointer (when Release has the full body) · 短双语标签指针（完整正文在 Release 时）

```text
vX.Y.Z: <one-line EN summary> / <一行中文摘要>

See GitHub Release for full EN+ZH notes. / 完整双语说明见 GitHub Release。
Commit: <full 40-char SHA>
```

## Example · 示例

See the published [`v2.0.2`](https://github.com/KunoLu/640-skills/releases/tag/v2.0.2) Release for a filled instance of this template (identity, English Changed/Fixed, 简体中文 变更／修复, deployment boundary, full comparison link).

已发布的 [`v2.0.2`](https://github.com/KunoLu/640-skills/releases/tag/v2.0.2) Release 是本模板的填好实例（发布身份、英文 Changed／Fixed、简体中文变更／修复、部署边界、完整对比链接）。

## Agent checklist · Agent 清单

1. Confirm tip SHA and previous tag.／确认 tip SHA 与上一标签。
2. Draft bilingual notes from the real diff / CHANGELOG — do not invent CI or counts.／按真实 diff／CHANGELOG 起草双语说明——不编造 CI 或计数。
3. Create annotated tag (full bilingual annotation if tag-only; full or short bilingual pointer if Release exists).／创建 annotated tag（仅标签用完整双语注解；有 Release 可用全文或短双语指针）。
4. If releasing: `gh release create` with the full body (prerelease flag for RC).／若发版：`gh release create` 使用完整正文（RC 加 prerelease）。
5. Paste tag, full SHA, and Release URL (if any) back to the requesting chat.／把标签、完整 SHA、Release URL（如有）回传请求方。
