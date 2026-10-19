# Dashboard 设计规格：自有 Token 定义（D17）

> 状态：PR-1 交付（R2.0a 拆分后）。范围：OMP 风格单页骨架的视觉与设计规格。
> 锁定决定：D17（Q10-A）——仅参考 OMP 视觉语言自行实现，**零代码／零资源复制**，无许可证义务；OMP 许可证已核验为 MIT（grill-r1.md Q10），如需升级为 token／图标级复用须另行 ADR。
> 本文把每一个 OMP 参考点写成**我们自己的 token 定义**；token 值由本项目按 PRD v0.2 §12.3 自行确定，不取自 OMP 源码或资源。实现：`sbtd-runtime/dashboard/src/tokens.css`。

## 参考点 → 自有 token 映射

| OMP 视觉参考点（仅风格描述） | 自有 token | 定义值（本项目自定） | 依据 |
|---|---|---|---|
| 深色为主、可切浅色的双主题结构 | `:root` 默认深色 + `:root[data-theme="light"]`；`--sbtd-bg`、`--sbtd-bg-elevated`、`--sbtd-bg-inset` | 深色 `#14171c / #1b1f26 / #101318`；浅色 `#f5f7fa / #ffffff / #eceff3` | §12.3「OMP 风格的暗色主题与浅色主题；默认跟随系统，用户可切换并记忆」 |
| 克制的边框分隔而非重阴影 | `--sbtd-border`、`--sbtd-border-width` | `#2c333d`（深）／`#d4dbe3`（浅）；1px | §12.3 版式规则 |
| 圆角卡片、适中圆角控件 | `--sbtd-radius-panel`、`--sbtd-radius-control` | 10px／8px | 本项目自定 |
| 宽松留白、不挤压表格 | `--sbtd-space-page`、`--sbtd-space-gap`、`--sbtd-space-panel-padding` | 24px／16px／16px | §12.3「页面 padding 24px、Panel gap 16px 为起始建议」 |
| 正文可读字号、大号指标数值 | `--sbtd-font-size-body`、`--sbtd-font-size-secondary`、`--sbtd-font-size-title`、`--sbtd-font-size-metric` | 14px／12px／16px／28px | §12.3「正文／表格默认 14px 以上；指标数值 24–32px」 |
| 系统字体栈＋明确 CJK fallback | `--sbtd-font-family`、`--sbtd-font-mono` | 系统栈含 PingFang SC／Hiragino Sans GB／Microsoft YaHei／Noto Sans CJK SC/JP | §13.4、D16（离线 HTML 纯系统字体栈＋CJK fallback，不写本机字体路径） |
| 分段按钮式预置时间范围 | `.segmented` 控件样式（`--sbtd-radius-control`、`--sbtd-accent`） | 24h／7d／30d／自定义；默认 24h | §12.5「分段按钮沿用 OMP 的预置范围」 |
| 状态用颜色＋文字＋图标三通道 | `--sbtd-ok`、`--sbtd-warn`、`--sbtd-error`、`--sbtd-unknown`（色相抽为 `--sbtd-hue-*`） | 色相 152／38／4／210，深浅主题各自定饱和度亮度 | §12.3「状态：颜色＋文字＋必要图标；unknown／partial 不用通过绿色」 |
| 主蓝色强调色 | `--sbtd-accent`、`--sbtd-accent-contrast`、`--sbtd-focus-ring` | `#5b9cf5`（深）／`#1f6fd6`（浅） | 本项目自定；可见焦点 §12.3 可访问性 |
| 标准报告宽度 | `--sbtd-report-width` | 1440 CSS px | §12.3「标准导出报告宽度 1,440 CSS px」 |

## 布局规格（§12.3，与 token 配合）

- 桌面 12 列网格；各 Panel 的列宽（6 或 12）不在 CSS 里写死，而是由 `contracts/panel-manifest.json` 的 `desktop_span` 派生（D14 单一事实源）。
- 窄屏（≤900px）折为单列；控件组可换行；时间选择与导出保持同一操作组、时间在前（§12.5 顺序：刷新／主题 → 时间范围 → 导出）。
- 一个主纵向滚动区域；核心 Panel 不使用内部独立滚动隐藏内容。
- 键盘可操作、可见焦点（`:focus-visible` 使用 `--sbtd-focus-ring`）；关键数值不只靠 hover。

## 零复制声明

本页面全部组件手写；未复制 OMP 的任何代码、CSS、图标、字体或图片资源，因此无 OMP 许可证义务（D17）。若未来升级为 Q10-B（token／图标级复用），须按 grill-r1.md Q10 的记录逐文件保留 OMP MIT 版权／许可证声明并记入第三方声明，且由独立 ADR 固定。
