# Genie Example Queries

These questions will be configured under:

Configure → Examples → Example query

Do not add an example until its SQL has been manually validated.

---

# Patient Journey

## EX-PJ-01

Question:

How many hospital admissions are in the dataset?

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach correct admission counting.

---

## EX-PJ-02

Question:

How many unique patients are represented?

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach distinct patient counting.

---

## EX-PJ-03

Question:

What is the average hospital length of stay?

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach the validated LOS metric.

---

## EX-PJ-04

Question:

What percentage of hospital admissions required ICU care?

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach the ICU admission rate.

---

## EX-PJ-05

Question:

Which clinical services have the longest average hospital length of stay?

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach service grouping and LOS aggregation.

---

## EX-PJ-06

Question:

Compare average hospital length of stay between ICU and non-ICU admissions.

Source:

`gold.patient_journey`

SQL:

**CONFIRM AFTER GOLD**

Purpose:

Teach grouping by ICU status.

---

# ICU Clinical Monitoring

## EX-ICU-01

Question:

How many ICU stays are represented?

Source:

`gold.icu_clinical_monitoring`

SQL:

**CONFIRM AFTER GOLD**

---

## EX-ICU-02

Question:

Which care units have the highest clinical monitoring activity?

Source:

`gold.icu_clinical_monitoring`

SQL:

**CONFIRM AFTER GOLD**

---

## EX-ICU-03

Question:

Which clinical measurements generate the most warnings?

Source:

`gold.icu_clinical_monitoring`

SQL:

**CONFIRM AFTER GOLD**

---

# Hospital Pressure

## EX-HP-01

Question:

Which dates had the highest patient load?

Source:

`gold.hospital_pressure_daily`

SQL:

**CONFIRM AFTER GOLD**

---

## EX-HP-02

Question:

Which care units experienced the highest operational pressure?

Source:

`gold.hospital_pressure_daily`

SQL:

**CONFIRM AFTER GOLD**

---

## EX-HP-03

Question:

Show the trend in admissions and discharges over time.

Source:

`gold.hospital_pressure_daily`

SQL:

**CONFIRM AFTER GOLD**

---

# Optional Diagnosis / Procedure Examples

Only add these if supporting Gold sources are implemented.

## Most Common Diagnoses

Question:

What are the five most common diagnoses?

Source:

**CONFIRM AFTER GOLD**

SQL:

**CONFIRM AFTER GOLD**

---

## Most Common Procedures

Question:

What are the five most common procedures?

Source:

**CONFIRM AFTER GOLD**

SQL:

**CONFIRM AFTER GOLD**

---

# Example Promotion Checklist

Before adding any example to Genie:

- [ ] Gold table implemented
- [ ] required fields confirmed
- [ ] SQL manually tested
- [ ] expected result confirmed
- [ ] no double counting
- [ ] question wording tested
- [ ] generated Genie SQL compared with trusted SQL