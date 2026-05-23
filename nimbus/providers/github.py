import json
from urllib import error, request

from nimbus.config import load_nimbus_config
from nimbus.providers.base import ProviderAdapter, ProvisioningResult


class GitHubAdapter(ProviderAdapter):
    provider_name = "github"

    def __init__(self, config: dict | None = None):
        self.config = config or load_nimbus_config()

    def provision(self, record: dict, resource: dict) -> ProvisioningResult:
        token = self.config.get("github_token")
        existing = resource.get("details", {})
        if not token:
            if existing.get("repo_url"):
                return ProvisioningResult(
                    provider=self.provider_name,
                    resource_type=resource["type"],
                    service=resource["service"],
                    status="created",
                    message="GitHub repository already exists for this project.",
                    details={
                        "repo_url": existing.get("repo_url"),
                        "clone_url": existing.get("clone_url"),
                        "full_name": existing.get("full_name"),
                        "visibility": existing.get("visibility", "private"),
                    },
                )
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="failed",
                message="GitHub repo creation requires GITHUB_TOKEN or NIMBUS_GITHUB_TOKEN.",
                details={},
            )

        repo_name = resource["details"]["repo_name"]
        visibility = (
            self.config.get("github_visibility")
            or resource["details"].get("visibility")
            or "private"
        )
        private = visibility != "public"
        owner = self.config.get("github_owner")

        url = "https://api.github.com/user/repos"
        if owner:
            url = f"https://api.github.com/orgs/{owner}/repos"

        payload = json.dumps(
            {
                "name": repo_name,
                "private": private,
                "auto_init": True,
                "description": f"Nimbus project for {record['project']['name']}",
            }
        ).encode("utf-8")

        req = request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "nimbus-cli",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 422 and "name already exists on this account" in body:
                repo_url = existing.get("repo_url") or f"https://github.com/{owner or body}/{repo_name}"
                clone_url = existing.get("clone_url") or f"{repo_url}.git"
                full_name = existing.get("full_name") or f"{owner}/{repo_name}" if owner else repo_name
                return ProvisioningResult(
                    provider=self.provider_name,
                    resource_type=resource["type"],
                    service=resource["service"],
                    status="created",
                    message="GitHub repository already exists for this account.",
                    details={
                        "repo_url": repo_url,
                        "clone_url": clone_url,
                        "full_name": full_name,
                        "visibility": visibility,
                    },
                )
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="failed",
                message=f"GitHub API error {exc.code}: {body}",
                details={},
            )
        except error.URLError as exc:
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="failed",
                message=f"GitHub API request failed: {exc.reason}",
                details={},
            )

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message="GitHub repository created successfully.",
            details={
                "repo_url": body.get("html_url"),
                "clone_url": body.get("clone_url"),
                "full_name": body.get("full_name"),
                "visibility": body.get("visibility", visibility),
            },
        )
