from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich import box

console = Console(highlight=False)

MODE_COLORS = {
    "cto":   "bold blue",
    "ceo":   "bold green",
    "debug": "bold red",
    "sales": "bold magenta",
    "deep":  "bold cyan",
    "quick": "bold white",
    "web":   "bold yellow",
}


def print_response(result, mode):
    color = MODE_COLORS.get(mode, "bold white")
    console.print()
    console.rule(f"[{color}] {mode} [/]", style="dim")
    console.print()
    console.print(Markdown(result))
    console.print()
    console.print("  [green]✓ copied[/green]")
    console.print()


def print_progress(msg):
    console.print(f"[dim]{msg}[/dim]")


def print_error(msg):
    console.print(f"[bold red]✗[/bold red] {msg}")


def print_init(cwd, count, est_cost, est_secs):
    mins, secs = divmod(int(est_secs), 60)
    time_str = f"{mins}m {secs}s" if mins else f"~{secs}s"
    console.print()
    console.rule("[bold]askr init[/]", style="dim")
    console.print(f"  [dim]directory[/dim]  {cwd}")
    console.print(f"  [dim]files[/dim]      {count}")
    console.print(f"  [dim]est. cost[/dim]  ~${est_cost:.3f}")
    console.print(f"  [dim]est. time[/dim]  {time_str}")
    console.print()


def make_progress_bar(total):
    progress = Progress(
        SpinnerColumn(style="dim"),
        TextColumn("  [dim]{task.description}[/dim]"),
        BarColumn(bar_width=36, style="dim", complete_style="green"),
        TextColumn("[green]{task.completed}[/green][dim]/{task.total}[/dim]"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )
    task = progress.add_task("indexing", total=total)
    return progress, task


def print_summary(recent, entries, total_in, total_out, total_cost, mode_counts):
    console.print()
    console.rule("[bold]askr — last 7 days[/]", style="dim")
    console.print()

    stats = Table(box=None, show_header=False, padding=(0, 2), show_edge=False)
    stats.add_column("key", style="dim", min_width=14)
    stats.add_column("value", style="bold")
    stats.add_row("queries", str(len(recent)))
    stats.add_row("tokens in", f"{total_in:,}")
    stats.add_row("tokens out", f"{total_out:,}")
    stats.add_row("total cost", f"[green]${total_cost:.4f}[/green]")
    console.print(stats)

    if mode_counts:
        console.print()
        modes = Table(box=box.SIMPLE_HEAD, show_header=True, padding=(0, 2))
        modes.add_column("mode", style="bold")
        modes.add_column("queries", justify="right", style="dim")
        for m, count in sorted(mode_counts.items(), key=lambda x: -x[1]):
            color = MODE_COLORS.get(m, "white")
            modes.add_row(f"[{color}]{m}[/]", str(count))
        console.print(modes)

    if entries:
        console.print()
        console.rule("[dim]last 5[/]", style="dim")
        for e in entries[-5:]:
            console.print(
                f"  [dim]{e['ts']}[/dim]  "
                f"[{MODE_COLORS.get(e['mode'], 'white')}]{e['mode']:<8}[/]  "
                f"[green]${e['cost_usd']:.5f}[/green]  "
                f"[dim]{e['q']}[/dim]"
            )

    console.print()
