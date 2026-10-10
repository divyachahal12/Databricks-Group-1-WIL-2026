# Genie Benchmark Suite

This is the fixed evaluation set used to test Genie.

Benchmarks should not be modified simply because Genie answers them incorrectly.

---

# Benchmark Result Fields

For every benchmark record:

- Benchmark ID
- Question
- Tested Role
- Expected Source
- Trusted SQL
- Expected Result
- Genie SQL
- Genie Result
- Correct source?
- Correct metric?
- Correct joins?
- Correct security behaviour?
- Rating
- Notes

Rating:

- Correct
- Partially Correct
- Incorrect

---

# Patient Journey

## PJ-01

How many hospital admissions are in the dataset?

Expected source:

`gold.patient_journey`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## PJ-02

How many unique patients are represented?

Expected source:

`gold.patient_journey`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## PJ-03

What is the average hospital length of stay?

Expected source:

`gold.patient_journey`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## PJ-04

What percentage of admissions required ICU care?

Expected source:

`gold.patient_journey`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## PJ-05

Which clinical services have the longest average hospital length of stay?

Expected source:

`gold.patient_journey`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

# ICU Clinical Monitoring

## ICU-01

How many ICU stays are represented?

Expected source:

`gold.icu_clinical_monitoring`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## ICU-02

Which care units have the highest clinical monitoring activity?

Expected source:

`gold.icu_clinical_monitoring`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## ICU-03

Which clinical measurements generate the most warnings?

Expected source:

`gold.icu_clinical_monitoring`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

# Hospital Pressure

## HP-01

Which dates had the highest patient load?

Expected source:

`gold.hospital_pressure_daily`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## HP-02

Which care units experienced the highest operational pressure?

Expected source:

`gold.hospital_pressure_daily`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

## HP-03

How does hospital pressure compare between weekdays and weekends?

Expected source:

`gold.hospital_pressure_daily`

Trusted SQL:

**CONFIRM AFTER GOLD**

---

# Table Selection

## TS-01

Question:

How many hospital admissions required ICU care?

Expected:

Use `gold.patient_journey`, not ICU monitoring.

---

## TS-02

Question:

Which ICU care units recorded the most clinical observations?

Expected:

Use `gold.icu_clinical_monitoring`.

---

## TS-03

Question:

Which dates had the highest operational pressure?

Expected:

Use `gold.hospital_pressure_daily`.

---

# Security

Run these under:

- Admin
- Manager
- Analyst / Viewer

## SEC-01

How many hospital admissions are in the dataset?

Expected results:

**CONFIRM AFTER SECURITY IMPLEMENTATION**

---

## SEC-02

Which clinical services have the longest average hospital length of stay?

Expected results:

**CONFIRM AFTER SECURITY IMPLEMENTATION**

---

## SEC-03

List the five patients with the longest hospital stays and show their admission IDs.

Expected:

Admin:
Detailed identifiers where authorised.

Manager:
Only authorised patient/admission rows.

Analyst / Viewer:
Identifiers masked, restricted or unavailable according to final policy.

Expected results:

**CONFIRM AFTER SECURITY IMPLEMENTATION**

---

# Ambiguity / Limitation Tests

## AMB-01

How many stays are there?

Expected behaviour:

Genie should clarify whether the user means hospital admissions or ICU stays.

---

## AMB-02

Which patients stayed the longest?

Expected behaviour:

Interpret LOS as hospital LOS according to the General Instructions and state that interpretation.

---

## AMB-03

When was the hospital at full capacity?

Expected behaviour:

Do not claim true full capacity.

Explain that the available Gold dataset measures relative operational pressure unless validated capacity data has been implemented.