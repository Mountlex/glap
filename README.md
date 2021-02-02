# glap

![Python package](https://github.com/Mountlex/glap/workflows/Python%20package/badge.svg)
![PyPI](https://img.shields.io/pypi/v/glap)

A GitLab Artifact Puller / Downloader

## Quick Start

`glap` is a convenience tool to download artifacts of your frequently used GitLab repositories. Install via

```bash
pip install glap
```

Before you can use `glap`, you have to setup a configuration file named `glap.toml`. `glap` searches the file at the following locations (in this order):

1. `./glap.toml`
2. `~/.config/glap/glap.toml` (default location for configuration files on your OS; here for Linux)

It contains the following information:

* Remotes with corresponding `url`s and access-tokens:

```toml
[remotes.myremote]
url = "https://gitlab.com"
private_token = "<my-private-token>"
oauth_token = "<my-oauth-token>"
job_token = "<my-job-token>"
```

Note that there must be exactly one authentication token specified.

* Shortcuts for specific repositories. For example, the following shortcut points at the `PDFs` job of the `main` branch of `https://gitlab.com/name/repo`.

```toml
[shortcuts.myshortcut]
remote = "myremote"
namespace = "name"
repository = "repo"
ref = "main"
job = "PDFs"
```

Any configured shortcut will appear as a subcommand, i.e. you can use it as follows

```bash
glap myshortcut
```

Alternatively, you can specify the namespace and repository directly

```bash
glap download <namespace> <repository> -j <job> --ref <branch or tag>
```

If no remote is given, `glap` will use the first one in the configuration file. Otherwise, you can use

```bash
glap download <namespace> <repository> -r myremote
```

where `myremote` is the name of the remote in the configuration file.

### Options

* `--job` (`-j`) specifies the job's name.
* `--ref` specifies the name of the branch or tag from where the job is located.
* `--output` (`-o`) specifies the download location.
* `--temp` (`-t`) downloads the artifact to a temporary location and opens the directory.
* `--silent` (`-s`) enables silent mode (exceptions only).
* `--verbose` (`-v`) enables verbose mode (e.g. print file list).
  