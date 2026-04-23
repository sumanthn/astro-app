"""Accumulating chart report — one JSON file per chart, grows as houses are added.

Each `analyze-house` call calls `add_house_reading()`, which updates
`reports/report_<slug>.json`. `build_markdown()` renders the final document
from that JSON — it can be called at any time to get the current state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vedic_llm.models.dossier import NatalDossier


def _report_path(slug: str, reports_dir: Path | str = "reports") -> Path:
    return Path(reports_dir) / f"report_{slug}.json"


def _chart_summary(dossier: NatalDossier) -> dict:
    """Compact, human-readable snapshot of the chart's key facts."""
    return {
        "ascendant": {
            "sign": dossier.ascendant.get("sign"),
            "degree": dossier.ascendant.get("degree"),
            "nakshatra": dossier.ascendant.get("nakshatra"),
            "pada": dossier.ascendant.get("pada"),
            "nakshatra_lord": dossier.ascendant.get("nakshatra_lord"),
            "lagna_lord": dossier.ascendant.get("lagna_lord"),
        },
        "planets": {
            name: {
                "sign": pf.sign,
                "degree": pf.degree,
                "house": pf.house,
                "nakshatra": pf.nakshatra,
                "pada": pf.pada,
                "dignity": pf.dignity,
                "natural_dignity": pf.natural_dignity,
                "retrograde": pf.retrograde,
                "combust": pf.combust,
                "vargottama": pf.vargottama,
                "functional_nature": pf.functional_nature,
            }
            for name, pf in dossier.planets.items()
        },
        "atmakaraka": dossier.atmakaraka,
        "amatyakaraka": dossier.amatyakaraka,
        "vargottama_planets": dossier.vargottama_planets,
        "functional_benefics": dossier.functional_benefics,
        "functional_malefics": dossier.functional_malefics,
        "functional_neutrals": dossier.functional_neutrals,
        "yogakarakas": dossier.yogakarakas,
        "yogas": dossier.yogas,
        "d9_ascendant": dossier.d9_summary.get("ascendant"),
        "d9_ascendant_nakshatra": dossier.d9_summary.get("ascendant_nakshatra"),
    }


def load_report(slug: str, reports_dir: Path | str = "reports") -> dict:
    path = _report_path(slug, reports_dir)
    if path.exists():
        return json.loads(path.read_text())
    return {"slug": slug, "houses": {}}


def save_report(report: dict, reports_dir: Path | str = "reports") -> Path:
    slug = report["slug"]
    path = _report_path(slug, reports_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str))
    return path


HOUSE_LABELS = {
    1: "The Self",
    2: "Wealth & Speech",
    3: "Courage & Siblings",
    4: "Home & Mother",
    5: "Intelligence & Children",
    6: "Enemies & Service",
    7: "Spouse & Partnerships",
    8: "Longevity & Transformation",
    9: "Dharma & Fortune",
    10: "Career & Status",
    11: "Gains & Networks",
    12: "Losses & Moksha",
}


def set_quick_analysis(
    slug: str,
    dossier: NatalDossier,
    quick_result: dict,
    token_usage: dict,
    reports_dir: Path | str = "reports",
) -> Path:
    """Store the quick (12-house overview) analysis on the running report."""
    report = load_report(slug, reports_dir)
    report["birth"] = dossier.birth
    report["chart_summary"] = _chart_summary(dossier)
    report["slug"] = slug
    report["quick_analysis"] = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "token_usage": token_usage,
        "result": quick_result,
    }
    return save_report(report, reports_dir)


