from os import name
import click
import gitlab
import os
import toml
from zipfile import ZipFile
from yaspin import yaspin
from pathlib import Path


@click.group()
def main():
    pass

@main.command()
@click.argument('namespace')
@click.argument('repository')
@click.option('-o', '--output', default='.', type=click.Path(file_okay=False, dir_okay=True))
@click.option('-b', '--branch', default='main', type=click.STRING)
@click.option('-r', '--remote_name', type=click.STRING)
@click.option('-j', '--job', default='PDFs', type=click.STRING)
def download(namespace, repository, output, branch, job, remote_name):
    if 'remotes' in config and len(list(config['remotes'])) > 0:
        all_remotes = config['remotes']
        if remote_name and remote_name in all_remotes:
            remote = all_remotes[remote_name]
        else:
            first_remote = list(all_remotes.keys())[0]
            remote = all_remotes[first_remote]
        
        connect_and_download(remote, namespace, repository, branch, job, output)
    else:
        print("There are no remotes configured!")

def shortcut_command(shortcut):
    shortcut_config = config['shortcuts'][shortcut]
    remote_name = shortcut_config['remote']
    default_branch = shortcut_config['branch']
    default_job = shortcut_config['job']
    @click.option('-j', '--job', default=default_job, type=click.STRING)
    @click.option('-b', '--branch', default=default_branch, type=click.STRING)
    @click.option('-o', '--output', default='.', type=click.Path(file_okay=False, dir_okay=True))
    def f(output, job, branch):
        remote = config['remotes'][remote_name]
        namespace = shortcut_config['namespace']
        repository = shortcut_config['repository'] 

        connect_and_download(remote, namespace, repository, branch, job, output)
  
    return f

def connect_and_download(remote, namespace, repository, branch, job, output):
    if check_remote(remote):
        try:
            gl = gitlab_instance(remote)  
            project = gl.projects.get(f"{namespace}/{repository}")
            download_and_unzip_artifacts(project, output, branch, job)
        except gitlab.GitlabGetError:
            print(f"Could not find GitLab repository at {remote['url']}/{namespace}/{repository}")

def check_remote(remote):
    if 'url' in remote and 'token' in remote:
        return True
    else:
        print("Remote is not configured properly!")
        return False

def gitlab_instance(remote):
    url = remote['url']
    token = remote['token']
    return gitlab.Gitlab(url, private_token=token)

def download_and_unzip_artifacts(project, output, branch, job):
    zipfn = f"___artifacts.zip"
    success = False
    with yaspin(text="Downloading", color="cyan") as spinner:
        try:
            with open(zipfn, "wb") as f:
                project.artifacts(ref_name=branch, job=job, streamed=True, action=f.write)
            success = True   
        except gitlab.exceptions.GitlabGetError:
            spinner.stop();
            print(f"Could not download artifacts for branch {branch} and job {job}!")
        else:
            spinner.ok("✔");

    if success:
        with ZipFile(zipfn, 'r') as zipObj:
            with yaspin(text="Unzipping", color="cyan") as spinner: 
                zipObj.extractall(output)
                spinner.ok("✔");
            
            print("Downloaded the following file(s):")
            for filename in zipObj.filelist:
                print(f"{output}/{filename.filename}")
        
        os.unlink(zipfn)


# Setup from config

CONFIG_PATH = Path.home() / ".config/glap/glap.toml"
try:
    config = toml.load(CONFIG_PATH)
    if 'shortcuts' in config:
        for shortcut in config['shortcuts']:
            main.command(name=shortcut)(shortcut_command(shortcut))
except FileNotFoundError or FileExistsError:
    print("Could not find configuration file!")
    exit(1)


