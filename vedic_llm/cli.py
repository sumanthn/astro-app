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


if __name__ == "__main__":
    app()