def add_house_reading(
    slug: str,
    dossier: NatalDossier,
    house_num: int,
    reading: dict,
    deep: bool,
    token_usage: dict,
    reports_dir: Path | str = "reports",
) -> Path:
    """Add (or overwrite) a house reading in the accumulating report."""
    report = load_report(slug, reports_dir)
    # Always refresh birth + chart summary (latest dossier wins)
    report["birth"] = dossier.birth
    report["chart_summary"] = _chart_summary(dossier)
    report["slug"] = slug

    # Extract score — deep readings put it under section_k_synthesis, shallow under top-level
    score = None
    if isinstance(reading, dict):
        synth = reading.get("section_k_synthesis")
        if isinstance(synth, dict):
            score = synth.get("score")
        if score is None:
            score = reading.get("score")

    report.setdefault("houses", {})[str(house_num)] = {
        "number": house_num,
        "label": HOUSE_LABELS.get(house_num, f"House {house_num}"),
        "topic": reading.get("topic") if isinstance(reading, dict) else None,
        "score": score,
        "deep": deep,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "token_usage": token_usage,
        "reading": reading,
    }
    return save_report(report, reports_dir)


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _fmt_planet_row(name: str, p: dict) -> str:
    flags = []
    if p.get("retrograde"):
        flags.append("R")
    if p.get("combust"):
        flags.append("C")
    if p.get("vargottama"):
        flags.append("V")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    nat_diff = ""
    if p.get("natural_dignity") and p.get("natural_dignity") != p.get("dignity"):
        nat_diff = f" / natural {p['natural_dignity']}"
    return (
        f"| {name} | {p.get('sign')} | {p.get('degree')} | {p.get('house')} | "
        f"{p.get('nakshatra')} p{p.get('pada')} | {p.get('dignity')}{nat_diff}{flag_str} | "
        f"{p.get('functional_nature')} |"
    )


def _render_house_section(house_data: dict) -> list[str]:
    """Render a single house reading as markdown lines."""
    h = house_data["number"]
    label = house_data.get("label", f"House {h}")
    score = house_data.get("score")
    score_str = f" — Score: **{score}/10**" if score is not None else ""
    deep_tag = " _(deep D1+D9 study)_" if house_data.get("deep") else ""
    lines = [f"\n## House {h} — {label}{score_str}{deep_tag}\n"]

    topic = house_data.get("topic")
    if topic:
        lines.append(f"*{topic}*\n")

    reading = house_data.get("reading", {})
    if not isinstance(reading, dict):
        lines.append(f"```\n{reading}\n```\n")
        return lines

    # Deep reading layout: sections A-K
    if reading.get("section_k_synthesis"):
        lines.extend(_render_deep_reading(reading))
    else:
        # Shallow 8-step layout (from prompts/house.py)
        lines.extend(_render_shallow_reading(reading))

    tokens = house_data.get("token_usage", {})
    if tokens:
        lines.append(
            f"\n<sub>Tokens — in: {tokens.get('input_tokens', 'n/a')}, "
            f"out: {tokens.get('output_tokens', 'n/a')}, "
            f"completed: {house_data.get('completed_at', '')}</sub>\n"
        )
    return lines


def _render_deep_reading(r: dict) -> list[str]:
    """Render the deep (Lagna or generic) reading sections."""
    out = []
    section_titles = {
        "section_a_d1_lagna": "A — The Lagna (D1)",
        "section_a_house_itself": "A — The House (D1)",
        "section_b_lagna_lord": "B — Lagna Lord",
        "section_b_house_lord": "B — House Lord",
        "section_c_aspects_on_lagna": "C — Aspects on the Lagna",
        "section_c_aspects_on_house": "C — Aspects on the House",
        "section_d_karakas": "D — Natural Karakas",
        "section_e_chandra_lagna": "E — Chandra Lagna (Moon as 1st)",
        "section_e_chandra_lagna_view": "E — Chandra Lagna view",
        "section_f_surya_lagna": "F — Surya Lagna (Sun as 1st)",
        "section_f_surya_lagna_view": "F — Surya Lagna view",
        "section_g_d9": "G — D9 Cross-Check",
        "section_h_functional_roll_call": "H — Functional Roll-Call",
        "section_i_yogas": "I — Yogas Touching this House",
        "section_j_special_cancellations": "J — Special Cancellations",
        "section_k_synthesis": "K — Synthesis",
    }
    for key, title in section_titles.items():
        if key not in r:
            continue
        out.append(f"\n### {title}\n")
        out.extend(_render_value(r[key]))
    return out


