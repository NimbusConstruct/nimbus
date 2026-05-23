import json
import os
import re
from datetime import datetime

from nimbus.comparison import get_top_architectures
from nimbus.config import load_nimbus_config
from nimbus.costs import estimate_cost
from nimbus.engine import SmartArchitectureEngine
from nimbus.explainer import get_explanation


PROJECTS_DIR = "projects"


def slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "project"


def normalize_project_input(project: dict) -> dict:
    normalized = dict(project)

    app_type = str(normalized.get("app_type", "dynamic")).strip().lower()
    if app_type == "static":
        app_type = "brochure"
    normalized["app_type"] = app_type

    scale = str(normalized.get("user_scale", "medium")).strip().lower()
    if scale == "low":
        scale = "small"
    elif scale == "high":
        scale = "large"
    normalized["user_scale"] = scale

    deployment = str(normalized.get("deployment", "container")).strip().lower()
    normalized["deployment"] = deployment

    integrations = normalized.get("integrations", [])
    normalized["integrations"] = sorted(
        {str(item).strip().lower() for item in integrations if str(item).strip()}
    )

    for key in ["auth_required", "real_time", "sensitive_data", "compliance"]:
        normalized[key] = bool(normalized.get(key, False))

    return normalized


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _append_activity(record: dict, event: dict) -> None:
    activity = record["status"].setdefault("activity", [])
    activity.append({"timestamp": _timestamp(), **event})


def _project_domain(project_name: str) -> str:
    config = load_nimbus_config()
    base_domain = str(config.get("base_domain") or "example.com").strip()
    return f"{project_name}.{base_domain}"


def _deployment_plan(project_name: str, project: dict) -> dict:
    deployment = project["deployment"]
    region = "us-west-1"
    project_domain = _project_domain(project_name)

    if deployment == "container":
        return {
            "provider": "aws",
            "mode": "planned",
            "notes": [
                "Container deployments currently target a single EC2 host first.",
                "Microservices-specific orchestration is deferred for a later phase.",
            ],
            "resources": [
                {
                    "type": "ec2_instance",
                    "service": "EC2",
                    "status": "pending",
                    "region": region,
                    "details": {
                        "instance_name": f"{project_name}-app",
                        "suggested_instance_type": "t3.small",
                        "ami_strategy": "amazon-linux-2023",
                        "instance_id": None,
                        "public_dns": None,
                        "public_ip": None,
                    },
                }
            ],
        }

    if deployment == "serverless":
        return {
            "provider": "aws_github",
            "mode": "planned",
            "notes": [
                "Static/serverless web delivery is modeled as a GitHub-backed site.",
                "Provisioning intent is captured here; API integrations can be added later.",
                "ACM certificates are requested and DNS-validated here, but HTTPS delivery for S3 websites still needs CloudFront.",
            ],
            "resources": [
                {
                    "type": "github_repository",
                    "service": "GitHub",
                    "status": "pending",
                    "details": {
                        "repo_name": project_name,
                        "visibility": "private",
                        "repo_url": None,
                        "clone_url": None,
                        "full_name": None,
                    },
                },
                {
                    "type": "storage_bucket",
                    "service": "S3",
                    "status": "pending",
                    "region": region,
                    "details": {
                        "bucket_name": f"{project_name}-site",
                        "website_hosting": True,
                        "bucket_arn": None,
                        "website_url": None,
                    },
                },
                {
                    "type": "certificate",
                    "service": "ACM",
                    "status": "pending",
                    "region": "us-east-1",
                    "details": {
                        "validation": "dns",
                        "domain": project_domain,
                        "certificate_arn": None,
                        "certificate_region": "us-east-1",
                        "validation_record_name": None,
                        "validation_record_type": None,
                        "validation_record_value": None,
                    },
                },
                {
                    "type": "cloudfront_distribution",
                    "service": "CloudFront",
                    "status": "pending",
                    "details": {
                        "distribution_id": None,
                        "distribution_domain_name": None,
                        "distribution_hosted_zone_id": "Z2FDTNDATAQYW2",
                        "origin_domain_name": f"{project_name}-site.s3-website-{region}.amazonaws.com",
                        "alias_domain": project_domain,
                    },
                },
                {
                    "type": "dns",
                    "service": "Route53",
                    "status": "pending",
                    "details": {
                        "record_name": project_domain,
                        "target": None,
                        "record_type": "A",
                        "change_id": None,
                        "hosted_zone_id": None,
                        "alias": True,
                    },
                },
            ],
        }

    return {
        "provider": "aws",
        "mode": "planned",
        "notes": ["Provisioning workflow for this deployment type is not defined yet."],
        "resources": [],
    }


