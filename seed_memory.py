"""
Seed reusable Vanna agent memory examples for the clinic NL2SQL project.

`DemoAgentMemory` is intentionally in-memory only. To keep the project simple
and dependency-free, this module contains the canonical examples and exposes a
function that both:
- seeds memory when imported by `vanna_setup.py`
- can be run directly to verify the memory examples
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from vanna.core.tool import ToolContext
from vanna.core.user import User
from vanna.integrations.local.agent_memory import DemoAgentMemory


@dataclass(frozen=True)
class MemoryExample:
    question: str
    sql: str
    summary: str


MEMORY_EXAMPLES: list[MemoryExample] = [
    MemoryExample(
        question="How many patients are registered?",
        sql="SELECT COUNT(*) AS total_patients FROM patients;",
        summary="Counts every registered patient in the clinic database.",
    ),
    MemoryExample(
        question="List all doctors with their specialization and department.",
        sql="SELECT name, specialization, department FROM doctors ORDER BY specialization, name;",
        summary="Returns the doctor directory ordered by specialty.",
    ),
    MemoryExample(
        question="Show the top 5 patients by invoice spending.",
        sql="""
        SELECT
            p.id,
            p.first_name || ' ' || p.last_name AS patient_name,
            ROUND(SUM(i.total_amount), 2) AS total_spending
        FROM patients p
        JOIN invoices i ON i.patient_id = p.id
        GROUP BY p.id, patient_name
        ORDER BY total_spending DESC
        LIMIT 5;
        """.strip(),
        summary="Ranks patients by total billed invoice amount.",
    ),
    MemoryExample(
        question="Which doctor has the most appointments?",
        sql="""
        SELECT
            d.name AS doctor_name,
            d.specialization,
            COUNT(a.id) AS appointment_count
        FROM doctors d
        LEFT JOIN appointments a ON a.doctor_id = d.id
        GROUP BY d.id, d.name, d.specialization
        ORDER BY appointment_count DESC
        LIMIT 1;
        """.strip(),
        summary="Finds the busiest doctor based on total appointments.",
    ),
    MemoryExample(
        question="Which city has the most patients?",
        sql="""
        SELECT city, COUNT(*) AS patient_count
        FROM patients
        GROUP BY city
        ORDER BY patient_count DESC
        LIMIT 1;
        """.strip(),
        summary="Shows the city with the largest patient base.",
    ),
    MemoryExample(
        question="What is the monthly revenue trend?",
        sql="""
        SELECT
            strftime('%Y-%m', invoice_date) AS month,
            ROUND(SUM(total_amount), 2) AS revenue
        FROM invoices
        GROUP BY month
        ORDER BY month;
        """.strip(),
        summary="Aggregates invoiced revenue month by month.",
    ),
    MemoryExample(
        question="Show total collected revenue.",
        sql="SELECT ROUND(SUM(paid_amount), 2) AS total_collected_revenue FROM invoices;",
        summary="Sums all paid invoice amounts.",
    ),
    MemoryExample(
        question="How many appointments were completed by each doctor?",
        sql="""
        SELECT
            d.name AS doctor_name,
            COUNT(a.id) AS completed_appointments
        FROM doctors d
        LEFT JOIN appointments a
            ON a.doctor_id = d.id
           AND a.status = 'completed'
        GROUP BY d.id, d.name
        ORDER BY completed_appointments DESC;
        """.strip(),
        summary="Breaks down completed appointments by doctor.",
    ),
    MemoryExample(
        question="Show average treatment cost by specialization.",
        sql="""
        SELECT
            d.specialization,
            ROUND(AVG(t.cost), 2) AS average_treatment_cost
        FROM treatments t
        JOIN appointments a ON a.id = t.appointment_id
        JOIN doctors d ON d.id = a.doctor_id
        GROUP BY d.specialization
        ORDER BY average_treatment_cost DESC;
        """.strip(),
        summary="Compares average treatment cost across specialties.",
    ),
    MemoryExample(
        question="How many appointments happened each month?",
        sql="""
        SELECT
            strftime('%Y-%m', appointment_date) AS month,
            COUNT(*) AS appointment_count
        FROM appointments
        GROUP BY month
        ORDER BY month;
        """.strip(),
        summary="Tracks monthly appointment volume.",
    ),
    MemoryExample(
        question="Which patients still have unpaid balances?",
        sql="""
        SELECT
            p.id,
            p.first_name || ' ' || p.last_name AS patient_name,
            ROUND(SUM(i.total_amount - i.paid_amount), 2) AS outstanding_balance
        FROM patients p
        JOIN invoices i ON i.patient_id = p.id
        GROUP BY p.id, patient_name
        HAVING outstanding_balance > 0
        ORDER BY outstanding_balance DESC;
        """.strip(),
        summary="Finds patients with remaining balances on invoices.",
    ),
    MemoryExample(
        question="What are the top 5 most expensive treatments?",
        sql="""
        SELECT
            treatment_name,
            ROUND(cost, 2) AS cost,
            duration_minutes
        FROM treatments
        ORDER BY cost DESC
        LIMIT 5;
        """.strip(),
        summary="Returns the most expensive treatments in the dataset.",
    ),
    MemoryExample(
        question="Show appointments by status.",
        sql="""
        SELECT status, COUNT(*) AS appointment_count
        FROM appointments
        GROUP BY status
        ORDER BY appointment_count DESC;
        """.strip(),
        summary="Groups appointments into scheduled, completed, cancelled, and no-show.",
    ),
    MemoryExample(
        question="Which doctor generated the highest revenue?",
        sql="""
        SELECT
            d.name AS doctor_name,
            d.specialization,
            ROUND(SUM(t.cost), 2) AS generated_revenue
        FROM doctors d
        JOIN appointments a ON a.doctor_id = d.id
        JOIN treatments t ON t.appointment_id = a.id
        GROUP BY d.id, d.name, d.specialization
        ORDER BY generated_revenue DESC
        LIMIT 1;
        """.strip(),
        summary="Uses treatment revenue as a proxy for doctor-generated revenue.",
    ),
    MemoryExample(
        question="How many new patients registered each month?",
        sql="""
        SELECT
            strftime('%Y-%m', registered_date) AS month,
            COUNT(*) AS new_patients
        FROM patients
        GROUP BY month
        ORDER BY month;
        """.strip(),
        summary="Measures patient registration growth over time.",
    ),
    MemoryExample(
        question="Which departments have the most doctors?",
        sql="""
        SELECT department, COUNT(*) AS doctor_count
        FROM doctors
        GROUP BY department
        ORDER BY doctor_count DESC, department;
        """.strip(),
        summary="Counts doctor headcount by department.",
    ),
]


async def seed_agent_memory(memory: DemoAgentMemory) -> int:
    """Load the static training examples into a DemoAgentMemory instance."""
    system_user = User(
        id="seed-user",
        email="seed@example.com",
        group_memberships=["user"],
    )
    context = ToolContext(
        user=system_user,
        conversation_id="seed-conversation",
        request_id="seed-request",
        agent_memory=memory,
        metadata={"source": "seed_memory.py"},
    )

    for example in MEMORY_EXAMPLES:
        await memory.save_tool_usage(
            question=example.question,
            tool_name="run_sql",
            args={"sql": example.sql},
            context=context,
            success=True,
            metadata={"summary": example.summary},
        )

    return len(MEMORY_EXAMPLES)


async def _main() -> None:
    memory = DemoAgentMemory(max_items=20_000)
    count = await seed_agent_memory(memory)
    print(f"Seeded {count} memory examples into DemoAgentMemory.")
    for example in MEMORY_EXAMPLES[:5]:
        print(f"- {example.question}")
    print("Memory seeding finished successfully.")


if __name__ == "__main__":
    asyncio.run(_main())
