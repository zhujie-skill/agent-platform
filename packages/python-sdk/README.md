# Agent Platform Python SDK

```powershell
pip install -e .\packages\python-sdk
```

```python
from agent_platform_sdk import AgentPlatformClient

with AgentPlatformClient(principal="data-agent-runtime") as client:
    tools = client.list_available_tools("00000000-0000-0000-0000-000000000101")
    result = client.invoke(
        "sql.list_tables",
        agent_id="00000000-0000-0000-0000-000000000101",
        arguments={"schema": "tool_data"},
    )
    print(result.trace_id, result.data)
```

`X-Local-Principal` 是本地展示项目的身份适配器。未来接入 OIDC 或 workload identity 时，SDK 的身份实现需要替换，但 discovery 与 invoke 数据契约保持在 API v1。