def build_project_record(project_name: str, project_input: dict) -> dict:
    project = normalize_project_input(project_input)
    engine = SmartArchitectureEngine(project)
    result = engine.analyze()
    recommended = result["recommended"]
    explanation = get_explanation(recommended)
    top_options = []

    for arch, data in get_top_architectures(result["details"]):
        cost = estimate_cost(project, arch)
        top_options.append(
            {
                "architecture": arch,
                "score": data["score"],
                "confidence": data["confidence"],
                "estimated_monthly_cost_usd": cost["total"],
            }
        )

    created_at = _timestamp()
    project_id = slugify_name(project_name)

    return {
        "project": {
            "id": project_id,
            "name": project_name,
            "created_at": created_at,
            "updated_at": created_at,
            "input": project,
        },
        "analysis": {
            "recommended_architecture": recommended,
            "explanation": explanation,
            "reasons": result["explanation"],
            "top_options": top_options,
            "cost_estimate": estimate_cost(project, recommended),
        },
        "deployment": {
            "type": project["deployment"],
            "plan": _deployment_plan(project_id, project),
        },
        "status": {
            "state": "planned",
            "provisioning": "not_started",
            "generated_outputs": [],
            "last_updated": created_at,
            "activity": [
                {
                    "timestamp": created_at,
                    "event": "project_created",
                    "message": "Project record created.",
                }
            ],
        },
    }


def _scalar_to_yaml(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def to_yaml(value, indent: int = 0) -> str:
    pad = " " * indent

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_scalar_to_yaml(item)}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {_scalar_to_yaml(item)}")
        return "\n".join(lines)

    return f"{pad}{_scalar_to_yaml(value)}"


def write_project_files(project_name: str, record: dict, projects_dir: str = PROJECTS_DIR) -> dict:
    project_id = record["project"]["id"]
    project_dir = os.path.join(projects_dir, project_id)
    os.makedirs(project_dir, exist_ok=True)

    yaml_path = os.path.join(project_dir, "project.yaml")
    json_path = os.path.join(project_dir, "project.json")
    legacy_json_path = os.path.join(projects_dir, f"{project_id}.json")

    with open(yaml_path, "w", encoding="utf-8") as handle:
        handle.write(to_yaml(record))
        handle.write("\n")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)

    with open(legacy_json_path, "w", encoding="utf-8") as handle:
        json.dump(record["project"]["input"], handle, indent=2)

    return {
        "project_dir": project_dir,
        "yaml_path": yaml_path,
        "json_path": json_path,
        "legacy_json_path": legacy_json_path,
    }


def save_project_record(record: dict, projects_dir: str = PROJECTS_DIR) -> dict:
    record["project"]["updated_at"] = _timestamp()
    record["status"]["last_updated"] = record["project"]["updated_at"]
    return write_project_files(record["project"]["name"], record, projects_dir=projects_dir)


def record_provisioning_attempt(record: dict, activity: list[dict]) -> dict:
    for item in activity:
        _append_activity(
            record,
            {
                "event": "provisioning_step",
                "service": item["service"],
                "resource_type": item["resource_type"],
                "status": item["status"],
                "message": item["message"],
            },
        )
    return record


def mark_provisioning_started(record: dict) -> dict:
    _append_activity(
        record,
        {
            "event": "provisioning_started",
            "message": "Provisioning run started.",
        },
    )
    return record


def mark_bootstrap_event(record: dict, message: str) -> dict:
    _append_activity(
        record,
        {
            "event": "bootstrap",
            "message": message,
        },
    )
    return record


