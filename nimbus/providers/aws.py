from nimbus.config import load_nimbus_config
from nimbus.providers.base import ProviderAdapter, ProvisioningResult

try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        WaiterError,
    )
except ImportError:  # pragma: no cover - optional dependency in dev env
    boto3 = None
    BotoCoreError = ClientError = NoCredentialsError = WaiterError = Exception


class AWSAdapter(ProviderAdapter):
    provider_name = "aws"
    CLOUDFRONT_HOSTED_ZONE_ID = "Z2FDTNDATAQYW2"

    def __init__(self, config: dict | None = None):
        self.config = config or load_nimbus_config()

    def _session(self, region_name: str | None = None):
        if boto3 is None:
            raise RuntimeError("boto3 is required for live AWS provisioning.")

        return boto3.session.Session(
            aws_access_key_id=self.config.get("aws_access_key_id"),
            aws_secret_access_key=self.config.get("aws_secret_access_key"),
            aws_session_token=self.config.get("aws_session_token"),
            region_name=region_name or self.config.get("aws_region") or "us-west-1",
        )

    def _provision_ec2_instance(self, record: dict, resource: dict) -> ProvisioningResult:
        region = resource.get("region") or self.config.get("aws_region") or "us-west-1"
        session = self._session(region_name=region)
        ec2 = session.client("ec2")

        image_id = (
            resource.get("details", {}).get("ami_id")
            or self.config.get("aws_ami_id")
        )
        if not image_id:
            raise RuntimeError(
                "EC2 launch requires aws_ami_id in .nimbus/config.yaml or NIMBUS_AWS_AMI_ID."
            )

        request = {
            "ImageId": image_id,
            "MinCount": 1,
            "MaxCount": 1,
            "InstanceType": (
                self.config.get("aws_instance_type")
                or resource.get("details", {}).get("suggested_instance_type")
                or "t3.small"
            ),
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": resource["details"]["instance_name"]},
                        {"Key": "Project", "Value": record["project"]["id"]},
                    ],
                }
            ],
        }

        if self.config.get("aws_key_name"):
            request["KeyName"] = self.config["aws_key_name"]
        if self.config.get("aws_subnet_id"):
            request["SubnetId"] = self.config["aws_subnet_id"]
        if self.config.get("aws_security_group_id"):
            request["SecurityGroupIds"] = [self.config["aws_security_group_id"]]

        response = ec2.run_instances(**request)
        instance = response["Instances"][0]
        instance_id = instance["InstanceId"]

        desc = ec2.describe_instances(InstanceIds=[instance_id])
        info = desc["Reservations"][0]["Instances"][0]

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message="EC2 instance launched successfully.",
            details={
                "instance_id": instance_id,
                "public_dns": info.get("PublicDnsName"),
                "public_ip": info.get("PublicIpAddress"),
                "region": region,
            },
        )

    def _provision_s3_bucket(self, record: dict, resource: dict) -> ProvisioningResult:
        region = resource.get("region") or self.config.get("aws_region") or "us-west-1"
        session = self._session(region_name=region)
        s3 = session.client("s3")

        bucket_name = resource["details"]["bucket_name"]
        create_args = {"Bucket": bucket_name}
        if region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}

        try:
            s3.create_bucket(**create_args)
            message = "S3 bucket created successfully."
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code != "BucketAlreadyOwnedByYou":
                raise
            message = "S3 bucket already exists and is owned by this AWS account."

        if resource["details"].get("website_hosting"):
            s3.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    "IndexDocument": {"Suffix": "index.html"},
                    "ErrorDocument": {"Key": "error.html"},
                },
            )

        website_url = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message=message,
            details={
                "bucket_name": bucket_name,
                "bucket_arn": f"arn:aws:s3:::{bucket_name}",
                "website_url": website_url,
                "region": region,
            },
        )

    def _provision_certificate(self, record: dict, resource: dict) -> ProvisioningResult:
        region = resource.get("region") or self.config.get("aws_region") or "us-west-1"
        session = self._session(region_name=region)
        acm = session.client("acm")

        domain_name = resource["details"]["domain"]
        certificate_arn = resource["details"].get("certificate_arn")
        if certificate_arn and f":{region}:" not in certificate_arn:
            certificate_arn = None
        if certificate_arn:
            message = "ACM certificate already exists for this project."
        else:
            response = acm.request_certificate(
                DomainName=domain_name,
                ValidationMethod="DNS",
            )
            certificate_arn = response["CertificateArn"]
            message = "ACM certificate requested successfully."

        describe = acm.describe_certificate(CertificateArn=certificate_arn)
        certificate = describe["Certificate"]
        validation_options = certificate.get("DomainValidationOptions", [])
        resource_record = {}
        if validation_options:
            resource_record = validation_options[0].get("ResourceRecord", {}) or {}

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message=message,
            details={
                "certificate_arn": certificate_arn,
                "domain": domain_name,
                "certificate_status": certificate.get("Status"),
                "certificate_region": region,
                "validation_record_name": resource_record.get("Name"),
                "validation_record_type": resource_record.get("Type"),
                "validation_record_value": resource_record.get("Value"),
                "region": region,
            },
        )

    def wait_for_certificate_issuance(self, record: dict, resource: dict) -> ProvisioningResult:
        region = resource.get("region") or self.config.get("aws_region") or "us-west-1"
        certificate_arn = resource.get("details", {}).get("certificate_arn")
        if not certificate_arn:
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status=resource.get("status", "pending"),
                message="No certificate ARN is available for validation polling.",
                details={},
            )

        session = self._session(region_name=region)
        acm = session.client("acm")

        try:
            waiter = acm.get_waiter("certificate_validated")
            waiter.wait(
                CertificateArn=certificate_arn,
                WaiterConfig={"Delay": 15, "MaxAttempts": 20},
            )
            describe = acm.describe_certificate(CertificateArn=certificate_arn)
            certificate = describe["Certificate"]
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="issued",
                message="ACM certificate is now issued.",
                details={
                    "certificate_arn": certificate_arn,
                    "certificate_status": certificate.get("Status"),
                    "domain": certificate.get("DomainName"),
                    "certificate_region": region,
                    "region": region,
                },
            )
        except WaiterError:
            describe = acm.describe_certificate(CertificateArn=certificate_arn)
            certificate = describe["Certificate"]
            validation_options = certificate.get("DomainValidationOptions", [])
            resource_record = {}
            if validation_options:
                resource_record = validation_options[0].get("ResourceRecord", {}) or {}
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="pending_validation",
                message=(
                    "ACM certificate is still pending validation. "
                    "DNS may still be propagating."
                ),
                details={
                    "certificate_arn": certificate_arn,
                    "certificate_status": certificate.get("Status"),
                    "domain": certificate.get("DomainName"),
                    "certificate_region": region,
                    "validation_record_name": resource_record.get("Name"),
                    "validation_record_type": resource_record.get("Type"),
                    "validation_record_value": resource_record.get("Value"),
                    "region": region,
                },
            )

    def _provision_cloudfront_distribution(self, record: dict, resource: dict) -> ProvisioningResult:
        certificate_resource = None
        for planned_resource in record["deployment"]["plan"]["resources"]:
            if planned_resource["type"] == "certificate":
                certificate_resource = planned_resource
                break

        if not certificate_resource:
            raise RuntimeError("CloudFront provisioning requires a certificate resource.")

        cert_details = certificate_resource.get("details", {})
        certificate_arn = cert_details.get("certificate_arn")
        certificate_status = cert_details.get("certificate_status")
        if not certificate_arn:
            raise RuntimeError("CloudFront provisioning requires an ACM certificate ARN.")
        if cert_details.get("certificate_region") != "us-east-1":
            raise RuntimeError("CloudFront requires the ACM certificate to be in us-east-1.")
        if certificate_status != "ISSUED":
            raise RuntimeError("CloudFront provisioning requires an ACM certificate in ISSUED status.")

        session = self._session(region_name="us-east-1")
        cloudfront = session.client("cloudfront")
        details = resource["details"]
        distribution_id = details.get("distribution_id")

        if distribution_id:
            distribution = cloudfront.get_distribution(Id=distribution_id)["Distribution"]
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource["type"],
                service=resource["service"],
                status="created",
                message="CloudFront distribution already exists for this project.",
                details={
                    "distribution_id": distribution["Id"],
                    "distribution_domain_name": distribution["DomainName"],
                    "distribution_status": distribution["Status"],
                    "distribution_hosted_zone_id": self.CLOUDFRONT_HOSTED_ZONE_ID,
                },
            )

        caller_reference = f"{record['project']['id']}-{record['project']['updated_at']}"
        origin_id = f"s3-website-{record['project']['id']}"
        distribution = cloudfront.create_distribution(
            DistributionConfig={
                "CallerReference": caller_reference,
                "Comment": f"Nimbus project {record['project']['id']}",
                "Enabled": True,
                "Aliases": {
                    "Quantity": 1,
                    "Items": [details["alias_domain"]],
                },
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": origin_id,
                            "DomainName": details["origin_domain_name"],
                            "CustomOriginConfig": {
                                "HTTPPort": 80,
                                "HTTPSPort": 443,
                                "OriginProtocolPolicy": "http-only",
                                "OriginSslProtocols": {
                                    "Quantity": 1,
                                    "Items": ["TLSv1.2"],
                                },
                            },
                        }
                    ],
                },
                "DefaultRootObject": "index.html",
                "DefaultCacheBehavior": {
                    "TargetOriginId": origin_id,
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "AllowedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"],
                        "CachedMethods": {
                            "Quantity": 2,
                            "Items": ["GET", "HEAD"],
                        },
                    },
                    "ForwardedValues": {
                        "QueryString": False,
                        "Cookies": {"Forward": "none"},
                    },
                    "MinTTL": 0,
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                },
                "ViewerCertificate": {
                    "ACMCertificateArn": certificate_arn,
                    "SSLSupportMethod": "sni-only",
                    "MinimumProtocolVersion": "TLSv1.2_2021",
                },
            }
        )["Distribution"]

        cloudfront.get_waiter("distribution_deployed").wait(
            Id=distribution["Id"],
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
        distribution = cloudfront.get_distribution(Id=distribution["Id"])["Distribution"]

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message="CloudFront distribution created successfully.",
            details={
                "distribution_id": distribution["Id"],
                "distribution_domain_name": distribution["DomainName"],
                "distribution_status": distribution["Status"],
                "distribution_hosted_zone_id": self.CLOUDFRONT_HOSTED_ZONE_ID,
            },
        )

    def _provision_dns(self, record: dict, resource: dict) -> ProvisioningResult:
        region = resource.get("region") or self.config.get("aws_region") or "us-west-1"
        hosted_zone_id = (
            resource["details"].get("hosted_zone_id")
            or self.config.get("route53_hosted_zone_id")
        )
        if not hosted_zone_id:
            raise RuntimeError(
                "Route53 record creation requires route53_hosted_zone_id in config or env."
            )

        distribution_details = None
        for planned_resource in record["deployment"]["plan"]["resources"]:
            if planned_resource["type"] == "cloudfront_distribution":
                distribution_details = planned_resource.get("details", {})
                break

        target = resource["details"].get("target")
        alias_record = bool(resource["details"].get("alias"))
        target_hosted_zone_id = None

        if distribution_details and distribution_details.get("distribution_domain_name"):
            target = distribution_details["distribution_domain_name"]
            target_hosted_zone_id = distribution_details.get(
                "distribution_hosted_zone_id", self.CLOUDFRONT_HOSTED_ZONE_ID
            )
            alias_record = True
        elif target and not str(target).endswith("amazonaws.com"):
            target = f"{target}.s3-website-{region}.amazonaws.com"

        validation_change = None
        changes = []

        for planned_resource in record["deployment"]["plan"]["resources"]:
            if planned_resource["type"] != "certificate":
                continue
            cert_details = planned_resource.get("details", {})
            if (
                cert_details.get("validation_record_name")
                and cert_details.get("validation_record_type")
                and cert_details.get("validation_record_value")
            ):
                changes.append(
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": cert_details["validation_record_name"],
                            "Type": cert_details["validation_record_type"],
                            "TTL": 300,
                            "ResourceRecords": [
                                {"Value": cert_details["validation_record_value"]}
                            ],
                        },
                    }
                )
                validation_change = {
                    "validation_record_name": cert_details["validation_record_name"],
                    "validation_record_type": cert_details["validation_record_type"],
                    "validation_record_value": cert_details["validation_record_value"],
                }
                break

        session = self._session(region_name=region)
        route53 = session.client("route53")
        record_name = resource["details"]["record_name"]

        if alias_record:
            existing = route53.list_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                StartRecordName=record_name,
                StartRecordType="CNAME",
                MaxItems="1",
            )["ResourceRecordSets"]
            if existing and existing[0]["Name"].rstrip(".") == record_name.rstrip(".") and existing[0]["Type"] == "CNAME":
                changes.append({"Action": "DELETE", "ResourceRecordSet": existing[0]})

        if alias_record:
            changes.append(
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": resource["details"].get("record_type", "A"),
                        "AliasTarget": {
                            "HostedZoneId": target_hosted_zone_id or self.CLOUDFRONT_HOSTED_ZONE_ID,
                            "DNSName": target,
                            "EvaluateTargetHealth": False,
                        },
                    },
                }
            )
        else:
            changes.append(
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": resource["details"].get("record_type", "CNAME"),
                        "TTL": 300,
                        "ResourceRecords": [{"Value": target}],
                    },
                }
            )

        response = route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": f"Nimbus project {record['project']['id']}",
                "Changes": changes,
            },
        )

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource["type"],
            service=resource["service"],
            status="created",
            message="Route53 record created successfully.",
            details={
                "change_id": response["ChangeInfo"]["Id"],
                "hosted_zone_id": hosted_zone_id,
                "target": target,
                "alias": alias_record,
                **(validation_change or {}),
                "region": region,
            },
        )

    def provision(self, record: dict, resource: dict) -> ProvisioningResult:
        resource_type = resource["type"]
        try:
            if resource_type == "ec2_instance":
                return self._provision_ec2_instance(record, resource)
            if resource_type == "storage_bucket":
                return self._provision_s3_bucket(record, resource)
            if resource_type == "certificate":
                return self._provision_certificate(record, resource)
            if resource_type == "cloudfront_distribution":
                return self._provision_cloudfront_distribution(record, resource)
            if resource_type == "dns":
                return self._provision_dns(record, resource)
        except (ClientError, BotoCoreError, NoCredentialsError, RuntimeError) as exc:
            return ProvisioningResult(
                provider=self.provider_name,
                resource_type=resource_type,
                service=resource["service"],
                status="failed",
                message=str(exc),
                details={},
            )

        return ProvisioningResult(
            provider=self.provider_name,
            resource_type=resource_type,
            service=resource["service"],
            status="unsupported",
            message="No live AWS handler exists for this resource type.",
            details={},
        )
