from dataclasses import asdict, dataclass

from app.models import Principal, Tool, ToolVersion


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    risk_level: str
    required_permissions: list[str]
    granted_permissions: list[str]
    missing_permissions: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def principal_permissions(principal: Principal) -> set[str]:
    return {
        permission.key
        for role in principal.roles
        for permission in role.permissions
    }


def principal_can_act_for_agent(principal: Principal, agent_id: str) -> bool:
    """Human users are unscoped; service accounts are bound to exactly one Agent."""
    if principal.type != "service_account":
        return True
    return principal.agent_id == agent_id


def evaluate_tool_policy(
    principal: Principal, tool: Tool, version: ToolVersion
) -> PolicyDecision:
    required = {"tool.invoke", *version.required_permissions}
    if tool.risk_level == "high":
        required.add("tool.high_risk.invoke")
    granted = principal_permissions(principal)
    missing = sorted(required - granted)
    return PolicyDecision(
        allowed=not missing,
        reason="all_required_permissions_granted" if not missing else "missing_permissions",
        risk_level=tool.risk_level,
        required_permissions=sorted(required),
        granted_permissions=sorted(granted),
        missing_permissions=missing,
    )
