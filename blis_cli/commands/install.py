import click
import os
import docker as lib_docker
import requests

from blis_cli.util import bash
from blis_cli.util import config
from blis_cli.util import docker_util as docker
from blis_cli.util import emoji
from blis_cli.util import environment as env
from blis_cli.util import packages


def install():
    # If Docker is installed, and we are in the docker group, we will not need root privileges.
    if not (env.in_docker_grp() and docker.installed()):
        if not (os.geteuid() == 0 or env.can_sudo()):
            click.secho(
                "Docker must be installed. You must run this script as root or have passwordless sudo privileges.", fg="red")
            return 1

        install_docker()

        # Returns a success code because we probably succeeded and installed Docker, but we need to log out and log back in.
        return 0

    # We might have Docker installed, but not be in the docker group.
    if docker.installed() and not env.in_docker_grp():
        click.secho("You have Docker installed, but you are not in the docker group.",
                    fg="yellow")
        # Try to fix the problem...
        if (env.can_sudo()):
            bash.sudo("usermod -aG docker $USER")
            click.echo(
                "Please log out and log back in, and run this command again.")
            return 0
        else:
            click.secho(
                "You must run this script as root or have passwordless sudo privileges.", fg="red")
        return 1

    # We have Docker installed and we are in the docker group.
    version = lib_docker.from_env().version()
    click.echo(
        f"Docker version: {click.style(version['Version'], fg='green')}")

    config.make_basedir()
    if not os.path.exists(config.compose_file()):
        download_docker_files()

    if config.validate_compose():
        click.echo("docker-compose.yml is valid.")
    else:
        click.secho(
            "docker-compose.yml is not valid.", fg="red")
        return 1

    click.secho("You are ready to rock!", fg="green")


def install_docker():
    click.echo("Setting up Docker... ", nl=False)
    packages.remove(["docker", "docker-engine",
                    "docker.io", "containerd", "runc"])
    packages.install(["ca-certificates", "curl", "gnupg", "lsb-release"])
    bash.sudo("mkdir -p /etc/apt/keyrings")
    bash.run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o - | sudo tee /etc/apt/keyrings/docker.gpg >/dev/null")
    bash.run("echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null")
    packages.install(["docker-ce", "docker-ce-cli", "containerd.io",
                     "docker-compose-plugin", "docker-buildx-plugin"])
    bash.sudo("usermod -aG docker $USER")
    click.secho("Success!", fg="green")
    click.echo("Please log out and log back in, and run this command again.")


def download_docker_files():
    click.echo("Downloading docker-compose.yml... ", nl=False)
    r = requests.get(
        "https://raw.githubusercontent.com/C4G/BLIS/master/docker/docker-compose.yml")
    if r.status_code != 200:
        click.secho("Failed to download docker-compose.yml", fg="red")
        return False
    with open(config.compose_file(), "wb") as f:
        f.write(r.content)
    click.secho("Success!", fg="green")