import click

from blis_cli.util import bash
from blis_cli.util import config
from blis_cli.util import docker_util as docker


def run():
    click.echo("Starting BLIS database... ", nl=False)
    out, err = bash.run(
        f"{docker.compose()} -f {config.compose_file()} up -d --wait db"
    )
    if err:
        click.secho("Failed", fg="red")
        click.echo(err, err=True)
        return 1

    click.secho("Success!", fg="green")

    click.echo("Starting BLIS... ", nl=False)
    out, err = bash.run(
        f"{docker.compose()} -f {config.compose_file()} up -d --wait app"
    )
    if err:
        click.secho("Failed", fg="red")
        click.echo(err, err=True)
        return 1

    click.secho("Success!", fg="green")

    return 0
