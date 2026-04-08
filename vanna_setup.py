"""
Vanna 2.0 agent setup for the clinic NL2SQL project.
"""

from __future__ import annotations

import os
import re
import asyncio
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.core.system_prompt.base import SystemPromptBuilder
from vanna.core.tool import ToolRejection
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)

from seed_memory import seed_agent_memory


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "clinic.db"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


SCHEMA_CONTEXT = """
You are working with a SQLite database named clinic.db.

Tables:
1. patients
   - id
   - first_name
   - last_name
   - email
   - phone
   - date_of_birth
   - gender
   - city
   - registered_date

2. doctors
   - id
   - name
   - specialization
   - department
   - phone

3. appointments
   - id
   - patient_id
   - doctor_id
   - appointment_date
   - status
   - notes

4. treatments
   - id
   - appointment_id
   - treatment_name
   - cost
   - duration_minutes

5. invoices
   - id
   - patient_id
   - invoice_date
   - total_amount
   - paid_amount
   - status

Relationships:
- appointments.patient_id -> patients.id
- appointments.doctor_id -> doctors.id
- treatments.appointment_id -> appointments.id
- invoices.patient_id -> patients.id
""".strip()


def validate_select_sql(sql: str) -> str:
    """Validate that the SQL is a single safe SELECT statement."""
    cleaned = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    cleaned = re.sub(r"--.*?$", " ", cleaned, flags=re.MULTILINE).strip()
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    normalized_upper = normalized.upper()

    if not normalized:
        raise ValueError("SQL query is empty.")
    if not normalized_upper.startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed.")
    if "SQLITE_MASTER" in normalized_upper:
        raise ValueError("Access to sqlite_master is not allowed.")
    if ";" in normalized[:-1]:
        raise ValueError("Multiple SQL statements are not allowed.")

    forbidden_terms = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "GRANT",
        "REVOKE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
    }
    tokens = set(re.findall(r"\b[A-Z_]+\b", normalized_upper))
    forbidden_hits = sorted(token for token in forbidden_terms if token in tokens)
    if forbidden_hits:
        raise ValueError(
            f"Forbidden SQL keyword(s) detected: {', '.join(forbidden_hits)}."
        )

    return normalized


class DefaultClinicUserResolver(UserResolver):
    """Resolve every request to a simple local application user."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="default-user",
            email="default.user@clinic.local",
            group_memberships=["user"],
            metadata={"source": "local-default-user"},
        )


class ClinicSystemPromptBuilder(SystemPromptBuilder):
    """Custom prompt tuned for clinic analytics and safe SQL generation."""

    async def build_system_prompt(self, user: User, tools: list) -> str:
        tool_names = ", ".join(tool.name for tool in tools)
        return (
            "You are a production-grade healthcare analytics assistant built with Vanna 2.0.\n"
            "Your job is to answer clinic analytics questions by generating safe SQLite SELECT queries.\n\n"
            f"{SCHEMA_CONTEXT}\n\n"
            "Operational rules:\n"
            "- Always search memory first with search_saved_correct_tool_uses.\n"
            "- Only generate a single SQLite SELECT statement.\n"
            "- Never use INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, GRANT, REVOKE, PRAGMA, or sqlite_master.\n"
            "- Prefer explicit joins, clear aliases, and readable column names.\n"
            "- After a successful run_sql call, save the successful pattern with save_question_tool_args.\n"
            "- When result data has a categorical or time axis and a numeric metric, call visualize_data.\n"
            "- Keep the final summary concise and focused on what the data shows.\n\n"
            f"Available tools: {tool_names}\n"
            f"Current user: {user.email or user.id}"
        )


class SafeToolRegistry(ToolRegistry):
    """Tool registry that enforces strict SELECT-only SQL before execution."""

    async def transform_args(self, tool, args, user, context):  # type: ignore[override]
        if tool.name == "run_sql" and hasattr(args, "sql"):
            try:
                args.sql = validate_select_sql(args.sql)
            except ValueError as exc:
                return ToolRejection(reason=str(exc))
        return args


class TrackingRunSqlTool(RunSqlTool):
    """RunSqlTool wrapper that records executed SQL per conversation."""

    def __init__(self, sql_runner: SqliteRunner):
        super().__init__(sql_runner=sql_runner)
        self.executions: dict[str, dict] = {}

    async def execute(self, context, args):  # type: ignore[override]
        self.executions[context.conversation_id] = {
            "sql": args.sql,
            "request_id": context.request_id,
        }
        result = await super().execute(context, args)
        self.executions[context.conversation_id]["metadata"] = result.metadata
        self.executions[context.conversation_id]["success"] = result.success
        if result.error:
            self.executions[context.conversation_id]["error"] = result.error
        return result

    def pop_execution(self, conversation_id: str) -> dict | None:
        return self.executions.pop(conversation_id, None)


@dataclass
class AgentBundle:
    agent: Agent
    agent_memory: DemoAgentMemory
    run_sql_tool: TrackingRunSqlTool


_AGENT_BUNDLE: AgentBundle | None = None
_AGENT_BUNDLE_LOCK = asyncio.Lock()


async def _build_agent_bundle() -> AgentBundle:
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing Groq API key. Set GROQ_API_KEY in .env."
        )

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database file not found at {DATABASE_PATH}. Run setup_database.py first."
        )

    llm_service = OpenAILlmService(
        model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    tool_registry = SafeToolRegistry()
    sqlite_runner = SqliteRunner(str(DATABASE_PATH))
    run_sql_tool = TrackingRunSqlTool(sql_runner=sqlite_runner)

    tool_registry.register_local_tool(run_sql_tool, access_groups=["user"])
    tool_registry.register_local_tool(VisualizeDataTool(), access_groups=["user"])
    tool_registry.register_local_tool(
        SaveQuestionToolArgsTool(),
        access_groups=["user"],
    )
    tool_registry.register_local_tool(
        SearchSavedCorrectToolUsesTool(),
        access_groups=["user"],
    )

    agent_memory = DemoAgentMemory(max_items=20_000)
    await seed_agent_memory(agent_memory)

    agent = Agent(
        llm_service=llm_service,
        tool_registry=tool_registry,
        user_resolver=DefaultClinicUserResolver(),
        agent_memory=agent_memory,
        system_prompt_builder=ClinicSystemPromptBuilder(),
    )

    return AgentBundle(
        agent=agent,
        agent_memory=agent_memory,
        run_sql_tool=run_sql_tool,
    )


async def get_agent_bundle_async() -> AgentBundle:
    global _AGENT_BUNDLE
    if _AGENT_BUNDLE is None:
        async with _AGENT_BUNDLE_LOCK:
            if _AGENT_BUNDLE is None:
                _AGENT_BUNDLE = await _build_agent_bundle()
    return _AGENT_BUNDLE


def get_agent_bundle() -> AgentBundle:
    return asyncio.run(get_agent_bundle_async())


async def get_agent_async() -> Agent:
    bundle = await get_agent_bundle_async()
    return bundle.agent


def get_agent() -> Agent:
    return asyncio.run(get_agent_async())


async def get_agent_memory_count() -> int:
    bundle = await get_agent_bundle_async()
    return len(bundle.agent_memory._memories)
