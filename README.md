# Clinic NL2SQL with Vanna 2.0 and FastAPI

## Overview

This project is a production-style Natural Language to SQL backend for clinic analytics. It allows users to ask questions in plain English, converts those questions into SQL, safely executes the query against a SQLite database, and returns structured results, summaries, and chart-ready output.

The project reflects a real-world analytics workflow commonly seen in internal dashboards and reporting systems, where business users need fast access to insights without writing SQL manually. Instead of being a notebook demo, this is designed as a backend service with clear API endpoints, safety controls, reusable memory patterns, and a modular Vanna 2.0 agent setup.

The API accepts a natural language question and returns:

- a natural language summary
- the generated SQL query
- result columns
- result rows
- row count
- a chart JSON payload

## Features

- Vanna 2.0 agent-based NL2SQL architecture
- FastAPI backend with clean REST endpoints
- SQLite clinic dataset with realistic seeded data
- Groq-powered LLM inference using an OpenAI-compatible API
- SELECT-only SQL validation for safe analytics queries
- Pre-seeded `DemoAgentMemory` examples to improve SQL generation quality
- Automatic fallback chart generation using Plotly
- Structured JSON responses for frontend or dashboard integration
- Clear health checks and error handling for production-style usage

## LLM Provider

The initial implementation used Google Gemini as the LLM provider. While it worked for NL2SQL generation, testing exposed intermittent `503` errors during periods of high demand. That kind of upstream instability is a realistic issue when building production AI systems.

To improve reliability and runtime consistency, the project was migrated to Groq using `llama-3.3-70b-versatile`. Groq exposes an OpenAI-compatible API, which made the provider switch straightforward while keeping the rest of the architecture unchanged.

Current LLM configuration:

- Provider: Groq
- Model: `llama-3.3-70b-versatile`
- Service: `OpenAILlmService`
- Base URL: `https://api.groq.com/openai/v1`

This provider migration is an intentional engineering decision: instead of forcing the original setup, the system was adapted to use a more reliable inference backend while preserving the Vanna 2.0 agent design and API behavior.

## Project Structure

```text
project/
├── setup_database.py
├── seed_memory.py
├── vanna_setup.py
├── main.py
├── requirements.txt
├── README.md
├── RESULTS.md
├── .env
└── clinic.db  # generated after setup_database.py runs
```

## Tech Stack

- Python 3.10+
- FastAPI
- Vanna AI 2.0
- Groq
- SQLite
- Pandas
- Plotly
- python-dotenv

## Setup

1. Move into the project folder:

```bash
cd project
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables.

### Using Groq (Recommended)

Add your Groq API key to `.env`:

```env
GROQ_API_KEY=your_key_here
```

The project uses:

- `OpenAILlmService`
- `base_url="https://api.groq.com/openai/v1"`

4. Create the SQLite database:

```bash
python setup_database.py
```

5. Verify memory seeding:

```bash
python seed_memory.py
```

6. Start the API:

```bash
python -m uvicorn main:app --reload
```

## API Usage

### `GET /health`

Checks API readiness, database connectivity, and memory initialization.

Example response:

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 16
}
```

### `POST /chat`

Accepts a natural language analytics question.

Request body:

```json
{
  "question": "Top 5 patients by spending"
}
```

Example response:

```json
{
  "message": "The result highlights the top patients by total invoice spending.",
  "sql_query": "SELECT ...",
  "columns": ["id", "patient_name", "total_spending"],
  "rows": [
    [14, "Emma Smith", 17420.55],
    [81, "Aisha Patel", 16995.2]
  ],
  "row_count": 5,
  "chart": {
    "data": [],
    "layout": {}
  },
  "chart_type": "bar"
}
```

## Architecture

### 1. Database Layer

`setup_database.py` creates and seeds a SQLite database with:

- patients
- doctors
- appointments
- treatments
- invoices

### 2. Memory Layer

`seed_memory.py` defines reusable NL-to-SQL examples and loads them into `DemoAgentMemory`.

### 3. Vanna Agent Layer

`vanna_setup.py` creates:

- `OpenAILlmService`
- `SafeToolRegistry`
- `TrackingRunSqlTool`
- `VisualizeDataTool`
- `SaveQuestionToolArgsTool`
- `SearchSavedCorrectToolUsesTool`
- `DemoAgentMemory`
- `DefaultClinicUserResolver`
- `Agent`

### 4. API Layer

`main.py`:

- receives natural language questions
- sends them to the Vanna agent
- captures generated SQL and execution results
- extracts summary, rows, and chart data
- returns a stable JSON response contract

## Design Decisions

- SELECT-only SQL validation is enforced before execution to prevent destructive or unsafe database operations and keep the system read-only for analytics use cases.
- Fallback chart generation was added so the API can still return visualization-ready output even if the agent does not explicitly trigger the chart tool.
- `DemoAgentMemory` is used to preload successful NL-to-SQL patterns, improving SQL accuracy for repeated reporting-style questions.
- The LLM provider was switched from Gemini to Groq after reliability issues, showing a practical production decision driven by operational stability rather than preference alone.

## SQL Safety Rules

Before execution, SQL is validated to allow only:

- `SELECT`

The API rejects SQL containing:

- `INSERT`
- `UPDATE`
- `DELETE`
- `DROP`
- `ALTER`
- `EXEC`
- `GRANT`
- `REVOKE`
- `PRAGMA`
- `sqlite_master`
- multiple statements

## Test Results Summary

The system was validated against 20 representative clinic analytics questions covering patients, doctors, appointments, revenue, balances, and time-based reporting.

- Total questions tested: 20
- Success rate: high across core reporting queries
- SQL accuracy: strong for seeded and schema-aligned analytical prompts
- Chart generation success: successful for chart-friendly categorical and time-series outputs

Some edge cases can still fail when a question is ambiguous or underspecified. Those cases and the corresponding reference outcomes are documented in `RESULTS.md`.

## Typical Questions

- total patients
- doctors list
- total billed revenue
- total collected revenue
- busiest doctor
- top patients by spending
- monthly revenue trend
- appointments by status
- outstanding balances
- average treatment cost by specialization

## Notes

- `DemoAgentMemory` is intentionally in-memory, so `seed_memory.py` acts as the canonical source of reusable examples and `vanna_setup.py` loads them at startup.
- `clinic.db` is generated locally after running `setup_database.py`.
- Plotly fallback generation helps ensure frontend consumers still receive chart-ready JSON when appropriate.
- `RESULTS.md` contains the validation set and expected SQL behavior for manual review.