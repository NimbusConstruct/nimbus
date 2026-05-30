from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProvisioningResult:
    provider: str
    resource_type: str
    service: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter:
    provider_name = "base"

    def provision(self, record: dict, resource: dict) -> ProvisioningResult:
        raise NotImplementedError
