# GitPilot

GitPilot is a Windows-first desktop GitHub manager built with Python + PySide6.
This first working foundation includes:

- Multiple GitHub accounts (personal access tokens stored via the OS keyring)
- Local repository registry
- Git status, branch and remote inspection
- Stage, commit and push
- Clone repositories
- Create GitHub repositories and publish existing local folders
- Create GitHub Releases
- View GitHub Actions workflow runs and rerun failed runs
- Dark desktop UI

## Requirements

- Windows 10/11
- Python 3.10+
- Git for Windows installed and available on PATH

## Run from source

```powershell
cd GitPilot
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py main.py
```

## GitHub token

Create a fine-grained or classic personal access token in GitHub.
For classic tokens, typical scopes are:
- `repo` for private/public repository operations and releases
- `workflow` to rerun GitHub Actions workflows

Add the token in **Accounts → Add account**. GitPilot validates it with GitHub and stores
the secret in Windows Credential Manager through `keyring`. The token is not written to
the JSON settings file.

For fine-grained tokens, grant access to the repositories you want to manage and the
appropriate repository permissions (Contents, Metadata, Actions, and Releases).

## First use

1. Open **Accounts** and add a GitHub account.
2. Open **Repositories** and add an existing local Git repository, or use **Clone**.
3. Select a repository to inspect its changes.
4. Stage all, enter a commit message, then **Commit & Push**.
5. Use **Publish folder** to create a new GitHub repository from a local project folder.

## Security notes

- Tokens are stored through the operating system keyring, not in GitPilot's config file.
- Never paste a token into chat or commit it to a repository.
- GitPilot invokes the installed `git` executable. Review changes before pushing.
- The initial release manager creates a GitHub Release and tag through the GitHub API.
- Actions rerun requires a token with suitable Actions permissions.

## Project layout

```text
GitPilot/
├── main.py
├── requirements.txt
├── gitpilot/
│   ├── app.py
│   ├── config.py
│   ├── github_api.py
│   ├── git_service.py
│   └── ui/
│       ├── main_window.py
│       └── dialogs.py
└── README.md
```

## Current scope / next engineering steps

This is a functional first desktop version, not yet a signed installer. The next milestones
should add background task workers, richer diff/conflict tools, asset upload for releases,
Git LFS helpers, configurable batch profiles, and a packaged Windows installer.
