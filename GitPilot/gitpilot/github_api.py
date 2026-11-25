import requests

API = "https://api.github.com"

class GitHubError(RuntimeError):
    pass

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitPilot"
        })

    def request(self, method, endpoint, **kwargs):
        url = endpoint if endpoint.startswith("https://") else API + endpoint
        response = self.session.request(method, url, timeout=30, **kwargs)
        if not response.ok:
            try:
                detail = response.json().get("message", response.text)
            except Exception:
                detail = response.text
            raise GitHubError(f"GitHub API {response.status_code}: {detail}")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def user(self):
        return self.request("GET", "/user")

    def repositories(self):
        result, page = [], 1
        while page <= 5:
            batch = self.request("GET", "/user/repos", params={
                "per_page": 100, "page": page, "sort": "updated", "affiliation": "owner,collaborator,organization_member"
            })
            result.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return result

    def create_repo(self, name, private=True, description=""):
        return self.request("POST", "/user/repos", json={
            "name": name, "private": private, "description": description,
            "auto_init": False
        })

    def create_release(self, owner, repo, tag, title, notes, target="main", prerelease=False):
        return self.request("POST", f"/repos/{owner}/{repo}/releases", json={
            "tag_name": tag, "target_commitish": target, "name": title,
            "body": notes, "draft": False, "prerelease": prerelease
        })

    def workflow_runs(self, owner, repo):
        data = self.request("GET", f"/repos/{owner}/{repo}/actions/runs",
                            params={"per_page": 30})
        return data.get("workflow_runs", [])

    def rerun_failed(self, owner, repo, run_id):
        return self.request("POST", f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed")

    @staticmethod
    def owner_repo(remote_url):
        value = remote_url.strip()
        if value.endswith(".git"):
            value = value[:-4]
        if value.startswith("git@github.com:"):
            value = value.split(":", 1)[1]
        elif "github.com/" in value:
            value = value.split("github.com/", 1)[1]
        else:
            return None, None
        parts = value.strip("/").split("/")
        return (parts[0], parts[1]) if len(parts) >= 2 else (None, None)
