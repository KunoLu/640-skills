"""Task Markdown parsing and candidate updates; no filesystem writes."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

from sbtd_project import (
    TaskDataError,
    parse_task_frontmatter,
    validate_task_data,
    validate_task_timestamps,
)

_EVENT_COLUMNS = ("at", "from", "to", "reason", "evidence")
_REPAIR = "preserve the task and resolve its document conflict before writing"


def _frontmatter_bounds(text: str) -> tuple[int, int, int]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].removeprefix("\ufeff").rstrip("\r\n") != "---":
        raise TaskDataError("task has no YAML frontmatter block", _REPAIR)
    offset = len(lines[0])
    start = offset
    for line in lines[1:]:
        if line.rstrip("\r\n") == "---":
            return start, offset, offset + len(line)
        offset += len(line)
    raise TaskDataError("task frontmatter block is not terminated", _REPAIR)


def _cells(line: str) -> list[str]:
    line = line.strip()
    line = line.removeprefix("|")
    if line.endswith("|"):
        tail = line[:-1]
        escapes = len(tail) - len(tail.rstrip("\\"))
        if escapes % 2 == 0:
            line = tail
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(line):
        character = line[index]
        if character == "\\" and index + 1 < len(line) and line[index + 1] in "\\|":
            index += 1
            current.append(line[index])
        elif character == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        index += 1
    cells.append("".join(current).strip())
    return cells


def _event_table(
    text: str, body_start: int, *, prepend: bool = False
) -> tuple[list[str], int | None]:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        raise TaskDataError(
            "required dependency markdown-it-py is not installed",
            "install the declared sbtd-workflow-onboard requirements before task writes",
        ) from None
    body = text[body_start:]
    # Token maps count CommonMark line endings, not Unicode text separators.
    lines = re.split(r"(?<=\n)|(?<=\r)(?!\n)", body)
    tokens = MarkdownIt("commonmark").enable("table").parse(body)
    headings = [
        index
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
        and token.tag == "h2"
        and token.level == 0
        and index + 1 < len(tokens)
        and tokens[index + 1].content == "状态事件"
    ]
    if not headings:
        return [], None
    if len(headings) != 1:
        raise TaskDataError("task has multiple state event sections", _REPAIR)
    table_index = headings[0] + 3
    table = tokens[table_index] if table_index < len(tokens) else None
    if (
        table is None
        or table.type != "table_open"
        or table.level != 0
        or table.map is None
    ):
        raise TaskDataError("task state event section has no top-level table", _REPAIR)
    for following in tokens[table_index + 1 :]:
        if (
            following.type == "heading_open"
            and following.level == 0
            and following.tag in ("h1", "h2")
        ):
            break
        if following.type == "table_open" and following.level == 0:
            raise TaskDataError(
                "task state event section contains multiple tables", _REPAIR
            )
    first, last = table.map
    if tuple(_cells(lines[first])) != _EVENT_COLUMNS:
        raise TaskDataError("task state event table has invalid columns", _REPAIR)
    separators = _cells(lines[first + 1])
    if len(separators) != 5 or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separators
    ):
        raise TaskDataError("task state event table has an invalid separator", _REPAIR)
    rows = lines[first + 2 : last]
    boundary = first + 2 if prepend else last
    return rows, body_start + sum(len(line) for line in lines[:boundary])


def _decode_event(line: str) -> dict[str, str]:
    values = _cells(line)
    if len(values) != 5:
        raise TaskDataError("task state event table has a malformed row", _REPAIR)
    return dict(
        zip(
            _EVENT_COLUMNS,
            (html.unescape(cell.replace("<br>", "\n")) for cell in values),
        )
    )


def _validate_event(
    event: dict[str, str], *, legacy: bool = False, after_baseline: bool = False
) -> None:
    candidate = event
    # 旧格式唯一放宽项：历史 in-progress -> done；其余五列和日期
    # 仍复用当前 schema，不能把任意解析失败当作旧格式。
    if legacy and event["from"] == "in-progress" and event["to"] == "done":
        candidate = {**event, "from": "checking"}
    validate_task_data(candidate, "stateEvent", "task state event")
    if event["at"] != "unknown":
        validate_task_timestamps({"updated_at": event["at"]}, "task state event")
    if (
        after_baseline
        and event["to"] == "done"
        and event["from"] not in ("checking", "done")
    ):
        raise TaskDataError("new done event requires checking", _REPAIR)


def _rows_digest(rows: list[str] | tuple[str, ...]) -> str:
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def _event_cell(value: str) -> str:
    """Escape one cell without losing whitespace removed by Markdown table parsing."""
    leading = len(value) - len(value.lstrip())
    if leading == len(value):
        return "".join(f"&#{ord(character)};" for character in value)
    trailing = len(value.rstrip())

    def escape(text: str) -> str:
        return (
            html.escape(text, quote=False)
            .replace("\\", "&#92;")
            .replace("|", "&#124;")
            .replace("\r", "&#13;")
            .replace("\n", "<br>")
        )

    return (
        "".join(f"&#{ord(character)};" for character in value[:leading])
        + escape(value[leading:trailing])
        + "".join(f"&#{ord(character)};" for character in value[trailing:])
    )


def _event_row(event: dict[str, str], newline: str) -> str:
    validate_task_data(event, "stateEvent", "task state event")
    if event["at"] != "unknown":
        validate_task_timestamps({"updated_at": event["at"]}, "task state event")
    cells = [_event_cell(event[key]) for key in _EVENT_COLUMNS]
    return "| " + " | ".join(cells) + " |" + newline


@dataclass(frozen=True)
class TaskDocument:
    text: str
    frontmatter: dict[str, Any]
    events: tuple[dict[str, str], ...]
    event_lines: tuple[str, ...] = ()
    legacy_events: bool = False
    baseline_changed: bool = False
    has_baseline: bool = False

    @classmethod
    def parse(cls, text: str) -> TaskDocument:
        frontmatter = parse_task_frontmatter(text, "task")
        validate_task_data(frontmatter, "taskFrontmatter", "task")
        validate_task_timestamps(frontmatter, "task")
        _, _, body_start = _frontmatter_bounds(text)
        rows, _ = _event_table(text, body_start)
        baselines = [
            index
            for index, line in enumerate(rows)
            if len(_cells(line)) == 5
            and _decode_event(line)["reason"].startswith("旧事件基线：")
        ]
        if len(baselines) > 1:
            raise TaskDataError("task has multiple legacy baselines", _REPAIR)
        changed = False
        legacy = False
        if baselines:
            boundary = baselines[0]
            events = [_decode_event(line) for line in rows[boundary:]]
            for event in events:
                _validate_event(event, after_baseline=True)
            try:
                baseline = json.loads(events[0]["evidence"])
                if (
                    set(baseline) != {"rows", "sha256"}
                    or type(baseline["rows"]) is not int
                    or baseline["rows"] < 0
                    or not isinstance(baseline["sha256"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", baseline["sha256"]) is None
                ):
                    raise ValueError
            except (ValueError, TypeError):
                raise TaskDataError("invalid legacy event baseline", _REPAIR) from None
            changed = baseline["rows"] != boundary or baseline[
                "sha256"
            ] != _rows_digest(rows[:boundary])
        else:
            events = [_decode_event(line) for line in rows]
            for event in events:
                try:
                    _validate_event(event)
                except TaskDataError:
                    _validate_event(event, legacy=True)
                    legacy = True
            if legacy:
                print("旧格式事件，不追溯", file=sys.stderr)
                events = []
        return cls(
            text,
            frontmatter,
            tuple(events),
            tuple(rows),
            legacy,
            changed,
            bool(baselines),
        )

    def updated(
        self,
        fields: dict[str, Any],
        *,
        event: dict[str, str] | None = None,
        prepend_event: bool = False,
    ) -> TaskDocument:
        # Compose only for source spans after the shared safe parser has accepted
        # the data. Replacing owned values preserves all unrelated YAML/body bytes.
        import yaml

        start, end, _ = _frontmatter_bounds(self.text)
        node = yaml.compose(self.text[start:end], Loader=yaml.BaseLoader)
        if not isinstance(node, yaml.MappingNode):
            raise TaskDataError("task frontmatter is not a mapping", _REPAIR)
        spans = {key.value: value for key, value in node.value}
        newline = "\r\n" if "\r\n" in self.text else "\n"
        additions: list[str] = []
        replacements: list[tuple[int, int, str]] = []
        for key, value in fields.items():
            try:
                encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError):
                raise TaskDataError(
                    "task update is not JSON-compatible", _REPAIR
                ) from None
            if key not in spans:
                additions.append(json.dumps(key, ensure_ascii=False) + ": " + encoded)
                continue
            scalar = spans[key]
            first = start + scalar.start_mark.index
            last = start + scalar.end_mark.index
            scalar_text = self.text[first:last]
            header = scalar_text.splitlines()[0] if scalar_text else ""
            if scalar.style in ("|", ">") and "#" in header:
                encoded += " " + header[header.index("#") :]
            if scalar_text.endswith(newline):
                encoded += newline
            replacements.append((first, last, encoded))
        if additions:
            if node.flow_style:
                insertion = start + node.end_mark.index - 1
                if node.value:
                    last_value = node.value[-1][1]
                    trailing = self.text[start + last_value.end_mark.index : insertion]
                    prefix = " " if trailing.lstrip().startswith(",") else ", "
                else:
                    prefix = " "
                appended = prefix + ", ".join(additions)
            else:
                insertion = end
                indent = " " * node.start_mark.column
                appended = "".join(indent + field + newline for field in additions)
            replacements.append((insertion, insertion, appended))
        candidate = self.text
        for first, last, encoded in sorted(replacements, reverse=True):
            candidate = candidate[:first] + encoded + candidate[last:]
        added: tuple[dict[str, str], ...] = ()
        if event is not None:
            _, _, body_start = _frontmatter_bounds(candidate)
            if self.has_baseline and prepend_event:
                raise TaskDataError("cannot prepend inside a legacy baseline", _REPAIR)
            if self.legacy_events:
                prepend_event = False
                baseline_lines = list(self.event_lines)
                if baseline_lines and not baseline_lines[-1].endswith(("\r", "\n")):
                    # EOF 追加需要行分隔符；摘要覆盖同次落盘后的旧事件行。
                    baseline_lines[-1] += newline
                baseline = {
                    "at": event["at"],
                    "from": self.frontmatter["status"],
                    "to": self.frontmatter["status"],
                    "reason": "旧事件基线：写入者沿用紧随的新事件",
                    "evidence": json.dumps(
                        {
                            "rows": len(self.event_lines),
                            "sha256": _rows_digest(baseline_lines),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
                _validate_event(event, after_baseline=True)
                added = (baseline,)
            elif self.has_baseline:
                _validate_event(event, after_baseline=True)
            _, insertion = _event_table(candidate, body_start, prepend=prepend_event)
            added += (event,)
            row = "".join(_event_row(item, newline) for item in added)
            if insertion is None:
                separator = newline if candidate.endswith(newline) else newline * 2
                candidate += separator + "## 状态事件" + newline * 2
                candidate += "| at | from | to | reason | evidence |" + newline
                candidate += "|---|---|---|---|---|" + newline + row
            else:
                prefix = (
                    newline
                    if insertion and candidate[insertion - 1] not in "\r\n"
                    else ""
                )
                candidate = candidate[:insertion] + prefix + row + candidate[insertion:]
        parsed = self.parse(candidate)
        # 未触碰的基线内原始行不重新解释；只核对严格后缀。
        expected_events = added + self.events if prepend_event else self.events + added
        if parsed.events != expected_events:
            raise TaskDataError(
                "task candidate cannot preserve the complete visible state-event history",
                _REPAIR,
            )
        return parsed
