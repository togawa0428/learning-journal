#!/usr/bin/env python3
"""Export public, aggregated PMP learning progress from a private Google Sheet."""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import google.auth
from google.auth.transport.requests import AuthorizedSession

ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")
SHEETS = [
    ("DX", "'DX推進_詳細進捗'!A4:D134"),
    ("PMBOK8", "'PMBOK第8版_詳細進捗'!A4:D118"),
]


def fetch_rows(session: AuthorizedSession, spreadsheet_id: str, cell_range: str) -> list[list[str]]:
    from urllib.parse import quote

    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + quote(spreadsheet_id, safe="")
        + "/values/"
        + quote(cell_range, safe="")
    )
    response = session.get(url, params={"valueRenderOption": "FORMATTED_VALUE"}, timeout=30)
    response.raise_for_status()
    return response.json().get("values", [])


def parse_day(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%-m/%-d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def build_progress(data: dict[str, list[list[str]]], today: str) -> dict:
    total = 0
    completed = 0
    courses = {}
    daily = Counter()
    missing_dates = 0
    for course, rows in data.items():
        course_total = 0
        course_done = 0
        for row in rows:
            # Column B is the lesson name. Ignore headings and blank rows.
            if len(row) < 2 or not row[1].strip():
                continue
            course_total += 1
            done = len(row) > 2 and row[2].strip().upper() == "TRUE"
            if done:
                course_done += 1
                day = parse_day(row[3]) if len(row) > 3 else None
                if day:
                    daily[day] += 1
                else:
                    missing_dates += 1
        total += course_total
        completed += course_done
        courses[course] = {"completed": course_done, "total": course_total}
    return {
        "as_of": today,
        "completed": completed,
        "total": total,
        "percent": round(completed / total * 100, 1) if total else 0,
        "courses": courses,
        "daily": dict(sorted(daily.items())),
        "undated_completed": missing_dates,
    }


def render_readme(p: dict) -> str:
    dx = p["courses"]["DX"]
    pm = p["courses"]["PMBOK8"]
    recent = list(p["daily"].items())[-14:][::-1]
    lines = [
        "# Learning Journal",
        "",
        "PMP資格更新に向けた学習記録。学習実績はGoogleスプレッドシートで管理し、公開可能な集計値のみを掲載しています。",
        "",
        "## 学習ダッシュボード",
        "",
        f"**{p['completed']} / {p['total']} レッスン完了（{p['percent']:.1f}%）**",
        "",
        f"- DX推進講座：{dx['completed']} / {dx['total']}",
        f"- PMBOK第8版講座：{pm['completed']} / {pm['total']}",
        f"- 集計日：{p['as_of']}（JST）",
        "",
        "## 最近の学習記録",
        "",
        "| 学習日 | 完了レッスン数 |",
        "| --- | ---: |",
    ]
    if recent:
        lines.extend(f"| {day} | {count} |" for day, count in recent)
    else:
        lines.append("| — | まだ記録がありません |")
    lines.extend([
        "",
        "## 学習履歴",
        "",
        "日別集計は [logs](logs/) にMarkdownで保存しています。個別の学習内容や個人の予定は公開していません。",
        "",
        "## このリポジトリについて",
        "",
        "- 実績の正本：非公開のGoogleスプレッドシート",
        "- 更新方法：GitHub Actionsによる日次集計（データ変更時のみコミット）",
        "- GitHubのContribution Graphは、学習日ではなくコミット日等の条件で集計されます",
        "",
    ])
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    spreadsheet_id = os.environ["PMP_SPREADSHEET_ID"]
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    session = AuthorizedSession(credentials)
    rows = {name: fetch_rows(session, spreadsheet_id, rng) for name, rng in SHEETS}
    today = datetime.now(JST).date().isoformat()
    progress = build_progress(rows, today)
    # Avoid creating commits on days when nothing changed: no timestamp in persisted data.
    progress.pop("as_of")
    write_if_changed(ROOT / "data" / "progress.json", json.dumps(progress, ensure_ascii=False, indent=2) + "\n")
    progress["as_of"] = today
    # The README's date should not force a daily commit.
    progress["as_of"] = "学習実績の更新時"
    write_if_changed(ROOT / "README.md", render_readme(progress))
    for day, count in progress["daily"].items():
        write_if_changed(
            ROOT / "logs" / (day + ".md"),
            f"# {day} の学習記録\n\n完了レッスン：**{count}件**\n\n※ 公開用の集計値のみを記録しています。\n",
        )
    print(f"Completed {progress['completed']}/{progress['total']} lessons")


if __name__ == "__main__":
    main()
