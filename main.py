"""
FastAPI backend for the clinic NL2SQL demo powered by Vanna 2.0.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import plotly.express as px
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from vanna.components import ChartComponent, DataFrameComponent, RichTextComponent
from vanna.core.user import RequestContext

from vanna_setup import get_agent_bundle_async


app = FastAPI(
    title="Clinic NL2SQL API",
    version="1.0.0",
    description="Natural language to SQL API built with FastAPI, SQLite, and Vanna 2.0.",
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Natural language question")


class ChatResponse(BaseModel):
    message: str
    sql_query: str | None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    chart: dict[str, Any] | None
    chart_type: str | None


class ErrorResponse(BaseModel):
    error: str
    detail: str


def _extract_rows_from_dataframe(component: DataFrameComponent) -> list[list[Any]]:
    return [[row.get(column) for column in component.columns] for row in component.rows]


def _infer_chart_type(chart_json: dict[str, Any] | None) -> str | None:
    if not chart_json:
        return None
    data = chart_json.get("data")
    if isinstance(data, list) and data:
        chart_type = data[0].get("type")
        if chart_type:
            return str(chart_type)
    return None


def _looks_like_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    try:
        pd.to_datetime(series, errors="raise")
        return True
    except Exception:
        return False


def _build_fallback_chart(columns: list[str], rows: list[list[Any]]) -> tuple[dict[str, Any] | None, str | None]:
    if len(columns) < 2 or not rows:
        return None, None

    dataframe = pd.DataFrame(rows, columns=columns)
    x_column = columns[0]
    numeric_columns = [
        column for column in columns[1:] if pd.api.types.is_numeric_dtype(dataframe[column])
    ]
    if not numeric_columns:
        return None, None

    y_column = numeric_columns[0]
    if _looks_like_datetime(dataframe[x_column]):
        dataframe[x_column] = pd.to_datetime(dataframe[x_column], errors="coerce")
        dataframe = dataframe.sort_values(x_column)
        figure = px.line(
            dataframe,
            x=x_column,
            y=y_column,
            title=f"{y_column} by {x_column}",
            markers=True,
        )
        return figure.to_plotly_json(), "line"

    figure = px.bar(
        dataframe,
        x=x_column,
        y=y_column,
        title=f"{y_column} by {x_column}",
    )
    return figure.to_plotly_json(), "bar"


def _extract_summary(components: list) -> str:
    text_chunks: list[str] = []
    for component in components:
        rich_component = getattr(component, "rich_component", None)
        simple_component = getattr(component, "simple_component", None)

        if isinstance(rich_component, RichTextComponent) and rich_component.content:
            text_chunks.append(rich_component.content.strip())

        if simple_component and getattr(simple_component, "text", None):
            text_chunks.append(str(simple_component.text).strip())

    text_chunks = [
        chunk
        for chunk in text_chunks
        if chunk
        and "Results saved to file:" not in chunk
        and "IMPORTANT: FOR VISUALIZE_DATA" not in chunk
        and not chunk.startswith("Created visualization from")
    ]
    return text_chunks[-1] if text_chunks else "Query completed successfully."


def _request_context_from_fastapi(request: Request) -> RequestContext:
    query_params = {key: value for key, value in request.query_params.items()}
    headers = {key: value for key, value in request.headers.items()}
    cookies = dict(request.cookies)
    remote_addr = request.client.host if request.client else None
    return RequestContext(
        cookies=cookies,
        headers=headers,
        query_params=query_params,
        remote_addr=remote_addr,
        metadata={},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error="validation_error", detail=str(exc)).model_dump(),
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    bundle = await get_agent_bundle_async()
    return {
        "status": "ok",
        "database": "connected",
        "agent_memory_items": len(bundle.agent_memory._memories),
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    bundle = await get_agent_bundle_async()
    conversation_id = str(uuid4())
    components: list = []

    try:
        async for component in bundle.agent.send_message(
            _request_context_from_fastapi(request),
            question,
            conversation_id=conversation_id,
        ):
            components.append(component)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        ) from exc

    execution = bundle.run_sql_tool.pop_execution(conversation_id)
    if not execution:
        raise HTTPException(
            status_code=500,
            detail="The agent did not execute any SQL for this request.",
        )

    sql_query = execution.get("sql")
    rich_dataframe = next(
        (
            component.rich_component
            for component in components
            if isinstance(getattr(component, "rich_component", None), DataFrameComponent)
        ),
        None,
    )
    rich_chart = next(
        (
            component.rich_component
            for component in components
            if isinstance(getattr(component, "rich_component", None), ChartComponent)
        ),
        None,
    )

    if rich_dataframe is None:
        raise HTTPException(
            status_code=404,
            detail="Query executed, but no tabular results were returned.",
        )

    columns = rich_dataframe.columns
    rows = _extract_rows_from_dataframe(rich_dataframe)
    row_count = rich_dataframe.row_count or len(rows)

    chart_json = rich_chart.data if rich_chart else None
    chart_type = _infer_chart_type(chart_json)

    if chart_json is None:
        chart_json, chart_type = _build_fallback_chart(columns, rows)

    if row_count == 0:
        summary = "Query executed successfully but returned no rows."
    else:
        summary = _extract_summary(components)

    return ChatResponse(
        message=summary,
        sql_query=sql_query,
        columns=columns,
        rows=rows,
        row_count=row_count,
        chart=chart_json,
        chart_type=chart_type,
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Clinic NL2SQL API is running.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
