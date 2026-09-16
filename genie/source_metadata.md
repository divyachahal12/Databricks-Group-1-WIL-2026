# Genie Source Metadata

This file contains the metadata required when adding Gold datasets to Genie.

Do not paste unconfirmed field names into Genie.

---

# 1. Patient Journey

## Source

`gold.patient_journey`

## Confirmed Purpose

Admission-level Gold dataset designed to summarise each hospital admission.

Intended analysis includes:

- hospital admissions
- patients
- hospital length of stay
- admission and discharge information
- transfers and care units
- clinical services
- ICU utilisation
- diagnoses and procedures
- mortality and outcomes

## Intended Grain

One row per hospital admission:

`hadm_id`

## Confirmed Core Identifiers

- `subject_id` = patient
- `hadm_id` = hospital admission

## Planned Source Tables

- patients
- admissions
- transfers
- services
- icustays
- diagnoses_icd
- d_icd_diagnoses
- procedures_icd
- d_icd_procedures

## Planned Information

- patient demographics
- admission/discharge information
- hospital LOS
- admission type/location
- first and last care unit
- transfer activity
- first and last service
- ICU utilisation
- primary diagnosis
- diagnosis count
- procedure count
- mortality

## Genie Table Description

**CONFIRM AFTER GOLD**

## Genie Column Descriptions

**CONFIRM AFTER GOLD**

## Validated Grain

**CONFIRM AFTER GOLD**

## Unique / Primary Key

**CONFIRM AFTER GOLD**

## Security Columns

**CONFIRM AFTER GOLD**

## Masked / Restricted Columns

**CONFIRM AFTER GOLD**

---

# 2. ICU Clinical Monitoring

## Source

`gold.icu_clinical_monitoring`

## Confirmed Purpose

Gold dataset designed to summarise clinical monitoring and ICU care activity.

Intended analysis includes:

- ICU stays
- clinical observation activity
- vital-sign summaries
- laboratory activity
- warnings / abnormal observations
- fluid input and output
- procedures
- care-unit comparisons

## Intended Grain

One row per ICU stay per clinical day:

`stay_id + clinical_date`

## Confirmed Core Identifiers

- `subject_id` = patient
- `hadm_id` = hospital admission
- `stay_id` = ICU stay

## Planned Source Tables

- icustays
- chartevents
- d_items
- labevents
- d_labitems
- inputevents
- outputevents
- procedureevents
- patients
- admissions

## Planned Information

- ICU care unit
- ICU LOS
- ICU day
- observation count
- distinct measurement count
- warning count
- selected vital-sign summaries
- lab activity
- abnormal lab count
- fluid input
- fluid output
- fluid balance
- procedure activity

## Genie Table Description

**CONFIRM AFTER GOLD**

## Genie Column Descriptions

**CONFIRM AFTER GOLD**

## Validated Grain

**CONFIRM AFTER GOLD**

## Unique / Primary Key

**CONFIRM AFTER GOLD**

## Security Columns

**CONFIRM AFTER GOLD**

## Masked / Restricted Columns

**CONFIRM AFTER GOLD**

---

# 3. Hospital Pressure

## Source

`gold.hospital_pressure_daily`

## Confirmed Purpose

Daily operational Gold dataset designed to identify periods of higher hospital workload and compare pressure between care units.

Intended analysis includes:

- patient load
- admissions
- discharges
- transfers
- ICU activity
- care-unit workload
- pressure over time
- weekday/weekend differences

## Intended Grain

One row per date per care unit:

`activity_date + careunit`

## Planned Source Tables

- admissions
- transfers
- icustays
- services
- patients

## Planned Information

- activity date
- care unit
- patient load
- daily admissions
- daily discharges
- net admission change
- transfers in/out
- ICU activity
- pressure score
- pressure level
- day/week/month fields

## Important Interpretation

This dataset measures observed workload.

It must not be described as true hospital bed capacity or staffing utilisation unless a validated capacity denominator is implemented.

## Genie Table Description

**CONFIRM AFTER GOLD**

## Genie Column Descriptions

**CONFIRM AFTER GOLD**

## Validated Grain

**CONFIRM AFTER GOLD**

## Unique / Primary Key

**CONFIRM AFTER GOLD**

## Security Columns

**CONFIRM AFTER GOLD**

---

# 4. Diagnosis Detail Source

## Required?

**CONFIRM AFTER GOLD**

Only create/add this source if detailed diagnosis analysis cannot be reliably supported by `gold.patient_journey`.

## Table Name

**CONFIRM AFTER GOLD**

## Grain

**CONFIRM AFTER GOLD**

## Join

**CONFIRM AFTER GOLD**

---

# 5. Procedure Detail Source

## Required?

**CONFIRM AFTER GOLD**

Only create/add this source if detailed procedure analysis cannot be reliably supported by `gold.patient_journey`.

## Table Name

**CONFIRM AFTER GOLD**

## Grain

**CONFIRM AFTER GOLD**

## Join

**CONFIRM AFTER GOLD**

---

# Final Source Checklist

Complete before adding tables to Genie:

- [ ] final table name
- [ ] validated grain
- [ ] unique key
- [ ] row count
- [ ] final column list
- [ ] important column descriptions
- [ ] security fields
- [ ] restricted/masked identifiers
- [ ] relationships to other Gold tables
- [ ] common categorical values checked
- [ ] synonyms required identified