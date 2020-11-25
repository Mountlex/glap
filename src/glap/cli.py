import click
import gitlab
import subprocess
import os
import toml

config = toml.load('config.toml')

@click.group()
def main():
    pass

@main.command()
@click.argument('namespace')
@click.argument('project_id')
@click.option('-o', '--output', default='.', type=click.Path(file_okay=False, dir_okay=True))
@click.option('-b', '--branch', default='main', type=click.STRING)
@click.option('-r', '--remote', type=click.STRING)
@click.option('-j', '--job', default='PDFs', type=click.STRING)
def download(namespace, project_id, output, dry, branch, job, remote):
    all_remotes = config['remotes']
    if remote and remote in all_remotes:
        repo = all_remotes[remote]
    else:
        first_repo = list(all_remotes.keys())[0]
        repo = all_remotes[first_repo]

    gl = gitlab_instance(repo)  
    project = gl.projects.get(f"{namespace}/{project_id}")
    download_and_unzip_artifacts(project, output, branch, job)

def shortcut_command(shortcut):
    shortcut_config = config['shortcuts'][shortcut]
    remote = shortcut_config['remote']
    default_branch = shortcut_config['branch']
    default_job = shortcut_config['job']
    @click.option('-j', '--job', default=default_job, type=click.STRING)
    @click.option('-b', '--branch', default=default_branch, type=click.STRING)
    @click.option('-o', '--output', default='.', type=click.Path(file_okay=False, dir_okay=True))
    def f(output, job, branch):
        repo = config['remotes'][remote]
        namespace = shortcut_config['namespace']
        project_id = shortcut_config['project'] 

        gl = gitlab_instance(repo)  
        project = gl.projects.get(f"{namespace}/{project_id}")
        download_and_unzip_artifacts(project, output, branch, job)
    return f

def gitlab_instance(repo):
    url = repo['url']
    token = repo['token']

    return gitlab.Gitlab(url, private_token=token)

def download_and_unzip_artifacts(project, output, branch, job):
    zipfn = f"___artifacts.zip"
    try:
        with open(zipfn, "wb") as f:
            project.artifacts(ref_name=branch, job=job, streamed=True, action=f.write)       
    except gitlab.exceptions.GitlabGetError:
        print(f"Could not download artifacts for branch {branch} and job {job}!")
    
    subprocess.run(["unzip", "-bo", zipfn, "-d", output])
    os.unlink(zipfn)


for shortcut in config['shortcuts']:
    main.command(name=shortcut)(shortcut_command(shortcut))