def _render_shallow_reading(r: dict) -> list[str]:
    out = []
    eight = r.get("eight_step")
    if isinstance(eight, dict):
        out.append("\n### Eight-Step Analysis\n")
        titles = {
            "step1_identification": "1. House & Lord",
            "step2_lord_placement": "2. Lord's Placement",
            "step3_lord_dignity": "3. Lord's Dignity",
            "step4_occupants": "4. Occupants",
            "step5_aspects": "5. Aspects",
            "step6_karaka": "6. Karaka",
            "step7_d9_crosscheck": "7. D9 Cross-Check",
            "step8_synthesis": "8. Synthesis",
        }
        for k, title in titles.items():
            if k in eight:
                out.append(f"\n**{title}**\n\n{eight[k]}\n")
    for label, key in [("Strengths", "strengths"), ("Weaknesses", "weaknesses"),
                       ("Promised Themes", "promised_themes"),
                       ("Contingent Themes", "contingent_themes")]:
        items = r.get(key)
        if items:
            out.append(f"\n**{label}:**\n")
            for it in items:
                out.append(f"- {it}\n")
    portrait = r.get("portrait")
    if portrait:
        out.append(f"\n**Portrait:**\n\n{portrait}\n")
    return out


def _render_value(v: Any, depth: int = 0) -> list[str]:
    """Pretty-print a JSON value into markdown lines."""
    out = []
    if isinstance(v, str):
        out.append(f"{v}\n")
    elif isinstance(v, dict):
        for k, val in v.items():
            if isinstance(val, (dict, list)):
                out.append(f"\n**{_humanize_key(k)}:**\n")
                out.extend(_render_value(val, depth + 1))
            else:
                out.append(f"- **{_humanize_key(k)}:** {val}\n")
    elif isinstance(v, list):
        for item in v:
            if isinstance(item, dict):
                # e.g. list of dignity-shift rows, aspect rows, yoga rows
                inline = "; ".join(f"**{_humanize_key(k)}**: {val}" for k, val in item.items())
                out.append(f"- {inline}\n")
            else:
                out.append(f"- {item}\n")
    else:
        out.append(f"{v}\n")
    return out


def _humanize_key(k: str) -> str:
    return k.replace("_", " ").replace("d9", "D9").replace("d1", "D1").strip().capitalize()


def build_markdown(slug: str, reports_dir: Path | str = "reports") -> str:
    """Render the full accumulated report as markdown."""
    report = load_report(slug, reports_dir)
    lines = [f"# Vedic Chart Analysis — {slug}\n"]

    birth = report.get("birth", {})
    if birth:
        lines.append("## Birth Details\n")
        for k in ("datetime_utc", "place", "latitude", "longitude", "timezone"):
            if birth.get(k) is not None:
                lines.append(f"- **{_humanize_key(k)}:** {birth[k]}\n")
        lines.append("")

    cs = report.get("chart_summary", {})
    if cs:
        asc = cs.get("ascendant", {})
        lines.append("## Chart Summary\n")
        lines.append(
            f"- **Ascendant:** {asc.get('sign')} {asc.get('degree')}° — "
            f"{asc.get('nakshatra')} pada {asc.get('pada')} "
            f"(nakshatra lord: {asc.get('nakshatra_lord')})\n"
        )
        lines.append(f"- **Lagna Lord:** {asc.get('lagna_lord')}\n")
        lines.append(f"- **Atmakaraka:** {cs.get('atmakaraka')}  |  "
                     f"**Amatyakaraka:** {cs.get('amatyakaraka')}\n")
        lines.append(f"- **Vargottama:** {', '.join(cs.get('vargottama_planets') or []) or '—'}\n")
        lines.append(f"- **Functional Benefics:** {', '.join(cs.get('functional_benefics') or []) or '—'}\n")
        lines.append(f"- **Functional Malefics:** {', '.join(cs.get('functional_malefics') or []) or '—'}\n")
        lines.append(f"- **D9 Ascendant:** {cs.get('d9_ascendant')} "
                     f"({cs.get('d9_ascendant_nakshatra', '')})\n")

        # Planet table
        planets = cs.get("planets", {})
        if planets:
            lines.append("\n### Planet Positions\n")
            lines.append("| Planet | Sign | Degree | House | Nakshatra | Dignity | Functional |\n")
            lines.append("|---|---|---|---|---|---|---|\n")
            for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                         "Saturn", "Rahu", "Ketu"]:
                if name in planets:
                    lines.append(_fmt_planet_row(name, planets[name]) + "\n")

        yogas = cs.get("yogas") or []
        if yogas:
            lines.append("\n### Yogas\n")
            for y in yogas:
                planets_str = ", ".join(y.get("planets", [])) if y.get("planets") else ""
                lines.append(
                    f"- **{y.get('name')}** "
                    f"({y.get('strength', 'n/a')}) — planets: {planets_str}; "
                    f"houses: {y.get('houses')}"
                )
                reason = y.get("reason")
                if reason:
                    lines.append(f" — {reason}")
                lines.append("\n")

    # Quick analysis (12-house overview), if present
    quick = report.get("quick_analysis", {})
    if quick:
        lines.append("\n---\n\n# Quick Analysis — 12-House Overview\n")
        lines.extend(_render_quick_analysis(quick.get("result", {})))
        tok = quick.get("token_usage", {})
        if tok:
            lines.append(
                f"\n<sub>Quick analysis tokens — in: {tok.get('input_tokens', 'n/a')}, "
                f"out: {tok.get('output_tokens', 'n/a')}, "
                f"completed: {quick.get('completed_at', '')}</sub>\n"
            )

    # Deep house readings (sorted numerically)
    houses = report.get("houses", {})
    if houses:
        lines.append("\n---\n\n# House-by-House Deep Analysis\n")
        for key in sorted(houses.keys(), key=int):
            lines.extend(_render_house_section(houses[key]))

    return "".join(lines)


