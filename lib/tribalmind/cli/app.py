"""TribalMind CLI - root Typer application."""

from __future__ import annotations

import typer

from tribalmind import __version__

app = typer.Typer(
    name="tribal",
    help="TribalMind - Shared memory for AI development agents",
    invoke_without_command=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tribal {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.", callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """TribalMind - Shared memory for AI development agents.

    Remember, recall, and share knowledge across projects and teams.
    Any agent that can run shell commands can use this.
    """
    if ctx.invoked_subcommand is None:
        from tribalmind.cli.banner import print_banner  # noqa: E402

        print_banner()
        # Show usage help after the banner
        import click
        click.echo(ctx.get_help())
        raise typer.Exit()
    else:
        if ctx.invoked_subcommand != "upgrade":
            from tribalmind.cli.version_check import check_and_notify  # noqa: E402

            check_and_notify()




# Register subcommands
from tribalmind.cli.config_cmd import config_app  # noqa: E402

app.add_typer(config_app, name="config", help="Manage TribalMind configuration.")

from tribalmind.cli.init_cmd import init  # noqa: E402

app.command()(init)

from tribalmind.cli.remember_cmd import remember  # noqa: E402

app.command()(remember)

from tribalmind.cli.recall_cmd import recall  # noqa: E402

app.command()(recall)

from tribalmind.cli.forget_cmd import forget  # noqa: E402

app.command()(forget)

from tribalmind.cli.status_cmd import status  # noqa: E402

app.command()(status)

from tribalmind.cli.activity_cmd import activity  # noqa: E402

app.command()(activity)

from tribalmind.cli.ui_cmd import ui  # noqa: E402

app.command()(ui)

from tribalmind.cli.upgrade_cmd import upgrade  # noqa: E402

app.command()(upgrade)

from tribalmind.cli.agents_cmd import setup_agents  # noqa: E402

app.command("setup-agents")(setup_agents)

from tribalmind.cli.completion_cmd import completion_app  # noqa: E402

app.add_typer(completion_app, name="completion", help="Manage shell completions.")

if __name__ == "__main__":
    app()
