import click
import gitlab
import os
import toml
from zipfile import ZipFile
from yaspin import yaspin
from appdirs import user_config_dir, user_data_dir
from pathlib import Path
import platform
import subprocess

CONFIG_FILE_NAME = "glap.toml"
CONFIG_PATH = user_config_dir("glap") + "/" + CONFIG_FILE_NAME
TMP_PATH = user_data_dir("glap")
PRIVATE_TOKEN_KEY = "private_token"
OAUTH_TOKEN_KEY = "oauth_token"
JOB_TOKEN_KEY = "job_token"


@click.group()
def main():
    pass


@main.command()
@click.argument('namespace')
@click.argument('repository')
@click.option('-o', '--output', default='.', type=click.Path(file_okay=False, dir_okay=True))
@click.option('--ref', default='main', type=click.STRING)
@click.option('-r', '--remote_name', type=click.STRING)
@click.option('-t', '--temp / --no-temp', default=False)
@click.option('-v', '--verbose / --no-verbose', default=False)
@click.option('-s', '--silent / --no-silent', default=False)
@click.option('-j', '--job', type=click.STRING)
def download(namespace, repository, output, ref, job, remote_name, temp, verbose, silent):
    if 'remotes' in config and len(list(config['remotes'])) > 0:
        all_remotes = config['remotes']
        if remote_name and remote_name in all_remotes:
            remote = all_remotes[remote_name]
        else:
            first_remote = list(all_remotes.keys())[0]
            remote = all_remotes[first_remote]

        
        connect_and_download(remote, namespace, repository,
                                ref, job, output, temp, verbose, silent)
    else:
        print("There are no remotes configured!")


def shortcut_command(shortcut):
    shortcut_config = config['shortcuts'][shortcut]
    
    default_remote = shortcut_config.get('remote')
    default_ref = shortcut_config.get('ref', 'main')
    default_job = shortcut_config.get('job')

    @click.option('-j', '--job', default=default_job, type=click.STRING)
    @click.option('--ref', default=default_ref, type=click.STRING)
    @click.option('-t', '--temp / --no-temp', default=False)
    @click.option('-r', '--remote_name', default=default_remote, type=click.STRING)
    @click.option('-o', '--output', default='.',
                  type=click.Path(file_okay=False, dir_okay=True))
    @click.option('-v', '--verbose / --no-verbose', default=False)
    @click.option('-s', '--silent / --no-silent', default=False)
    def f(output, job, ref, remote_name, temp, verbose, silent):
        if remote_name not in config['remotes']:
            print(f"Cannot find remote {remote_name}! Check your remote configuration.")
            return

        remote = config['remotes'][remote_name]

        if 'namespace' not in shortcut_config:
            print(f"No namespace specified for shortcut {shortcut}!")
            return
  
        if 'repository' not in shortcut_config:
            print(f"No repository specified for shortcut {shortcut}!")
            return

        namespace = shortcut_config['namespace']
        repository = shortcut_config['repository']

        connect_and_download(remote, namespace, repository,
                             ref, job, output, temp, verbose, silent)

    return f


def connect_and_download(remote, namespace, repository, ref, job, output, temp, verbose, silent):
    if check_remote(remote):
        try:
            gl = gitlab_instance(remote)
            project = gl.projects.get(f"{namespace}/{repository}", lazy=True)
            if verbose:
                print(
                    f"Job {job}@{ref} from {remote['url']}{namespace}/{repository}")
            download_and_unzip_artifacts(
                project, output, ref, job, temp, verbose, silent)
        except gitlab.GitlabGetError as error:
            print(
                f"Could not find GitLab repository: {error}")
        except Exception as error:
            print(
                f"Error while trying to connect to GitLab repository: {error}")


def check_remote(remote):
    if 'url' not in remote:
        print("Remote is not configured properly: No url specified!")
        return False
    elif len(set(remote).intersection(set([PRIVATE_TOKEN_KEY, OAUTH_TOKEN_KEY, JOB_TOKEN_KEY]))) != 1:
        print("Remote is not configured properly: There must be exactly one authentication token!")
        return False
    else:
        return True


def gitlab_instance(remote):
    url = remote['url']
    private_token = remote.get(PRIVATE_TOKEN_KEY)
    oauth_token = remote.get(OAUTH_TOKEN_KEY)
    job_token = remote.get(JOB_TOKEN_KEY)
    return gitlab.Gitlab(url, private_token, oauth_token, job_token)


def download_and_unzip_artifacts(project, output, ref_name, job, temp, verbose, silent):
    zipfn = "___artifacts.zip"
    success = False

    spinner = yaspin(text="Downloading", color="cyan")
    if not silent:
        spinner.start()

    try:
        with open(zipfn, "wb") as f:
            project.artifacts(ref_name=ref_name, job=job,
                              streamed=True, action=f.write)
        success = True
    except gitlab.exceptions.GitlabGetError as error:
        if not silent:
            spinner.stop()
        print(
            f"Could not download artifacts for job {job}@{ref_name}: {error}!")
    else:
        if not silent:
            spinner.ok("✔")

    if success:
        with ZipFile(zipfn, 'r') as zipObj:
            if temp:
                Path(TMP_PATH).mkdir(parents=True, exist_ok=True)
                [f.unlink() for f in Path(TMP_PATH).glob("*") if f.is_file()]
                output = TMP_PATH

            zip_spinner = yaspin(text="Unzipping", color="cyan")
            if not silent:
                zip_spinner.start()
            zipObj.extractall(output)
            if not silent:
                zip_spinner.ok("✔")

            if verbose and not silent:
                print("Downloaded the following file(s):")
                for filename in zipObj.filelist:
                    print(f"- {filename.filename}")

            if temp:
                open_dir(TMP_PATH)

        os.unlink(zipfn)


def open_dir(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


# Setup from config
if Path(CONFIG_FILE_NAME).is_file():
    config_file = CONFIG_FILE_NAME
elif Path(CONFIG_PATH).is_file():
    config_file = CONFIG_PATH
else:
    config_file = None

if config_file:
    try:
        config = toml.load(config_file)
        if 'shortcuts' in config:
            for shortcut in config['shortcuts']:
                main.command(name=shortcut)(shortcut_command(shortcut))
    except toml.TomlDecodeError as error:
        print(f"Could not decode configuration file {config_file}: {error}!")
        exit(1)
else:
    print(
        f"Could not find a configuration file at {CONFIG_PATH} or ./{CONFIG_FILE_NAME}!")
    exit(1)
