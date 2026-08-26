"""Render a Trigpoint ledger.

Pure functions over strings. No filesystem access and no third-party imports.
"""

from __future__ import annotations

import html as html_module
import re
from typing import List, Tuple

from trigpoint_ledger import Ledger, Track


def heading_text(track: Track) -> str:
    """Format track heading, avoiding duplication for single-word tracks.

    For a track with name, returns "identifier name".
    For a single-word track with empty name, returns just "identifier".
    """
    if track.name:
        return "{0} {1}".format(track.track_identifier, track.name)
    else:
        return track.track_identifier


def marker_pair(region: str) -> Tuple[str, str]:
    return (
        "<!-- trigpoint:{0}:begin -->".format(region),
        "<!-- trigpoint:{0}:end -->".format(region),
    )


def replace_marked_region(text: str, region: str, replacement: str) -> Tuple[str, bool]:
    begin_marker, end_marker = marker_pair(region)
    pattern = re.compile(
        re.escape(begin_marker) + r".*?" + re.escape(end_marker), re.DOTALL
    )
    if not pattern.search(text):
        return text, False
    body = "{0}\n{1}\n{2}".format(begin_marker, replacement.strip("\n"), end_marker)
    return pattern.sub(lambda _: body, text, count=1), True


def render_progress_table(ledger: Ledger) -> str:
    lines = [
        "| Track | Scope | Tasks | Done | Blocked by |",
        "| --- | --- | --- | --- | --- |",
    ]
    for track in ledger.tracks:
        lines.append(
            "| **{0}** | {1} | {2} | {3} | {4} |".format(
                heading_text(track),
                track.scope,
                track.task_count,
                track.done_count,
                track.blocked_by or "nothing",
            )
        )
    lines.append(
        "| **Total** | | {0} | {1} | |".format(ledger.task_count, ledger.done_count)
    )
    return "\n".join(lines)


DASHBOARD_STYLE = """
:root {
  --page: #f6f5f2; --ink: #1b1c1e; --muted: #6a6b70;
  --rule: #d9d7d1; --panel: #ffffff; --accent: #b4541f;
  --done: #2f6f4f; --open: #9a9893;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --page: #16171a; --ink: #e9e8e4; --muted: #9a9ba0;
    --rule: #2c2e33; --panel: #1d1f23; --accent: #e0763c;
    --done: #6fbf95; --open: #5a5c62;
  }
}
:root[data-theme="dark"] {
  --page: #16171a; --ink: #e9e8e4; --muted: #9a9ba0;
  --rule: #2c2e33; --panel: #1d1f23; --accent: #e0763c;
  --done: #6fbf95; --open: #5a5c62;
}
body { background: var(--page); color: var(--ink); margin: 0;
  font: 16px/1.55 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
.wrap { max-width: 60rem; margin: 0 auto; padding: 3rem 1.25rem 5rem; }
.headline { font-size: 1.35rem; line-height: 1.35; border-left: 3px solid var(--accent);
  padding-left: 1rem; margin: 0 0 2.5rem; }
.track { border: 1px solid var(--rule); background: var(--panel);
  border-radius: 6px; padding: 1.1rem 1.25rem; margin: 0 0 1rem; }
.track h2 { font-size: 1rem; margin: 0 0 .35rem; letter-spacing: .01em; }
.meta { color: var(--muted); font-size: .85rem; margin: 0 0 .8rem; }
.bar { height: 4px; background: var(--open); border-radius: 2px; overflow: hidden;
  margin: 0 0 .9rem; }
.bar span { display: block; height: 100%; background: var(--done); }
ul.tasks { list-style: none; margin: 0; padding: 0; }
ul.tasks li { padding: .3rem 0; border-top: 1px solid var(--rule); font-size: .92rem; }
ul.tasks li:first-child { border-top: 0; }
.state { display: inline-block; width: 1.4rem; color: var(--muted); }
.state.done { color: var(--done); }
.task-id { display: inline-block; min-width: 2.6rem; color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem; }
.evidence { display: block; color: var(--muted); font-size: .8rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; padding-left: 1.4rem; }
footer { color: var(--muted); font-size: .82rem; border-top: 1px solid var(--rule);
  margin-top: 3rem; padding-top: 1rem; }
.scroll { overflow-x: auto; }
"""


def render_dashboard(
    ledger: Ledger,
    title: str,
    headline: str,
    lanes_run: List[str],
    lanes_skipped: List[str],
) -> str:
    escape = html_module.escape
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>{0}</title>".format(escape(title)),
        "<style>{0}</style>".format(DASHBOARD_STYLE),
        "</head><body><div class=\"wrap\">",
        "<p class=\"headline\">{0}</p>".format(escape(headline)),
        "<p class=\"meta\">{0} of {1} tasks complete across {2} tracks.</p>".format(
            ledger.done_count, ledger.task_count, len(ledger.tracks)
        ),
    ]

    for track in ledger.tracks:
        percent = (
            int(round(100.0 * track.done_count / track.task_count))
            if track.task_count
            else 0
        )
        parts.append('<section class="track">')
        parts.append(
            "<h2>{0}</h2>".format(escape(heading_text(track)))
        )
        parts.append(
            '<p class="meta">{0} &middot; blocked by {1} &middot; {2} / {3}</p>'.format(
                escape(track.scope),
                escape(track.blocked_by or "nothing"),
                track.done_count,
                track.task_count,
            )
        )
        parts.append('<div class="bar"><span style="width:{0}%"></span></div>'.format(percent))
        parts.append('<ul class="tasks">')
        for task in track.tasks:
            state_class = "state done" if task.done else "state"
            state_mark = "x" if task.done else "-"
            parts.append(
                '<li><span class="{0}">{1}</span><span class="task-id">{2}</span>{3}'.format(
                    state_class, state_mark, escape(task.task_id), escape(task.text)
                )
            )
            if task.evidence:
                parts.append(
                    '<span class="evidence">{0}</span>'.format(escape(task.evidence))
                )
            parts.append("</li>")
        parts.append("</ul></section>")

    if ledger.done_criteria:
        parts.append('<section class="track"><h2>Definition of done</h2>')
        parts.append('<ul class="tasks">')
        for criterion in ledger.done_criteria:
            state_class = "state done" if criterion.done else "state"
            state_mark = "x" if criterion.done else "-"
            parts.append(
                '<li><span class="{0}">{1}</span>{2}</li>'.format(
                    state_class, state_mark, escape(criterion.text)
                )
            )
        parts.append("</ul></section>")

    parts.append("<footer>")
    parts.append(
        "<p>Audit lanes run: {0}.</p>".format(
            escape(", ".join(lanes_run)) if lanes_run else "none recorded"
        )
    )
    parts.append(
        "<p>Audit lanes NOT run: {0}. Nothing is claimed about them.</p>".format(
            escape(", ".join(lanes_skipped)) if lanes_skipped else "none"
        )
    )
    parts.append(
        "<p>Generated from the ledger. Do not hand-edit this file.</p>"
    )
    parts.append("</footer></div></body></html>")
    return "\n".join(parts)
