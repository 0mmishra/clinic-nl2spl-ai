"""
Create and seed the SQLite database used by the NL2SQL demo project.

This script creates a small but realistic clinic dataset with:
- 200 patients
- 15 doctors
- 500 appointments
- 350 treatments
- 300 invoices
"""

from __future__ import annotations

import random
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "clinic.db"
RANDOM_SEED = 42


FIRST_NAMES = [
    "Aarav",
    "Aisha",
    "Anaya",
    "Arjun",
    "David",
    "Emma",
    "Ethan",
    "Fatima",
    "Grace",
    "Hannah",
    "Ishaan",
    "Jacob",
    "Liam",
    "Maya",
    "Mia",
    "Noah",
    "Olivia",
    "Priya",
    "Riya",
    "Sophia",
    "Vihaan",
    "William",
    "Zara",
]

LAST_NAMES = [
    "Anderson",
    "Brown",
    "Carter",
    "Clark",
    "Davis",
    "Garcia",
    "Gupta",
    "Hall",
    "Johnson",
    "Khan",
    "Lewis",
    "Martin",
    "Patel",
    "Rodriguez",
    "Sharma",
    "Smith",
    "Taylor",
    "Thomas",
    "Walker",
    "Wilson",
]

CITIES = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "San Jose",
    "Austin",
    "Jacksonville",
]

SPECIALIZATIONS = [
    ("Cardiology", "Heart Care"),
    ("Dermatology", "Skin Care"),
    ("Neurology", "Neuroscience"),
    ("Orthopedics", "Bone and Joint"),
    ("Pediatrics", "Child Care"),
]

APPOINTMENT_STATUSES = ["scheduled", "completed", "cancelled", "no_show"]
INVOICE_STATUSES = ["paid", "partial", "pending", "overdue"]

TREATMENTS_BY_SPECIALIZATION = {
    "Cardiology": [
        "ECG",
        "Stress Test",
        "Cardiac Consultation",
        "Blood Pressure Monitoring",
        "Echocardiogram Review",
    ],
    "Dermatology": [
        "Skin Examination",
        "Acne Treatment",
        "Mole Removal Consultation",
        "Rash Evaluation",
        "Allergy Skin Assessment",
    ],
    "Neurology": [
        "Neurological Assessment",
        "Migraine Management",
        "Nerve Conduction Follow-up",
        "Seizure Evaluation",
        "Cognitive Screening",
    ],
    "Orthopedics": [
        "Joint Pain Assessment",
        "Fracture Follow-up",
        "Physiotherapy Consultation",
        "Back Pain Evaluation",
        "Mobility Screening",
    ],
    "Pediatrics": [
        "Child Wellness Check",
        "Vaccination Review",
        "Fever Assessment",
        "Growth Monitoring",
        "Pediatric Consultation",
    ],
}


def random_phone() -> str:
    return f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"


def maybe_none(value: str, chance: float) -> str | None:
    return None if random.random() < chance else value


