"""TribalMind CLI - root Typer application."""

from __future__ import annotations

import typer

from tribalmind import __version__

app = typer.Typer(
    name="tribal",
    help="TribalMind - Federated Developer Knowledge Agent",
    no_args_is_help=True,
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
    """TribalMind - Federated Developer Knowledge Agent.

    Observes terminal activity, correlates errors with upstream library health,
    and shares validated fixes across your team.
    """
    # Show logo when displaying main help (no subcommand) or for install
    if ctx.invoked_subcommand is None:
        from tribalmind.cli.banner import print_banner  # noqa: E402

        print_banner()
    else:
        # Prompt to upgrade if running an old version (skip when already running upgrade)
        if ctx.invoked_subcommand != "upgrade":
            from tribalmind.cli.version_check import check_and_notify  # noqa: E402

            check_and_notify()


# Register subcommands
from tribalmind.cli.config_cmd import config_app  # noqa: E402

app.add_typer(config_app, name="config", help="Manage TribalMind configuration.")

from tribalmind.cli.daemon_cmd import start, status, stop  # noqa: E402

app.command()(start)
app.command()(stop)
app.command()(status)

from tribalmind.cli.install import install  # noqa: E402

app.command()(install)

from tribalmind.cli.team import enable_team_sharing  # noqa: E402

app.command(name="enable-team-sharing")(enable_team_sharing)

from tribalmind.cli.ui_cmd import ui  # noqa: E402

app.command()(ui)

from tribalmind.cli.watch_cmd import watch_app  # noqa: E402

app.add_typer(watch_app, name="watch", help="Manage watched directories.")

from tribalmind.cli.upgrade_cmd import upgrade  # noqa: E402

app.command()(upgrade)


if __name__ == "__main__":
    app()
