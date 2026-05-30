import base64
import json
from urllib import error, request

from nimbus.config import load_nimbus_config


def _github_request(url: str, token: str, method: str = "GET", payload: dict | None = None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nimbus-cli",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def _put_file(owner: str, repo: str, path: str, content: str, message: str, token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    sha = None
    try:
        existing = _github_request(url, token, method="GET")
        sha = existing.get("sha")
    except error.HTTPError as exc:
        if exc.code != 404:
            raise

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "committer": {
            "name": "Nimbus",
            "email": "nimbus@local.dev",
        },
    }
    if sha:
        payload["sha"] = sha

    _github_request(url, token, method="PUT", payload=payload)


def _site_files(project_id: str, domain: str, distribution_domain: str | None):
    cname = distribution_domain or domain
    workflow = f"""name: Deploy Static Site

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate site files
        run: |
          test -f index.html
          test -f styles.css
          test -f script.js
  summary:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Deployment summary
        run: |
          echo "GitHub Pages-style static assets are ready."
          echo "CloudFront target: {cname}"
"""

    index_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{project_id}</title>
    <link rel="stylesheet" href="styles.css">
  </head>
  <body>
    <main class="hero">
      <p class="eyebrow">Nimbus Provisioned</p>
      <h1>{project_id}</h1>
      <p class="lede">This site was bootstrapped by Nimbus and is ready for content and deployment polish.</p>
      <div class="meta">
        <span>Domain: {domain}</span>
        <span>CDN: {distribution_domain or "pending"}</span>
      </div>
      <button id="pulse">Check deployment</button>
      <p id="status">Static starter is online.</p>
    </main>
    <script src="script.js"></script>
  </body>
</html>
"""

    styles_css = """html, body {
  margin: 0;
  min-height: 100%;
  font-family: Georgia, "Times New Roman", serif;
  background:
    radial-gradient(circle at top, #f6ede0 0%, #efe3d0 35%, #d6c2a4 100%);
  color: #1f1710;
}

.hero {
  max-width: 52rem;
  margin: 0 auto;
  padding: 6rem 1.5rem 4rem;
}

.eyebrow {
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.8rem;
}

h1 {
  font-size: clamp(3rem, 8vw, 6rem);
  margin: 0.4rem 0 1rem;
}

.lede {
  max-width: 40rem;
  font-size: 1.2rem;
  line-height: 1.6;
}

.meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 2rem 0;
  font-size: 0.95rem;
}

button {
  border: 0;
  background: #1f1710;
  color: #f6ede0;
  padding: 0.9rem 1.2rem;
  cursor: pointer;
}

#status {
  margin-top: 1rem;
}
"""

    script_js = """const button = document.getElementById('pulse');
const status = document.getElementById('status');

button.addEventListener('click', () => {
  const stamp = new Date().toLocaleString();
  status.textContent = `Nimbus bootstrap verified at ${stamp}.`;
});
"""

    readme = f"""# {project_id}

This repository was bootstrapped by Nimbus.

## Files

- `index.html`: starter page
- `styles.css`: starter styling
- `script.js`: small interaction hook
- `.github/workflows/deploy-static-site.yml`: placeholder CI workflow

## Provisioned target

- Domain: `{domain}`
- CloudFront: `{distribution_domain or "pending"}`
"""

    gitignore = """*.log
.DS_Store
"""

    return {
        "README.md": readme,
        "index.html": index_html,
        "styles.css": styles_css,
        "script.js": script_js,
        ".gitignore": gitignore,
        ".github/workflows/deploy-static-site.yml": workflow,
    }


def bootstrap_repository(record: dict) -> dict:
    config = load_nimbus_config()
    token = config.get("github_token")
    if not token:
        raise RuntimeError("GitHub bootstrap requires GITHUB_TOKEN or NIMBUS_GITHUB_TOKEN.")

    github_resource = next(
        resource for resource in record["deployment"]["plan"]["resources"]
        if resource["type"] == "github_repository"
    )
    dns_resource = next(
        resource for resource in record["deployment"]["plan"]["resources"]
        if resource["type"] == "dns"
    )
    cloudfront_resource = next(
        (resource for resource in record["deployment"]["plan"]["resources"]
         if resource["type"] == "cloudfront_distribution"),
        None,
    )

    full_name = github_resource["details"]["full_name"]
    owner, repo = full_name.split("/", 1)
    domain = dns_resource["details"]["record_name"]
    distribution_domain = None
    if cloudfront_resource:
        distribution_domain = cloudfront_resource["details"].get("distribution_domain_name")

    files = _site_files(record["project"]["id"], domain, distribution_domain)
    for path, content in files.items():
        _put_file(owner, repo, path, content, f"Bootstrap {path}", token)

    return {
        "repo": full_name,
        "files": sorted(files.keys()),
        "domain": domain,
        "distribution_domain": distribution_domain,
    }