def load_project_record_by_name(project_ref: str, projects_dir: str = PROJECTS_DIR) -> dict:
    raw_ref = project_ref.replace(".json", "").strip()
    candidate_ids = [raw_ref]
    slug_candidate = slugify_name(raw_ref)
    if slug_candidate not in candidate_ids:
        candidate_ids.append(slug_candidate)

    for project_id in candidate_ids:
        json_path = os.path.join(projects_dir, project_id, "project.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        legacy_json_path = os.path.join(projects_dir, f"{project_id}.json")
        if os.path.exists(legacy_json_path):
            with open(legacy_json_path, "r", encoding="utf-8") as handle:
                project = json.load(handle)
            return build_project_record(project_id, project)

    raise FileNotFoundError(f"Project '{project_ref}' was not found in {projects_dir}")


def load_project_record_from_yaml(yaml_path: str) -> dict:
    project_dir = os.path.dirname(os.path.abspath(yaml_path))
    json_path = os.path.join(project_dir, "project.json")

    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"Could not find companion project.json for YAML file: {yaml_path}"
        )

    with open(json_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_projects(projects_dir: str = PROJECTS_DIR) -> list[dict]:
    projects = []
    if not os.path.exists(projects_dir):
        return projects

    for entry in sorted(os.listdir(projects_dir)):
        json_path = os.path.join(projects_dir, entry, "project.json")
        if not os.path.exists(json_path):
            continue
        with open(json_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        projects.append(
            {
                "id": record["project"]["id"],
                "name": record["project"]["name"],
                "deployment": record["deployment"]["type"],
                "state": record["status"]["state"],
                "provisioning": record["status"]["provisioning"],
                "recommended_architecture": record["analysis"]["recommended_architecture"],
                "updated_at": record["status"]["last_updated"],
            }
        )

    return projects


def format_project_list(items: list[dict]) -> str:
    if not items:
        return "No projects found."

    lines = ["Nimbus Projects", ""]
    for item in items:
        lines.append(
            f"- {item['id']}: {item['name']} | {item['deployment']} | "
            f"{item['state']} | {item['recommended_architecture']} | {item['updated_at']}"
        )
    return "\n".join(lines)


def sync_project_record_config(record: dict) -> dict:
    if record["deployment"]["type"] != "serverless":
        return record

    project_id = record["project"]["id"]
    project_domain = _project_domain(project_id)
    fresh_resources = _deployment_plan(project_id, record["project"]["input"])["resources"]
    existing_resources = {
        resource["type"]: resource for resource in record["deployment"]["plan"]["resources"]
    }
    merged_resources = []

    for fresh in fresh_resources:
        existing = existing_resources.get(fresh["type"])
        if existing:
            merged = dict(fresh)
            merged.update(existing)
            merged["details"] = dict(fresh.get("details", {}))
            merged["details"].update(existing.get("details", {}))
            merged_resources.append(merged)
        else:
            merged_resources.append(fresh)

    record["deployment"]["plan"]["resources"] = merged_resources
    resources = record["deployment"]["plan"]["resources"]

    for resource in resources:
        details = resource.get("details", {})
        if resource["type"] == "github_repository":
            details["repo_name"] = project_id
        elif resource["type"] == "storage_bucket":
            details["bucket_name"] = f"{project_id}-site"
        elif resource["type"] == "certificate":
            details["domain"] = project_domain
            resource["region"] = "us-east-1"
            details["certificate_region"] = "us-east-1"
            certificate_arn = details.get("certificate_arn")
            if certificate_arn and ":us-east-1:" not in certificate_arn:
                details["certificate_arn"] = None
                details["certificate_status"] = None
        elif resource["type"] == "cloudfront_distribution":
            details["origin_domain_name"] = (
                f"{project_id}-site.s3-website-us-west-1.amazonaws.com"
            )
            details["alias_domain"] = project_domain
        elif resource["type"] == "dns":
            details["record_name"] = project_domain
            details["target"] = None
            details["record_type"] = "A"
            details["alias"] = True

    return record


def describe_record(record: dict) -> str:
    project = record["project"]
    analysis = record["analysis"]
    deployment = record["deployment"]

    lines = [
        f"Project: {project['name']} ({project['id']})",
        f"Created: {project['created_at']}",
        f"Deployment: {deployment['type']}",
        f"Recommended architecture: {analysis['recommended_architecture']}",
        f"Estimated monthly cost: ${analysis['cost_estimate']['total']}",
        "",
        "Inputs:",
    ]

    for key, value in project["input"].items():
        lines.append(f" - {key}: {value}")

    lines.extend(["", "Why this architecture:"])
    for reason in analysis["reasons"]:
        lines.append(f" - {reason}")

    lines.extend(["", "Provisioning plan:"])
    for resource in deployment["plan"]["resources"]:
        service = resource["service"]
        resource_type = resource["type"]
        status = resource["status"]
        lines.append(f" - {service} / {resource_type}: {status}")
        if resource.get("provisioning", {}).get("message"):
            lines.append(f"   {resource['provisioning']['message']}")
        resource_details = resource.get("details", {})
        persisted = [
            f"{key}={value}"
            for key, value in resource_details.items()
            if key.endswith(("_id", "_arn", "_url", "_status")) and value
        ]
        if persisted:
            lines.append(f"   persisted: {', '.join(persisted)}")

    return "\n".join(lines)


def status_record(record: dict) -> str:
    project = record["project"]
    analysis = record["analysis"]
    deployment = record["deployment"]
    status = record["status"]

    lines = [
        f"Project: {project['name']} ({project['id']})",
        f"State: {status['state']}",
        f"Provisioning: {status['provisioning']}",
        f"Recommended architecture: {analysis['recommended_architecture']}",
        f"Deployment target: {deployment['type']}",
        f"Last updated: {status['last_updated']}",
        "",
        "Top options:",
    ]

    for option in analysis["top_options"]:
        lines.append(
            " - "
            f"{option['architecture']} "
            f"(confidence {option['confidence']}, "
            f"${option['estimated_monthly_cost_usd']}/mo)"
        )

    lines.extend(["", "Provision targets:"])
    for resource in deployment["plan"]["resources"]:
        lines.append(
            f" - {resource['service']} / {resource['type']}: {resource['status']}"
        )

    activity = status.get("activity", [])
    if activity:
        lines.extend(["", "Recent activity:"])
        for event in activity[-5:]:
            lines.append(f" - {event['timestamp']}: {event['message']}")

    return "\n".join(lines)
