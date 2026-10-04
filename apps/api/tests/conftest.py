from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models import (
    Agent,
    AgentToolBinding,
    Permission,
    Principal,
    Role,
    Tool,
    ToolVersion,
    Workspace,
)

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
DEVELOPER_AGENT_ID = "00000000-0000-0000-0000-000000000102"
ECHO_TOOL_ID = "00000000-0000-0000-0000-000000000201"
ADMIN_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000501"
ANALYST_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000502"
VIEWER_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000503"
DATA_SERVICE_ACCOUNT_ID = "00000000-0000-0000-0000-000000000504"


def seed_catalog(session: Session) -> None:
    workspace = Workspace(id=WORKSPACE_ID, name="Default Workspace", slug="default")
    data_agent = Agent(
        id=DATA_AGENT_ID,
        workspace_id=WORKSPACE_ID,
        namespace="platform",
        name="data-agent",
        display_name="Data Agent",
        description="Data consumer",
        agent_type="data",
        status="active",
        owner="Data Platform",
    )
    developer_agent = Agent(
        id=DEVELOPER_AGENT_ID,
        workspace_id=WORKSPACE_ID,
        namespace="platform",
        name="developer-agent",
        display_name="Developer Agent",
        description="Developer consumer",
        agent_type="developer",
        status="active",
        owner="Developer Platform",
    )
    echo = Tool(
        id=ECHO_TOOL_ID,
        workspace_id=WORKSPACE_ID,
        namespace="system",
        name="echo",
        display_name="Echo",
        description="Echo a message",
        owner="Tool Platform",
        provider_type="native",
        risk_level="low",
        status="active",
        default_version="1.0.0",
    )
    echo.versions.append(
        ToolVersion(
            version="1.0.0",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["message"],
                "properties": {"message": {"type": "string", "minLength": 1}},
            },
            output_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["message"],
                "properties": {"message": {"type": "string"}},
            },
            executor_type="native",
            executor_config={"handler_key": "system.echo"},
            timeout_seconds=5,
            retry_policy={"max_attempts": 1},
            required_permissions=[],
            definition_hash="test-definition-hash",
            registration_channel="seed",
        )
    )
    invoke_permission = Permission(
        key="tool.invoke", description="Invoke an enabled Tool through the Gateway."
    )
    database_permission = Permission(
        key="database.read", description="Read an approved database source."
    )
    admin_permission = Permission(
        key="platform.admin", description="Manage platform policy."
    )
    high_risk_permission = Permission(
        key="tool.high_risk.invoke", description="Invoke high-risk Tools."
    )
    admin_role = Role(
        workspace_id=WORKSPACE_ID,
        name="platform-admin",
        description="Full local administration.",
        permissions=[
            invoke_permission,
            database_permission,
            admin_permission,
            high_risk_permission,
        ],
    )
    analyst_role = Role(
        workspace_id=WORKSPACE_ID,
        name="data-analyst",
        description="Read governed data.",
        permissions=[invoke_permission, database_permission],
    )
    viewer_role = Role(
        workspace_id=WORKSPACE_ID,
        name="tool-user",
        description="Invoke low-risk tools.",
        permissions=[invoke_permission],
    )
    admin = Principal(
        id=ADMIN_PRINCIPAL_ID,
        workspace_id=WORKSPACE_ID,
        type="user",
        display_name="Local Admin",
        external_id="local-admin",
        status="active",
        roles=[admin_role],
    )
    analyst = Principal(
        id=ANALYST_PRINCIPAL_ID,
        workspace_id=WORKSPACE_ID,
        type="user",
        display_name="Local Data Analyst",
        external_id="local-analyst",
        status="active",
        roles=[analyst_role],
    )
    viewer = Principal(
        id=VIEWER_PRINCIPAL_ID,
        workspace_id=WORKSPACE_ID,
        type="user",
        display_name="Local Viewer",
        external_id="local-viewer",
        status="active",
        roles=[viewer_role],
    )
    data_service_account = Principal(
        id=DATA_SERVICE_ACCOUNT_ID,
        workspace_id=WORKSPACE_ID,
        agent_id=DATA_AGENT_ID,
        type="service_account",
        display_name="Data Agent Runtime",
        external_id="data-agent-runtime",
        status="active",
        roles=[analyst_role],
    )
    session.add_all(
        [
            workspace,
            data_agent,
            developer_agent,
            echo,
            admin,
            analyst,
            viewer,
            data_service_account,
        ]
    )
    session.flush()
    session.add_all(
        [
            AgentToolBinding(agent_id=DATA_AGENT_ID, tool_id=ECHO_TOOL_ID),
            AgentToolBinding(agent_id=DEVELOPER_AGENT_ID, tool_id=ECHO_TOOL_ID),
        ]
    )
    session.commit()


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as session:
        seed_catalog(session)

    def override_session() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
