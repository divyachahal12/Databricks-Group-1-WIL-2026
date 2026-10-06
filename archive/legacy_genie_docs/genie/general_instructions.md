# Genie General Instructions

## Paste into Genie

### Core identifiers

- `subject_id` identifies a unique patient.
- `hadm_id` identifies a unique hospital admission.
- `stay_id` identifies an ICU or unit stay.
- Do not treat these identifiers as interchangeable.

### Counting rules

- When asked for patients, count distinct `subject_id`.
- When asked for hospital admissions, count distinct `hadm_id`.
- When asked for ICU stays, count distinct `stay_id`.
- Do not count diagnosis, procedure, transfer or event rows as separate admissions.

### Business terminology

- LOS means hospital length of stay unless ICU LOS is explicitly requested.
- ICU admission means a hospital admission containing at least one ICU stay.
- Mortality means in-hospital mortality unless another outcome is explicitly requested.
- Hospital pressure means observed operational workload from the Hospital Pressure Gold dataset.
- Do not describe hospital pressure as true bed-capacity utilisation unless a validated capacity denominator exists.

### Dataset selection

- Use `gold.patient_journey` for admission, patient, LOS, service, care-unit, ICU-utilisation and outcome questions.
- Use `gold.icu_clinical_monitoring` for ICU monitoring, clinical observations, laboratory activity, fluids and ICU procedures.
- Use `gold.hospital_pressure_daily` for workload, patient load, admissions, discharges, transfers and pressure-over-time questions.
- Use additional diagnosis or procedure detail tables only when the requested detail cannot be answered from the main Gold datasets.

### Analytical behaviour

- Use the documented Gold metrics rather than creating alternative definitions.
- Avoid joins that inflate patient, admission or ICU-stay counts.
- Clearly state the grouping used when a question could have multiple interpretations.
- Ask for clarification when the user's question is genuinely ambiguous.
- Do not invent missing clinical definitions, values or relationships.
- Do not interpret descriptive relationships as proof of causation.

### Security

- Operate only within the current user's authorised Unity Catalog access.
- Do not attempt to bypass row filters, column masks or table permissions.
- If a requested field is unavailable to the user, explain that the detail is unavailable in their authorised view.
- Different users may receive different results because their permitted data scope differs.

### Clinical use

- Provide analytical summaries only.
- Do not provide medical diagnosis, treatment recommendations or individual clinical advice.

---

# CONFIRM AFTER GOLD

Before pasting into Genie:

- Confirm final Gold table names.
- Confirm identifier fields remain `subject_id`, `hadm_id` and `stay_id`.
- Confirm the implemented definition of ICU admission.
- Confirm the implemented mortality field.
- Confirm final hospital-pressure terminology.
- Remove any instruction referring to a field or table that was not implemented.


