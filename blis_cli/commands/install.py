import click
import glob
import os
import docker as lib_docker
import shutil

from blis_cli.util import bash
from blis_cli.util import config
from blis_cli.util import docker_util as docker
from blis_cli.util import environment as env
from blis_cli.util import packages


def install():
    if not docker.installed():
        click.secho("You must install Docker before continuing. Please run:", fg="red")
        click.echo("  sudo blis docker install")
        return 1

    if not env.in_docker_grp():
        click.secho("You must be in the Docker group to continue. Please run", fg="red")
        click.echo("  sudo blis docker install")
        return 1

    # We have Docker installed and we are in the docker group.
    version = lib_docker.from_env().version()
    click.echo(f"Docker version: {click.style(version['Version'], fg='green')}")

    if os.path.exists(config.compose_file()):
        if not click.confirm(
            "BLIS has already been installed in ~/.blis. Do you want to overwrite the configuration?"
        ):
            return 0

    config.make_basedir()
    copy_docker_files()

    if config.validate_compose():
        click.echo("docker-compose.yml is valid.")
    else:
        click.secho("docker-compose.yml is not valid.", fg="red")
        return 1

    run_blis_and_setup_db()

    click.secho("You are ready to rock!", fg="green")
    click.echo("Run `blis start` to start BLIS!")


def copy_docker_files():
    click.echo("Copying docker-compose.yml to ~/.blis/...")
    shutil.copy(
        f"{os.path.dirname(__file__)}/../extra/docker-compose.yml",
        config.compose_file(),
    )


def run_blis_and_setup_db():
    click.echo("Starting BLIS database... ", nl=False)
    out, err = bash.run(
        f"{docker.compose()} -f {config.compose_file()} up -d --wait db"
    )
    if err:
        click.secho("Failed", fg="red")
        click.echo(err, err=True)
        return False

    click.secho("Success!", fg="green")

    db_password = config.compose_key("services.db.environment.MYSQL_ROOT_PASSWORD")
    seed_failed = False

    for file in glob.glob(f"{os.path.dirname(__file__)}/../extra/*.sql"):
        click.echo(f"Seeding {os.path.basename(file)}... ", nl=False)
        out, err = bash.run(
            f"{docker.compose()} -f {config.compose_file()} exec -T db mysql -hdb -uroot -p{db_password} < {file}"
        )
        if err:
            click.secho("Failed", fg="red")
            click.echo(err, err=True, nl=False)
            seed_failed = True
        else:
            click.secho("Success!", fg="green")

    if seed_failed:
        click.secho("Seeding database failed.", fg="yellow")
        click.echo("BLIS might still start. Please check the errors for details.")

    click.echo("Stopping database... ", nl=False)
    out, err = bash.run(f"{docker.compose()} -f {config.compose_file()} down")
    if err:
        click.secho("Failed", fg="red")
        click.echo(err, err=True)
        return False

    click.secho("Success!", fg="green")
