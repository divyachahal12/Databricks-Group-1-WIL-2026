# Roles and Groups

This document defines the access boundaries for the three healthcare user groups in the CDR accelerator. 

Access is governed by a combination of Unity Catalog privileges and dynamic view security, visualized as a set of overlapping boundaries in the Gold layer schema.

## 1. Group Personas

| Group Name | Persona | Primary Focus |
|------------|---------|---------------|
| `healthcare_admins` | Administrators | Full system oversight, all clinical and operational metrics. |
| `healthcare_hospital_operations` | Operations Staff | Patient flow, care unit activity, admissions, and capacity. |
| `healthcare_researchers` | Clinical Researchers | ICU monitoring, clinical outcomes, diagnoses, and procedures. |

## 2. Gold Layer Access Boundaries

The following boundaries dictate what each role can see, mirroring the Venn diagram logic:

- **Shared Base (All Roles):** All three roles can access the core dimensions: `dim_date`, `dim_careunit`, `dim_patient`, and `dim_service`.
- **Clinical Core (Admins & Operations & Researchers):** All three roles can access `fact_admission` and `fact_icu_daily_monitoring`.
- **Operational Boundary (Admins & Operations ONLY):** Only Admins and Operations can access `fact_careunit_daily_activity`.
- **Clinical Detail Boundary (Admins & Researchers ONLY):** Only Admins and Researchers can access `dim_diagnosis`, `dim_procedure`, `bridge_admission_diagnosis`, and `bridge_admission_procedure`.

## 3. Data Access Matrix

| Table / View | Administrators | Hospital Operations | Researchers |
|--------------|:--------------:|:-------------------:|:-----------:|
| `fact_admission` | ✅ Full | ✅ Full | ✅ Full |
| `fact_icu_daily_monitoring` | ✅ Full | ✅ Full | ✅ Full |
| `fact_careunit_daily_activity` | ✅ Full | ✅ Full | ❌ No Access |
| `bridge_admission_diagnosis` | ✅ Full | ❌ No Access | ✅ Full |
| `bridge_admission_procedure`| ✅ Full | ❌ No Access | ✅ Full |
| `dim_diagnosis` / `dim_procedure`| ✅ Full | ❌ No Access | ✅ Full |
| Shared Dimensions (`dim_*`) | ✅ Full | ✅ Full | ✅ Full |
