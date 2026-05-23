import os
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(".nimbus") / "config.yaml"


def _coerce_value(raw: str):
    value = raw.strip()
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    return value


def _parse_simple_yaml(text: str) -> dict:
    data = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = _coerce_value(value)
    return data


def load_nimbus_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    file_config = {}

    if path.exists():
        file_config = _parse_simple_yaml(path.read_text(encoding="utf-8"))

    env_config = {
        "aws_region": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
        "aws_ami_id": os.getenv("NIMBUS_AWS_AMI_ID"),
        "aws_instance_type": os.getenv("NIMBUS_AWS_INSTANCE_TYPE"),
        "aws_key_name": os.getenv("NIMBUS_AWS_KEY_NAME"),
        "aws_subnet_id": os.getenv("NIMBUS_AWS_SUBNET_ID"),
        "aws_security_group_id": os.getenv("NIMBUS_AWS_SECURITY_GROUP_ID"),
        "base_domain": os.getenv("NIMBUS_BASE_DOMAIN"),
        "route53_hosted_zone_id": os.getenv("NIMBUS_ROUTE53_HOSTED_ZONE_ID"),
        "github_token": os.getenv("GITHUB_TOKEN") or os.getenv("NIMBUS_GITHUB_TOKEN"),
        "github_owner": os.getenv("NIMBUS_GITHUB_OWNER"),
        "github_visibility": os.getenv("NIMBUS_GITHUB_VISIBILITY"),
    }

    merged = dict(file_config)
    for key, value in env_config.items():
        if value not in (None, ""):
            merged[key] = value

    return merged