def create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS patients;

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            date_of_birth TEXT NOT NULL,
            gender TEXT,
            city TEXT NOT NULL,
            registered_date TEXT NOT NULL
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            department TEXT NOT NULL,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            treatment_name TEXT NOT NULL,
            cost REAL NOT NULL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            invoice_date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
        """
    )


def generate_patients() -> list[tuple[str, str, str | None, str | None, str, str | None, str, str]]:
    patients: list[tuple[str, str, str | None, str | None, str, str | None, str, str]] = []
    genders = ["Male", "Female", "Non-binary", None]
    start_registered = date.today() - timedelta(days=730)

    for index in range(200):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = maybe_none(
            f"{first_name.lower()}.{last_name.lower()}{index + 1}@example.com",
            0.08,
        )
        phone = maybe_none(random_phone(), 0.05)
        age = random.randint(1, 90)
        dob = date.today() - timedelta(days=age * 365 + random.randint(0, 364))
        gender = random.choice(genders)
        city = random.choice(CITIES)
        registered_date = start_registered + timedelta(days=random.randint(0, 730))

        patients.append(
            (
                first_name,
                last_name,
                email,
                phone,
                dob.isoformat(),
                gender,
                city,
                registered_date.isoformat(),
            )
        )

    return patients


def generate_doctors() -> list[tuple[str, str, str, str]]:
    doctors: list[tuple[str, str, str, str]] = []
    selected_names = set()

    while len(doctors) < 15:
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        doctor_name = f"Dr. {first_name} {last_name}"
        if doctor_name in selected_names:
            continue
        selected_names.add(doctor_name)
        specialization, department = SPECIALIZATIONS[len(doctors) % len(SPECIALIZATIONS)]
        doctors.append((doctor_name, specialization, department, maybe_none(random_phone(), 0.12) or random_phone()))

    return doctors


def generate_appointments(
    patient_ids: list[int],
    doctor_rows: list[tuple[int, str]],
) -> list[tuple[int, int, str, str, str | None]]:
    appointments: list[tuple[int, int, str, str, str | None]] = []
    start_datetime = datetime.now() - timedelta(days=365)
    notes_pool = [
        "Follow-up required in two weeks.",
        "Patient reported mild pain improvement.",
        "Requested additional lab work.",
        "Vitals stable during checkup.",
        "Medication review completed.",
        None,
        None,
    ]

    weighted_patients = patient_ids + random.choices(patient_ids, k=100)

    for _ in range(500):
        patient_id = random.choice(weighted_patients)
        doctor_id, specialization = random.choice(doctor_rows)
        appointment_datetime = start_datetime + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(8, 17),
            minutes=random.choice([0, 15, 30, 45]),
        )
        status_weights = [0.18, 0.62, 0.12, 0.08]
        status = random.choices(APPOINTMENT_STATUSES, weights=status_weights, k=1)[0]
        note = random.choice(notes_pool)
        if note and random.random() < 0.25:
            note = f"{note} Specialty focus: {specialization}."
        appointments.append(
            (
                patient_id,
                doctor_id,
                appointment_datetime.isoformat(timespec="minutes"),
                status,
                note,
            )
        )

    return appointments


def generate_treatments(
    completed_appointments: Iterable[tuple[int, str]],
) -> list[tuple[int, str, float, int | None]]:
    completed_list = list(completed_appointments)
    if not completed_list:
        raise ValueError("No completed appointments available to generate treatments.")

    treatments: list[tuple[int, str, float, int | None]] = []
    for appointment_id, specialization in random.choices(completed_list, k=350):
        treatment_name = random.choice(TREATMENTS_BY_SPECIALIZATION[specialization])
        cost = round(random.uniform(50, 5000), 2)
        duration = random.choice([15, 20, 30, 45, 60, 90, 120, None])
        treatments.append((appointment_id, treatment_name, cost, duration))

    return treatments


def generate_invoices(patient_ids: list[int]) -> list[tuple[int, str, float, float, str]]:
    invoices: list[tuple[int, str, float, float, str]] = []
    start_date = date.today() - timedelta(days=365)
    weighted_patients = patient_ids + random.choices(patient_ids, k=150)

    for _ in range(300):
        patient_id = random.choice(weighted_patients)
        invoice_date = start_date + timedelta(days=random.randint(0, 364))
        total_amount = round(random.uniform(50, 5000), 2)
        status = random.choices(
            INVOICE_STATUSES,
            weights=[0.5, 0.2, 0.18, 0.12],
            k=1,
        )[0]

        if status == "paid":
            paid_amount = total_amount
        elif status == "partial":
            paid_amount = round(total_amount * random.uniform(0.2, 0.8), 2)
        else:
            paid_amount = 0.0 if random.random() < 0.7 else round(total_amount * random.uniform(0.05, 0.3), 2)

        invoices.append(
            (patient_id, invoice_date.isoformat(), total_amount, paid_amount, status)
        )

    return invoices


def main() -> None:
    random.seed(RANDOM_SEED)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        create_tables(cursor)

        patients = generate_patients()
        cursor.executemany(
            """
            INSERT INTO patients (
                first_name, last_name, email, phone, date_of_birth, gender, city, registered_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            patients,
        )

        doctors = generate_doctors()
        cursor.executemany(
            """
            INSERT INTO doctors (name, specialization, department, phone)
            VALUES (?, ?, ?, ?)
            """,
            doctors,
        )

        patient_ids = [row[0] for row in cursor.execute("SELECT id FROM patients").fetchall()]
        doctor_rows = cursor.execute(
            "SELECT id, specialization FROM doctors"
        ).fetchall()

        appointments = generate_appointments(patient_ids, doctor_rows)
        cursor.executemany(
            """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            appointments,
        )

        completed_appointments = cursor.execute(
            """
            SELECT appointments.id, doctors.specialization
            FROM appointments
            JOIN doctors ON doctors.id = appointments.doctor_id
            WHERE appointments.status = 'completed'
            """
        ).fetchall()
        treatments = generate_treatments(completed_appointments)
        cursor.executemany(
            """
            INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
            VALUES (?, ?, ?, ?)
            """,
            treatments,
        )

        invoices = generate_invoices(patient_ids)
        cursor.executemany(
            """
            INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            invoices,
        )

        connection.commit()

        city_distribution = Counter(patient[-2] for patient in patients).most_common(3)
        print(
            "Created "
            f"{len(patients)} patients, "
            f"{len(doctors)} doctors, "
            f"{len(appointments)} appointments, "
            f"{len(treatments)} treatments, "
            f"{len(invoices)} invoices."
        )
        print(
            "Top patient cities: "
            + ", ".join(f"{city} ({count})" for city, count in city_distribution)
        )
        print(f"Database file: {DATABASE_PATH}")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
