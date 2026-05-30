from nimbus.providers.aws import AWSAdapter
from nimbus.providers.github import GitHubAdapter


PROVIDER_REGISTRY = {
    "EC2": AWSAdapter(),
    "S3": AWSAdapter(),
    "ACM": AWSAdapter(),
    "Route53": AWSAdapter(),
    "CloudFront": AWSAdapter(),
    "GitHub": GitHubAdapter(),
}


def provision_project(record: dict) -> tuple[dict, list[dict]]:
    deployment = record["deployment"]
    resources = deployment["plan"]["resources"]
    activity = []

    if not resources:
        record["status"]["provisioning"] = "not_applicable"
        record["status"]["state"] = "planned"
        return record, activity

    record["status"]["provisioning"] = "in_progress"
    record["status"]["state"] = "provisioning"

    ordered_services = ["GitHub", "S3", "ACM", "Route53", "CloudFront"]
    ordered_resources = []
    for service in ordered_services:
        ordered_resources.extend([resource for resource in resources if resource["service"] == service])
    ordered_resources.extend([resource for resource in resources if resource not in ordered_resources])

    aws_adapter = AWSAdapter()
    dns_resource = None
    certificate_resource = None
    cloudfront_resource = None
    for resource in resources:
        if resource["type"] == "dns":
            dns_resource = resource
        elif resource["type"] == "certificate":
            certificate_resource = resource
        elif resource["type"] == "cloudfront_distribution":
            cloudfront_resource = resource

    for resource in ordered_resources:
        if resource["type"] == "cloudfront_distribution":
            if certificate_resource and certificate_resource.get("status") != "issued":
                continue

        adapter = PROVIDER_REGISTRY.get(resource["service"])

        if adapter is None:
            resource["status"] = "unsupported"
            resource["provisioning"] = {
                "provider": "unmapped",
                "message": "No provider adapter is registered for this service.",
            }
            activity.append(
                {
                    "service": resource["service"],
                    "resource_type": resource["type"],
                    "status": resource["status"],
                    "message": resource["provisioning"]["message"],
                }
            )
            continue

        result = adapter.provision(record, resource)
        resource["status"] = result.status
        if result.details:
            resource.setdefault("details", {}).update(result.details)
        resource["provisioning"] = {
            "provider": result.provider,
            "message": result.message,
            "details": result.details,
        }
        activity.append(
            {
                "service": resource["service"],
                "resource_type": resource["type"],
                "status": result.status,
                "message": result.message,
            }
        )

        if resource["type"] == "dns" and certificate_resource and certificate_resource.get("status") in {"created", "pending_validation"}:
            result = aws_adapter.wait_for_certificate_issuance(record, certificate_resource)
            certificate_resource["status"] = result.status
            if result.details:
                certificate_resource.setdefault("details", {}).update(result.details)
            certificate_resource["provisioning"] = {
                "provider": result.provider,
                "message": result.message,
                "details": result.details,
            }
            activity.append(
                {
                    "service": certificate_resource["service"],
                    "resource_type": certificate_resource["type"],
                    "status": result.status,
                    "message": result.message,
                }
            )

            if cloudfront_resource and certificate_resource.get("status") == "issued":
                cf_result = aws_adapter.provision(record, cloudfront_resource)
                cloudfront_resource["status"] = cf_result.status
                if cf_result.details:
                    cloudfront_resource.setdefault("details", {}).update(cf_result.details)
                cloudfront_resource["provisioning"] = {
                    "provider": cf_result.provider,
                    "message": cf_result.message,
                    "details": cf_result.details,
                }
                activity.append(
                    {
                        "service": cloudfront_resource["service"],
                        "resource_type": cloudfront_resource["type"],
                        "status": cf_result.status,
                        "message": cf_result.message,
                    }
                )

                if dns_resource:
                    dns_result = aws_adapter.provision(record, dns_resource)
                    dns_resource["status"] = dns_result.status
                    if dns_result.details:
                        dns_resource.setdefault("details", {}).update(dns_result.details)
                    dns_resource["provisioning"] = {
                        "provider": dns_result.provider,
                        "message": dns_result.message,
                        "details": dns_result.details,
                    }
                    activity.append(
                        {
                            "service": dns_resource["service"],
                            "resource_type": dns_resource["type"],
                            "status": dns_result.status,
                            "message": dns_result.message,
                        }
                    )

    statuses = {resource["status"] for resource in resources}

    if "failed" in statuses:
        record["status"]["provisioning"] = "failed"
        record["status"]["state"] = "attention_required"
    elif statuses <= {"created", "issued"}:
        record["status"]["provisioning"] = "completed"
        record["status"]["state"] = "provisioned"
    elif "pending_validation" in statuses:
        record["status"]["provisioning"] = "pending_validation"
        record["status"]["state"] = "awaiting_certificate_validation"
    else:
        record["status"]["provisioning"] = "partial"
        record["status"]["state"] = "planned"

    return record, activity
