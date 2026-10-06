# Genie Semantic Definitions

This file contains the structured semantic definitions that should be configured through Genie Examples.

Only validated SQL expressions should be entered into Genie.

---

# Measures

## Patient Journey

### Total Admissions

Business meaning:

Number of unique hospital admissions.

SQL:

**CONFIRM AFTER GOLD**

Expected basis:

Distinct `hadm_id`.

---

### Distinct Patients

Business meaning:

Number of unique patients.

SQL:

**CONFIRM AFTER GOLD**

Expected basis:

Distinct `subject_id`.

---

### Average Hospital LOS

Business meaning:

Average hospital length of stay in days.

SQL:

**CONFIRM AFTER GOLD**

Gold field required:

**CONFIRM AFTER GOLD**

---

### ICU Admission Rate

Business meaning:

Percentage of hospital admissions containing at least one ICU stay.

SQL:

**CONFIRM AFTER GOLD**

ICU indicator required:

**CONFIRM AFTER GOLD**

---

### In-Hospital Mortality Rate

Business meaning:

Percentage of hospital admissions ending in in-hospital mortality.

SQL:

**CONFIRM AFTER GOLD**

Mortality field required:

**CONFIRM AFTER GOLD**

---

## ICU Clinical Monitoring

### Total ICU Stays

Business meaning:

Number of unique ICU stays.

SQL:

**CONFIRM AFTER GOLD**

Expected basis:

Distinct `stay_id`.

---

### Clinical Observation Count

Business meaning:

Number of clinical observations represented by the Gold monitoring dataset.

SQL:

**CONFIRM AFTER GOLD**

---

### Warning / Abnormal Observation Count

Business meaning:

Number of monitoring observations meeting the implemented warning or abnormal criteria.

SQL:

**CONFIRM AFTER GOLD**

---

### Net Fluid Balance

Business meaning:

Recorded fluid input minus recorded fluid output.

SQL:

**CONFIRM AFTER GOLD**

---

## Hospital Pressure

### Active Patient Load

Business meaning:

Number of active patients represented for a date/care unit.

SQL:

**CONFIRM AFTER GOLD**

---

### Daily Admissions

Business meaning:

Number of admissions during the selected date or period.

SQL:

**CONFIRM AFTER GOLD**

---

### Daily Discharges

Business meaning:

Number of discharges during the selected date or period.

SQL:

**CONFIRM AFTER GOLD**

---

### Pressure Score

Business meaning:

Project-defined measure of relative operational workload.

Formula:

**CONFIRM AFTER GOLD**

Important:

This must not be interpreted as true percentage capacity.

---

# Filters

Only configure filters that exist in the final Gold schema.

## Planned Filters

### ICU Admissions

Definition:

Hospital admissions that contain at least one ICU stay.

SQL condition:

**CONFIRM AFTER GOLD**

---

### Non-ICU Admissions

Definition:

Hospital admissions with no ICU stay.

SQL condition:

**CONFIRM AFTER GOLD**

---

### Weekend

Definition:

Dates classified as Saturday or Sunday.

SQL condition:

**CONFIRM AFTER GOLD**

---

### High Pressure

Definition:

Dates / care units classified as high pressure according to the final pressure methodology.

SQL condition:

**CONFIRM AFTER GOLD**

---

# Fields

Prefer physically implemented Gold columns rather than creating duplicate Genie-calculated fields.

Potential fields requiring Genie definitions:

**CONFIRM AFTER GOLD**

Only create Genie Fields where a useful analytical field was not appropriate to materialise in Gold.

---

# Joins

No joins should be configured until both table grains and key uniqueness have been validated.

## Patient Journey → Diagnosis Detail

Required:

**CONFIRM AFTER GOLD**

Join SQL:

**CONFIRM AFTER GOLD**

Cardinality:

**CONFIRM AFTER GOLD**

---

## Patient Journey → Procedure Detail

Required:

**CONFIRM AFTER GOLD**

Join SQL:

**CONFIRM AFTER GOLD**

Cardinality:

**CONFIRM AFTER GOLD**

---

## Patient Journey → ICU Clinical Monitoring

Required for Genie?

**CONFIRM AFTER GOLD**

Join SQL:

**CONFIRM AFTER GOLD**

Cardinality:

Expected to be one admission to many ICU monitoring rows, but must be validated.

---

# Semantic Validation Checklist

Before adding a Measure / Filter / Field / Join:

- [ ] underlying Gold fields exist
- [ ] SQL tested manually
- [ ] expected result known
- [ ] no row multiplication
- [ ] denominator confirmed
- [ ] null handling confirmed
- [ ] join cardinality validated
- [ ] measure produces same result as trusted SQL