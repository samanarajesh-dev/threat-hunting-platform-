"""Investigation report generation (PDF for sharing, Markdown for pasting into tickets)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.db.models import Case

NAVY = colors.HexColor("#1F3864")


def _clean(text: str | None) -> str:
    # The built-in PDF fonts have no arrow glyph; keep user text safe for reportlab's mini-markup.
    return escape((text or "").replace("→", "->"))


def _fmt(dt: datetime | None) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if dt else "-"


def build_case_report_pdf(case: Case, generated_by: str, ioc_verdicts: list[dict] | None = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Investigation report - case {case.id}", author=generated_by)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=20, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11)

    def table(rows, widths):
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BFC7D5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F5F9")]),
        ]))
        return t

    P = lambda t, s=cell: Paragraph(_clean(t), s)  # noqa: E731
    story = [
        Paragraph("Investigation Report", h1),
        Paragraph(f"Case #{case.id}: {_clean(case.title)}", body),
        Paragraph(f"Generated {_fmt(datetime.now(timezone.utc))} by {_clean(generated_by)}", small),
        Spacer(1, 8),
        table([["Status", "Severity", "Owner", "Opened", "Last updated"],
               [case.status, case.severity, case.owner.username if case.owner else "-", _fmt(case.created_at), _fmt(case.updated_at)]],
              [28 * mm, 28 * mm, 36 * mm, 40 * mm, 40 * mm]),
        Paragraph("Summary", h2), Paragraph(_clean(case.description) or "No summary recorded.", body),
    ]

    story.append(Paragraph("Linked alerts", h2))
    if case.alerts:
        rows = [["Time (first seen)", "Severity", "Alert", "MITRE", "Entities"]]
        for a in sorted(case.alerts, key=lambda x: x.first_seen):
            rows.append([P(_fmt(a.first_seen)), P(a.severity), P(a.title), P(f"{a.mitre_tactic or ''} {a.mitre_technique or ''}"), P(", ".join(a.entities))])
        story.append(table(rows, [30 * mm, 18 * mm, 52 * mm, 34 * mm, 38 * mm]))
    else:
        story.append(Paragraph("No alerts linked.", body))

    story.append(Paragraph("Findings", h2))
    if case.findings:
        for f in case.findings:
            story.append(Paragraph(f"<b>{_clean(f.title)}</b> ({f.severity} severity, {f.confidence} confidence"
                                   f"{', ' + _clean(f.mitre_technique) if f.mitre_technique else ''})", body))
            story.append(Paragraph(_clean(f.description), body))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No findings recorded.", body))

    if ioc_verdicts:
        story.append(Paragraph("Indicators of compromise", h2))
        rows = [["Indicator", "Type", "Verdict", "Detail"]] + [
            [P(i["value"]), P(i["type"]), P(i["verdict"]), P(", ".join(f"{r['provider']}:{r['verdict']}" for r in i.get("results", [])))] for i in ioc_verdicts]
        story.append(table(rows, [60 * mm, 18 * mm, 24 * mm, 70 * mm]))

    story.append(Paragraph("Evidence register", h2))
    if case.evidence:
        rows = [["#", "Added", "Type", "Title", "SHA-256 (integrity)"]]
        for e in sorted(case.evidence, key=lambda x: x.added_at):
            rows.append([P(str(e.id)), P(_fmt(e.added_at)), P(e.kind), P(e.title), P(e.sha256)])
        story.append(table(rows, [8 * mm, 32 * mm, 18 * mm, 40 * mm, 76 * mm]))
        story.append(Paragraph("Each evidence item is stored append-only; the SHA-256 lets a reviewer prove it was not modified after collection.", small))
    else:
        story.append(Paragraph("No evidence attached.", body))

    doc.build(story)
    return buf.getvalue()


def build_case_report_markdown(case: Case, generated_by: str) -> str:
    lines = [f"# Investigation Report - Case #{case.id}: {case.title}", "",
             f"*Generated {_fmt(datetime.now(timezone.utc))} by {generated_by}*", "",
             f"**Status:** {case.status}  |  **Severity:** {case.severity}", "", "## Summary", "", case.description or "_None_", "", "## Linked alerts", ""]
    lines += [f"- [{a.severity}] {a.title} ({a.mitre_tactic or '-'} / {a.mitre_technique or '-'}) - {_fmt(a.first_seen)}" for a in case.alerts] or ["_None_"]
    lines += ["", "## Findings", ""]
    for f in case.findings:
        lines += [f"### {f.title}  ({f.severity}/{f.confidence})", f.description, ""]
    if not case.findings:
        lines.append("_None_")
    lines += ["", "## Evidence register", ""]
    lines += [f"- #{e.id} [{e.kind}] {e.title} - sha256 `{e.sha256}`" for e in case.evidence] or ["_None_"]
    return "\n".join(lines) + "\n"
