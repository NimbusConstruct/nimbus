import os
from pathlib import Path

from nimbus.config import DEFAULT_CONFIG_PATH, load_nimbus_config


def _has_shared_aws_profile() -> bool:
    credentials_path = Path.home() / ".aws" / "credentials"
    config_path = Path.home() / ".aws" / "config"
    return credentials_path.exists() or config_path.exists()


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def run_doctor() -> list[dict]:
    config = load_nimbus_config()
    checks = []

    checks.append(
        _check(
            "config_file",
            DEFAULT_CONFIG_PATH.exists(),
            f"Expected config at {DEFAULT_CONFIG_PATH}",
        )
    )

    checks.append(
        _check(
            "boto3",
            _has_boto3(),
            "Install and run through the same interpreter Nimbus uses for provisioning.",
        )
    )

    checks.append(
        _check(
            "aws_region",
            bool(config.get("aws_region")),
            "Set AWS_REGION, AWS_DEFAULT_REGION, or aws_region in .nimbus/config.yaml",
        )
    )
    checks.append(
        _check(
            "aws_credentials",
            bool(
                (config.get("aws_access_key_id") and config.get("aws_secret_access_key"))
                or _has_shared_aws_profile()
            ),
            "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or rely on your AWS profile chain.",
        )
    )
    checks.append(
        _check(
            "aws_ami_id",
            bool(config.get("aws_ami_id")),
            "Needed for container deployments that launch EC2 instances.",
        )
    )
    checks.append(
        _check(
            "route53_hosted_zone_id",
            bool(config.get("route53_hosted_zone_id")),
            "Needed for Route53 record creation in serverless flows.",
        )
    )
    checks.append(
        _check(
            "github_token",
            bool(config.get("github_token")),
            "Set GITHUB_TOKEN or NIMBUS_GITHUB_TOKEN for GitHub repo creation.",
        )
    )

    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    proxy_ok = not any(proxy == "http://127.0.0.1:9" for proxy in [http_proxy, https_proxy] if proxy)
    checks.append(
        _check(
            "proxy",
            proxy_ok,
            "Current shell should not point HTTP_PROXY/HTTPS_PROXY at http://127.0.0.1:9 for AWS/GitHub calls.",
        )
    )

    return checks


def _has_boto3() -> bool:
    try:
        import boto3  # noqa: F401
    except ImportError:
        return False
    return True


def format_doctor_report() -> str:
    checks = run_doctor()
    passed = sum(1 for check in checks if check["ok"])
    total = len(checks)

    lines = [
        "Nimbus Doctor",
        f"Checks passed: {passed}/{total}",
        "",
    ]

    for check in checks:
        status = "OK" if check["ok"] else "MISSING"
        lines.append(f"[{status}] {check['name']}: {check['detail']}")

    lines.extend(
        [
            "",
            "Recommended command:",
            "  pipenv run python -m nimbus project provision <project-id>",
        ]
    )

    if not DEFAULT_CONFIG_PATH.exists():
        example_path = Path(".nimbus") / "config.example.yaml"
        lines.extend(
            [
                "",
                "Quick start:",
                f"  Copy {example_path} to {DEFAULT_CONFIG_PATH}",
            ]
        )

    return "\n".join(lines)
