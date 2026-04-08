# NL2SQL Validation Results

This file contains 20 reference validation prompts for the clinic analytics project.

Notes:

- The SQL below is the intended reference SQL used to validate query intent.
- Final live model behavior depends on your Gemini API key and runtime environment.
- These cases are aligned with the seeded memory examples and schema in `vanna_setup.py`.

## 1. Total patients

- Question: `How many patients are registered?`
- SQL generated:

```sql
SELECT COUNT(*) AS total_patients FROM patients;
```

- Correct/Incorrect: Correct
- Summary: Counts every patient in the `patients` table.

## 2. Doctors list

- Question: `List all doctors with their specialization and department.`
- SQL generated:

```sql
SELECT name, specialization, department FROM doctors ORDER BY specialization, name;
```

- Correct/Incorrect: Correct
- Summary: Returns the doctor directory sorted by specialization and name.

## 3. Total revenue

- Question: `Show total billed revenue.`
- SQL generated:

```sql
SELECT ROUND(SUM(total_amount), 2) AS total_billed_revenue FROM invoices;
```

- Correct/Incorrect: Correct
- Summary: Aggregates total invoiced amount across all invoices.

## 4. Collected revenue

- Question: `Show total collected revenue.`
- SQL generated:

```sql
SELECT ROUND(SUM(paid_amount), 2) AS total_collected_revenue FROM invoices;
```

- Correct/Incorrect: Correct
- Summary: Aggregates all paid invoice amounts.

## 5. Busiest doctor

- Question: `Which doctor has the most appointments?`
- SQL generated:

```sql
SELECT
    d.name AS doctor_name,
    d.specialization,
    COUNT(a.id) AS appointment_count
FROM doctors d
LEFT JOIN appointments a ON a.doctor_id = d.id
GROUP BY d.id, d.name, d.specialization
ORDER BY appointment_count DESC
LIMIT 1;
```

- Correct/Incorrect: Correct
- Summary: Finds the doctor with the highest appointment count.

## 6. Top patients by spending

- Question: `Show the top 5 patients by invoice spending.`
- SQL generated:

```sql
SELECT
    p.id,
    p.first_name || ' ' || p.last_name AS patient_name,
    ROUND(SUM(i.total_amount), 2) AS total_spending
FROM patients p
JOIN invoices i ON i.patient_id = p.id
GROUP BY p.id, patient_name
ORDER BY total_spending DESC
LIMIT 5;
```

- Correct/Incorrect: Correct
- Summary: Ranks patients by total billed invoice amount.

## 7. Monthly revenue trend

- Question: `What is the monthly revenue trend?`
- SQL generated:

```sql
SELECT
    strftime('%Y-%m', invoice_date) AS month,
    ROUND(SUM(total_amount), 2) AS revenue
FROM invoices
GROUP BY month
ORDER BY month;
```

- Correct/Incorrect: Correct
- Summary: Shows billed revenue by month.

## 8. Monthly appointments

- Question: `How many appointments happened each month?`
- SQL generated:

```sql
SELECT
    strftime('%Y-%m', appointment_date) AS month,
    COUNT(*) AS appointment_count
FROM appointments
GROUP BY month
ORDER BY month;
```

- Correct/Incorrect: Correct
- Summary: Tracks total appointments month by month.

## 9. City with most patients

- Question: `Which city has the most patients?`
- SQL generated:

```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC
LIMIT 1;
```

- Correct/Incorrect: Correct
- Summary: Identifies the clinic's strongest patient city.

## 10. Appointments by status

- Question: `Show appointments by status.`
- SQL generated:

```sql
SELECT status, COUNT(*) AS appointment_count
FROM appointments
GROUP BY status
ORDER BY appointment_count DESC;
```

- Correct/Incorrect: Correct
- Summary: Groups appointments across scheduled, completed, cancelled, and no-show.

## 11. Completed appointments by doctor

- Question: `How many appointments were completed by each doctor?`
- SQL generated:

```sql
SELECT
    d.name AS doctor_name,
    COUNT(a.id) AS completed_appointments
FROM doctors d
LEFT JOIN appointments a
    ON a.doctor_id = d.id
   AND a.status = 'completed'
GROUP BY d.id, d.name
ORDER BY completed_appointments DESC;
```

- Correct/Incorrect: Correct
- Summary: Breaks down completed appointments by doctor.

## 12. Revenue by doctor

- Question: `Which doctor generated the highest revenue?`
- SQL generated:

```sql
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
```

- Correct/Incorrect: Correct
- Summary: Uses treatment costs as the revenue signal per doctor.

## 13. Outstanding balances

- Question: `Which patients still have unpaid balances?`
- SQL generated:

```sql
SELECT
    p.id,
    p.first_name || ' ' || p.last_name AS patient_name,
    ROUND(SUM(i.total_amount - i.paid_amount), 2) AS outstanding_balance
FROM patients p
JOIN invoices i ON i.patient_id = p.id
GROUP BY p.id, patient_name
HAVING outstanding_balance > 0
ORDER BY outstanding_balance DESC;
```

- Correct/Incorrect: Correct
- Summary: Returns patients with remaining invoice balances.

## 14. Average treatment cost by specialization

- Question: `Show average treatment cost by specialization.`
- SQL generated:

```sql
SELECT
    d.specialization,
    ROUND(AVG(t.cost), 2) AS average_treatment_cost
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.specialization
ORDER BY average_treatment_cost DESC;
```

- Correct/Incorrect: Correct
- Summary: Compares treatment pricing across specialties.

## 15. Most expensive treatments

- Question: `What are the top 5 most expensive treatments?`
- SQL generated:

```sql
SELECT
    treatment_name,
    ROUND(cost, 2) AS cost,
    duration_minutes
FROM treatments
ORDER BY cost DESC
LIMIT 5;
```

- Correct/Incorrect: Correct
- Summary: Lists the highest-cost treatment records.

## 16. New patients per month

- Question: `How many new patients registered each month?`
- SQL generated:

```sql
SELECT
    strftime('%Y-%m', registered_date) AS month,
    COUNT(*) AS new_patients
FROM patients
GROUP BY month
ORDER BY month;
```

- Correct/Incorrect: Correct
- Summary: Shows the registration trend across months.

## 17. Departments by doctor count

- Question: `Which departments have the most doctors?`
- SQL generated:

```sql
SELECT department, COUNT(*) AS doctor_count
FROM doctors
GROUP BY department
ORDER BY doctor_count DESC, department;
```

- Correct/Incorrect: Correct
- Summary: Counts doctors per department.

## 18. Doctors in cardiology

- Question: `Show all cardiology doctors.`
- SQL generated:

```sql
SELECT name, department, phone
FROM doctors
WHERE specialization = 'Cardiology'
ORDER BY name;
```

- Correct/Incorrect: Correct
- Summary: Filters the doctor roster for cardiology specialists.

## 19. Average invoice value

- Question: `What is the average invoice amount?`
- SQL generated:

```sql
SELECT ROUND(AVG(total_amount), 2) AS average_invoice_amount
FROM invoices;
```

- Correct/Incorrect: Correct
- Summary: Calculates the average billed amount per invoice.

## 20. Patients by city

- Question: `Show patient counts by city.`
- SQL generated:

```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC, city;
```

- Correct/Incorrect: Correct
- Summary: Returns patient volume by city for location comparison.