def _render_quick_analysis(q: dict) -> list[str]:
    out = []
    overview = q.get("overview", {})
    if overview:
        head = overview.get("headline")
        if head:
            out.append(f"\n> {head}\n")
        lagna = overview.get("lagna_snapshot")
        if lagna:
            out.append(f"\n**Lagna:** {lagna}\n")
        ak_note = overview.get("atmakaraka_note")
        if ak_note:
            out.append(f"\n**Atmakaraka:** {ak_note}\n")
        d9 = overview.get("d9_qualification")
        if d9:
            out.append(f"\n**D9 cross-check:** {d9}\n")
        for label, key in [("Top strengths", "top_strengths"),
                           ("Top vulnerabilities", "top_vulnerabilities"),
                           ("Structural pillars", "structural_pillars"),
                           ("Key yogas", "key_yogas")]:
            items = overview.get(key) or []
            if items:
                out.append(f"\n**{label}:**\n")
                for it in items:
                    out.append(f"- {it}\n")

    houses = q.get("houses", {})
    if houses:
        out.append("\n## Per-house snapshot\n")
        out.append("\n| # | Topic | Score | Snapshot |\n|---|---|---|---|\n")
        for num in range(1, 13):
            h = houses.get(str(num)) or houses.get(num) or {}
            out.append(
                f"| {num} | {h.get('topic', '')} | {h.get('score', '—')}/10 | "
                f"{h.get('snapshot', '').replace(chr(10), ' ').strip()} |\n"
            )
        for num in range(1, 13):
            h = houses.get(str(num)) or houses.get(num) or {}
            if not h:
                continue
            out.append(f"\n### House {num} — {h.get('topic', '')} (Score: {h.get('score', '—')}/10)\n")
            snap = h.get("snapshot")
            if snap:
                out.append(f"\n{snap}\n")
            strengths = h.get("strengths") or []
            if strengths:
                out.append("\n**Strengths:**\n")
                for s in strengths:
                    out.append(f"- {s}\n")
            weaknesses = h.get("weaknesses") or []
            if weaknesses:
                out.append("\n**Weaknesses:**\n")
                for w in weaknesses:
                    out.append(f"- {w}\n")

    priorities = q.get("top_priorities") or []
    if priorities:
        out.append("\n## Top priorities\n")
        for p in priorities:
            out.append(f"- {p}\n")
    return out


def write_markdown(slug: str, reports_dir: Path | str = "reports",
                   output: str | None = None) -> Path:
    md = build_markdown(slug, reports_dir)
    out = Path(output) if output else Path(reports_dir) / f"report_{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    return out
