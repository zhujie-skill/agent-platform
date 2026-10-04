from typing import Literal

from pydantic import BaseModel


class ContractReference(BaseModel):
    version: str
    stability: Literal["stable"]
    documentation: str


class CompatibilityRead(BaseModel):
    api_family: str
    status: Literal["stable"]
    discovery_endpoint: str
    invoke_endpoint_template: str
    identity_header: str
    minimum_python_sdk_version: str
    contracts: dict[str, ContractReference]
    guarantees: list[str]
