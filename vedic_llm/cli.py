"""Vedic Chart Analysis CLI."""
import typer
import json
import os
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

app = typer.Typer(help="Vedic Chart Analysis — LLM-powered Jyotish readings")
console = Console()


def _parse_birth(date: str, time: str, tz: str, lat: float, lon: float, place: str):
    """Parse CLI args into BirthData."""
    from dateutil import tz as dateutil_tz
    from vedic_llm.models.chart import BirthData

    dt_local = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    local_tz = dateutil_tz.gettz(tz)
    dt_local = dt_local.replace(tzinfo=local_tz)
    dt_utc = dt_local.astimezone(dateutil_tz.UTC)

    return BirthData(
        datetime_utc=dt_utc,
        latitude=lat,
        longitude=lon,
        timezone=tz,
        place=place or f"{lat},{lon}",
    )


@app.command()
def analyze(
    date: str = typer.Option(..., help="Birth date YYYY-MM-DD"),
    time: str = typer.Option(..., help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    place: str = typer.Option("", help="Place name"),
    output: str = typer.Option("report.json", help="Output file path"),
):
    """Run full LLM-powered analysis."""
    load_dotenv()

    birth = _parse_birth(date, time, tz, lat, lon, place)

    console.print(Panel(f"[bold]Analyzing chart for {place or 'location'}[/bold]\n"
                       f"Born: {date} {time} {tz}\nCoords: {lat}, {lon}"))

    from vedic_llm.llm.client import ClaudeClient
    from vedic_llm.llm.orchestrator import AnalysisOrchestrator

    client = ClaudeClient()
    orchestrator = AnalysisOrchestrator(client)

    with console.status("[bold green]Running 4-stage analysis..."):
        result = orchestrator.run_full_analysis(birth)

    # Save to file
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    console.print(f"\n[green]Report saved to {out_path}[/green]")

    # Print summary
    usage = result.get("token_usage", {})
    console.print(f"Tokens used: {usage.get('total', 'N/A')}")

    synth = result.get("synthesis", {})
    if isinstance(synth, dict):
        headline = synth.get("current_life_chapter", "")
        if headline:
            console.print(Panel(headline, title="Current Life Chapter"))

        priorities = synth.get("three_priorities", [])
        if priorities:
            console.print("\n[bold]Top 3 Priorities:[/bold]")
            for i, p in enumerate(priorities, 1):
                console.print(f"  {i}. {p}")


@app.command()
def chart(
    date: str = typer.Option(..., help="Birth date YYYY-MM-DD"),
    time: str = typer.Option(..., help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    place: str = typer.Option("", help="Place name"),
):
    """Print chart positions — no LLM calls."""
    birth = _parse_birth(date, time, tz, lat, lon, place)

    from vedic_llm.compute.chart import build_d1_chart, build_d9_chart
    from vedic_llm.compute.aspects import populate_house_aspects

    d1 = build_d1_chart(birth)
    populate_house_aspects(d1)
    d9 = build_d9_chart(d1)

    # Mark vargottama
    for planet in d1.planets:
        if planet in d9.planets and d1.planets[planet].sign == d9.planets[planet].sign:
            d1.planets[planet].vargottama = True

    console.print(Panel(f"[bold]D1 Rashi Chart — {place or 'location'}[/bold]\n"
                       f"Ascendant: {d1.ascendant_sign.name.title()} {d1.ascendant_degree:.2f}°"))

    # Planet positions table
    table = Table(title="Planet Positions")
    table.add_column("Planet", style="cyan")
    table.add_column("Sign")
    table.add_column("Degree")
    table.add_column("House", justify="center")
    table.add_column("Nakshatra")
    table.add_column("Dignity", style="green")
    table.add_column("R", justify="center")
    table.add_column("V", justify="center")

    for planet, ps in d1.planets.items():
        d = int(ps.degree_in_sign)
        m = int((ps.degree_in_sign - d) * 60)
        table.add_row(
            planet.value,
            ps.sign.name.title(),
            f"{d}°{m:02d}'",
            str(ps.house),
            ps.nakshatra.name.replace("_", " ").title(),
            ps.dignity.value,
            "R" if ps.retrograde else "",
            "V" if ps.vargottama else "",
        )

    console.print(table)

    # Houses table
    h_table = Table(title="Houses")
    h_table.add_column("House", justify="center")
    h_table.add_column("Sign")
    h_table.add_column("Lord")
    h_table.add_column("Occupants")
    h_table.add_column("Aspected By")

    for h_num in range(1, 13):
        h = d1.houses[h_num]
        h_table.add_row(
            str(h_num),
            h.sign.name.title(),
            h.lord.value,
            ", ".join(p.value for p in h.occupants) or "—",
            ", ".join(p.value for p in h.aspected_by) or "—",
        )

    console.print(h_table)


@app.command("save-chart")
def save_chart(
    date: str = typer.Option(..., help="Birth date YYYY-MM-DD"),
    time: str = typer.Option(..., help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    place: str = typer.Option("", help="Place name"),
    name: str = typer.Option("", help="Short name used in the filename (e.g. 'ravi'); defaults to the date"),
    output: str = typer.Option("", help="Output path (default reports/chart_<name>.json)"),
):
    """Compute the full natal dossier and save to disk. Subsequent `analyze-house` calls can load it via --chart-file."""
    birth = _parse_birth(date, time, tz, lat, lon, place)

    from vedic_llm.compute.chart import build_d1_chart, build_d9_chart, build_d10_chart
    from vedic_llm.compute.aspects import populate_house_aspects
    from vedic_llm.extract.natal_facts import extract_natal_dossier

    d1 = build_d1_chart(birth)
    populate_house_aspects(d1)
    d9 = build_d9_chart(d1)
    d10 = build_d10_chart(d1)
    for p in d1.planets:
        if p in d9.planets and d1.planets[p].sign == d9.planets[p].sign:
            d1.planets[p].vargottama = True

    dossier = extract_natal_dossier(d1, d9, d10)

    slug = name or date
    out_path = Path(output) if output else Path("reports") / f"chart_{slug}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dossier.model_dump_json(indent=2))

    console.print(Panel(
        f"[bold]Chart saved[/bold]\n"
        f"Born: {date} {time} {tz}  |  {place or f'{lat},{lon}'}\n"
        f"Asc: {dossier.ascendant['sign']} {dossier.ascendant['degree']}°  |  "
        f"Nakshatra: {dossier.ascendant['nakshatra']} pada {dossier.ascendant['pada']}\n"
        f"Lagna lord: {dossier.ascendant['lagna_lord']}  |  Atmakaraka: {dossier.atmakaraka}\n"
        f"Saved to: {out_path}",
        title="vedic save-chart",
    ))
    console.print(f"\nUse: [cyan]vedic analyze-house --chart-file {out_path} --house N --deep ...[/cyan]")


def _load_dossier(chart_file: str):
    """Load a NatalDossier previously written by save-chart."""
    from vedic_llm.models.dossier import NatalDossier
    path = Path(chart_file).expanduser()
    if not path.exists():
        raise typer.BadParameter(f"Chart file not found: {path}")
    return NatalDossier.model_validate_json(path.read_text())


@app.command("analyze-house")
def analyze_house(
    date: str = typer.Option("", help="Birth date YYYY-MM-DD (omit if using --chart-file)"),
    time: str = typer.Option("", help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(0.0, help="Latitude"),
    lon: float = typer.Option(0.0, help="Longitude"),
    place: str = typer.Option("", help="Place name"),
    chart_file: str = typer.Option("", help="Load a saved chart (from vedic save-chart); skips recomputation"),
    house: int = typer.Option(1, help="House to analyse (1-12)"),
    deep: bool = typer.Option(False, help="Exhaustive D1+D9 deep study (any house)"),
    key_file: str = typer.Option("", help="Path to a file containing ANTHROPIC_API_KEY"),
    output: str = typer.Option("", help="Output JSON path (default reports/house<N>_<slug>.json)"),
    max_tokens: int = typer.Option(32000, help="Max output tokens for the LLM call"),
):
    """Focused LLM reading of a single house — one API call."""
    load_dotenv()
    if key_file:
        key_path = Path(key_file).expanduser()
        if not key_path.exists():
            raise typer.BadParameter(f"Key file not found: {key_path}")
        os.environ["ANTHROPIC_API_KEY"] = key_path.read_text().strip()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise typer.BadParameter("ANTHROPIC_API_KEY not set — pass --key-file or put it in .env")

    if not 1 <= house <= 12:
        raise typer.BadParameter("house must be 1-12")

    from vedic_llm.prompts.house import build_house_prompt, HOUSE_TOPIC
    from vedic_llm.llm.client import ClaudeClient

    slug = ""
    if chart_file:
        natal = _load_dossier(chart_file)
        slug = Path(chart_file).stem.replace("chart_", "")
        birth_summary = f"{natal.birth.get('place', '')} (loaded from {chart_file})"
    else:
        if not date or not time:
            raise typer.BadParameter("Provide --chart-file, or all of --date/--time/--lat/--lon")

        from vedic_llm.compute.chart import build_d1_chart, build_d9_chart, build_d10_chart
        from vedic_llm.compute.aspects import populate_house_aspects
        from vedic_llm.extract.natal_facts import extract_natal_dossier

        birth = _parse_birth(date, time, tz, lat, lon, place)
        d1 = build_d1_chart(birth)
        populate_house_aspects(d1)
        d9 = build_d9_chart(d1)
        d10 = build_d10_chart(d1)
        for p in d1.planets:
            if p in d9.planets and d1.planets[p].sign == d9.planets[p].sign:
                d1.planets[p].vargottama = True
        natal = extract_natal_dossier(d1, d9, d10)
        slug = date
        birth_summary = f"Born: {date} {time} {tz}  |  {place or f'{lat},{lon}'}"

    if deep and house == 1:
        from vedic_llm.prompts.lagna import build_lagna_deep_prompt
        sys_prompt, user_prompt = build_lagna_deep_prompt(natal)
        title_suffix = " (DEEP D1+D9 study)"
    elif deep:
        from vedic_llm.prompts.house_deep import build_house_deep_prompt
        sys_prompt, user_prompt = build_house_deep_prompt(natal, house)
        title_suffix = " (DEEP D1+D9 study)"
    else:
        sys_prompt, user_prompt = build_house_prompt(natal, house)
        title_suffix = ""

    console.print(Panel(
        f"[bold]House {house} reading{title_suffix} — {HOUSE_TOPIC[house]}[/bold]\n"
        f"{birth_summary}",
        title="Focused natal analysis",
    ))

    client = ClaudeClient()
    with console.status(f"[bold green]Calling Claude ({client.model}) for house {house}..."):
        result = client.analyze_json(sys_prompt, user_prompt, max_tokens=max_tokens)

    out = Path(output) if output else Path("reports") / f"house{house}_{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "birth": natal.birth,
        "house": house,
        "deep": deep,
        "reading": result,
        "token_usage": client.token_usage(),
    }
    out.write_text(json.dumps(payload, indent=2, default=str))

    # Accumulate into the running report (one JSON per chart slug)
    from vedic_llm.report import add_house_reading
    report_slug = slug or "default"
    report_path = add_house_reading(
        slug=report_slug,
        dossier=natal,
        house_num=house,
        reading=result if isinstance(result, dict) else {"raw": result},
        deep=deep,
        token_usage=client.token_usage(),
    )
    console.print(f"\n[green]Saved reading to {out}[/green]")
    console.print(f"[green]Appended to running report {report_path}[/green]")
    console.print(f"Tokens — in: {client.total_input_tokens}, out: {client.total_output_tokens}")

    if isinstance(result, dict):
        # Standard house output
        score = result.get("score")
        if score is not None:
            console.print(f"\n[bold]Score:[/bold] {score}/10")
        portrait = result.get("portrait")
        if portrait:
            console.print(Panel(portrait, title=f"House {house} — portrait"))
        # Deep output (any house)
        synth = result.get("section_k_synthesis")
        if isinstance(synth, dict):
            if synth.get("score") is not None:
                console.print(f"\n[bold]House {house} score:[/bold] {synth['score']}/10")
            for key, title in [("character_signature", "Character signature"),
                               ("portrait", f"House {house} — portrait")]:
                body = synth.get(key)
                if body:
                    console.print(Panel(body, title=title))


@app.command()
def dossier(
    date: str = typer.Option(..., help="Birth date YYYY-MM-DD"),
    time: str = typer.Option(..., help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(..., help="Latitude"),
    lon: float = typer.Option(..., help="Longitude"),
    place: str = typer.Option("", help="Place name"),
    output: str = typer.Option("", help="Output file (prints to stdout if empty)"),
):
    """Dump dossier JSON — no LLM calls. For debugging prompts."""
    birth = _parse_birth(date, time, tz, lat, lon, place)

    from vedic_llm.llm.orchestrator import AnalysisOrchestrator
    from vedic_llm.llm.client import ClaudeClient

    orchestrator = AnalysisOrchestrator(ClaudeClient())
    result = orchestrator.run_dossier_only(birth)

    text = json.dumps(result, indent=2, default=str)

    if output:
        Path(output).write_text(text)
        console.print(f"[green]Dossier saved to {output}[/green]")
    else:
        console.print(text)


@app.command("quick-analysis")
def quick_analysis(
    date: str = typer.Option("", help="Birth date YYYY-MM-DD (omit if using --chart-file)"),
    time: str = typer.Option("", help="Birth time HH:MM (24hr)"),
    tz: str = typer.Option("Asia/Kolkata", help="Timezone"),
    lat: float = typer.Option(0.0, help="Latitude"),
    lon: float = typer.Option(0.0, help="Longitude"),
    place: str = typer.Option("", help="Place name"),
    chart_file: str = typer.Option("", help="Load a saved chart (from vedic save-chart); skips recomputation"),
    key_file: str = typer.Option("", help="Path to a file containing ANTHROPIC_API_KEY"),
    max_tokens: int = typer.Option(16000, help="Max output tokens for the LLM call"),
):
    """Single Claude call covering ALL 12 houses — first-pass triage before --deep drill-downs."""
    load_dotenv()
    if key_file:
        key_path = Path(key_file).expanduser()
        if not key_path.exists():
            raise typer.BadParameter(f"Key file not found: {key_path}")
        os.environ["ANTHROPIC_API_KEY"] = key_path.read_text().strip()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise typer.BadParameter("ANTHROPIC_API_KEY not set")

    from vedic_llm.prompts.quick import build_quick_prompt
    from vedic_llm.llm.client import ClaudeClient
    from vedic_llm.report import set_quick_analysis

    slug = ""
    if chart_file:
        natal = _load_dossier(chart_file)
        slug = Path(chart_file).stem.replace("chart_", "")
        birth_summary = f"{natal.birth.get('place', '')} (loaded from {chart_file})"
    else:
        if not date or not time:
            raise typer.BadParameter("Provide --chart-file, or --date/--time/--lat/--lon")
        from vedic_llm.compute.chart import build_d1_chart, build_d9_chart, build_d10_chart
        from vedic_llm.compute.aspects import populate_house_aspects
        from vedic_llm.extract.natal_facts import extract_natal_dossier
        birth = _parse_birth(date, time, tz, lat, lon, place)
        d1 = build_d1_chart(birth)
        populate_house_aspects(d1)
        d9 = build_d9_chart(d1)
        d10 = build_d10_chart(d1)
        for p in d1.planets:
            if p in d9.planets and d1.planets[p].sign == d9.planets[p].sign:
                d1.planets[p].vargottama = True
        natal = extract_natal_dossier(d1, d9, d10)
        slug = date
        birth_summary = f"Born: {date} {time} {tz}  |  {place or f'{lat},{lon}'}"

    console.print(Panel(
        f"[bold]Quick analysis — 12 houses in one call[/bold]\n{birth_summary}",
        title="vedic quick-analysis",
    ))

    client = ClaudeClient()
    sys_prompt, user_prompt = build_quick_prompt(natal)
    with console.status(f"[bold green]Calling Claude ({client.model})..."):
        result = client.analyze_json(sys_prompt, user_prompt, max_tokens=max_tokens)

    report_path = set_quick_analysis(
        slug=slug or "default",
        dossier=natal,
        quick_result=result if isinstance(result, dict) else {"raw": result},
        token_usage=client.token_usage(),
    )

    console.print(f"\n[green]Saved to {report_path}[/green]")
    console.print(f"Tokens — in: {client.total_input_tokens}, out: {client.total_output_tokens}")

    # Print compact summary
    if isinstance(result, dict):
        ov = result.get("overview", {})
        if ov.get("headline"):
            console.print(Panel(ov["headline"], title="Headline"))
        houses = result.get("houses", {})
        if houses:
            t = Table(title="Per-house scores")
            t.add_column("#", justify="center")
            t.add_column("Topic")
            t.add_column("Score", justify="center")
            for num in range(1, 13):
                h = houses.get(str(num)) or houses.get(num) or {}
                t.add_row(str(num), h.get("topic", ""), f"{h.get('score', '—')}/10")
            console.print(t)


@app.command("status")
def status_cmd(
    slug: str = typer.Option(..., help="Chart slug (the part after 'chart_' in the filename)"),
    reports_dir: str = typer.Option("reports", help="Reports directory"),
):
    """Show which houses have been analysed for a given chart."""
    from vedic_llm.report import load_report, HOUSE_LABELS
    report = load_report(slug, reports_dir)
    houses = report.get("houses", {})
    if not houses:
        console.print(f"[yellow]No analyses yet for slug '{slug}'.[/yellow]")
        return

    birth = report.get("birth", {})
    console.print(Panel(
        f"Chart: [bold]{slug}[/bold]\n"
        f"Born: {birth.get('datetime_utc', 'n/a')} — {birth.get('place', '')}\n"
        f"Houses analysed: {len(houses)} / 12",
        title="Report status",
    ))
    table = Table(title="Completed house readings")
    table.add_column("House", justify="center")
    table.add_column("Label")
    table.add_column("Score", justify="center")
    table.add_column("Deep?", justify="center")
    table.add_column("Completed", style="dim")
    for num in range(1, 13):
        h = houses.get(str(num))
        if h:
            table.add_row(
                str(num),
                h.get("label", HOUSE_LABELS.get(num, "")),
                str(h.get("score", "")) or "—",
                "Y" if h.get("deep") else "N",
                (h.get("completed_at") or "")[:19],
            )
        else:
            table.add_row(str(num), HOUSE_LABELS.get(num, ""), "—", "—", "[dim]pending[/dim]")
    console.print(table)


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address — use 0.0.0.0 for external access"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(False, help="Auto-reload on code changes (dev only)"),
    reports_dir: str = typer.Option("reports", help="Directory for saved charts/reports"),
):
    """Start the FastAPI web UI for chart entry + quick analysis."""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        raise typer.BadParameter(
            "Web dependencies not installed. Install them with:\n"
            "  uv pip install -e '.[web]'\n"
            "or: pip install -e '.[web]'"
        )

    os.environ["VEDIC_REPORTS_DIR"] = reports_dir
    if not os.environ.get("ANTHROPIC_API_KEY"):
        load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[yellow]Warning:[/yellow] ANTHROPIC_API_KEY is not set. "
            "Chart computation will work, but LLM analysis will fail."
        )

    console.print(Panel(
        f"Starting vedic_llm web UI\n"
        f"[bold]http://{host}:{port}[/bold]\n"
        f"Reports dir: {reports_dir}",
        title="vedic serve",
    ))

    import uvicorn
    uvicorn.run(
        "vedic_llm.web.app:app",
        host=host, port=port, reload=reload,
        log_level="info",
    )


@app.command("build-report")
def build_report_cmd(
    slug: str = typer.Option(..., help="Chart slug (the part after 'chart_' in the filename)"),
    reports_dir: str = typer.Option("reports", help="Reports directory"),
    output: str = typer.Option("", help="Output markdown path (default reports/report_<slug>.md)"),
):
    """Render the accumulated report as a single Markdown document."""
    from vedic_llm.report import write_markdown, load_report
    report = load_report(slug, reports_dir)
    houses_count = len(report.get("houses", {}))
    out = write_markdown(slug, reports_dir, output or None)
    console.print(f"[green]Wrote {out}[/green] — {houses_count}/12 houses included")


if __name__ == "__main__":
    app()
