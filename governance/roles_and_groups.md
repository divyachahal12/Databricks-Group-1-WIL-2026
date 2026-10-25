# Roles and Groups

## 1. Overview
This document describes how roles/users and role/user groups are set up and maintained in Databricks. Access is governed by a combination of Unity Catalog privileges and dynamic view security, visualized as a set of overlapping boundaries in the Gold layer schema.
It covers where each type of object is managed (account level or workspace level) and the steps for configuring groups so that access to Unity Catalog resources can be granted consistently.
It also defines the access boundaries for the three healthcare user groups in the CDR accelerator. 
**Scope:**
1. Creating and maintaining roles/users and role/user groups
2. How account-level and workspace-level configuration relate to each other

## 2. Role and Group Configuration

All user and group configuration is done in **Databricks**.

**Requirement:** Access to **Unity Catalog**, since groups are used as the principals when granting permissions on catalogs, schemas, and tables.

### Steps

1. **Create users and groups at the account level.**

   Open the Databricks Account Console and go to **User management**. From here you can create users and add them to user groups.

2. **Mirror each group at the workspace level.**
   
   For every user group created at the account level, create a group with the same name in the workspace. You do **not** need to create individual users at the workspace level.

3. **Maintain users and groups in the right place.**
   
   - **Users** are maintained at the **account level** only.
   - **User groups** must be managed at **both** the account level and the workspace level.

| Object | Account Level | Workspace Level |
|--------|:-------------:|:---------------:|
| Users  | ✅ Managed here | ❌ Not required |
| Groups | ✅ Managed here | ✅ Must mirror account groups |

> **Note:** Keep group names identical across both levels so that permissions resolve correctly.

## 4. Group Personas

ADD UML DIAGRAM

| Group Name | Persona | Primary Focus |
|------------|---------|---------------|
| `healthcare_admins` | Administrators | Full system oversight, all clinical and operational metrics. |
| `healthcare_hospital_operations` | Operations Staff | Patient flow, care unit activity, admissions, and capacity. |
| `healthcare_researchers` | Clinical Researchers | ICU monitoring, clinical outcomes, diagnoses, and procedures. |

## 5. Gold Layer Access Boundaries

The following boundaries dictate what each role can see,as in the UML diagram:

- **Shared Base (All Roles):** All three roles can access the core dimensions: `dim_date`, `dim_careunit`, `dim_patient`, and `dim_service`.
- **Clinical Core (Admins & Operations & Researchers):** All three roles can access `fact_admission` and `fact_icu_daily_monitoring`.
- **Operational Boundary (Admins & Operations ONLY):** Only Admins and Operations can access `fact_careunit_daily_activity`.
- **Clinical Detail Boundary (Admins & Researchers ONLY):** Only Admins and Researchers can access `dim_diagnosis`, `dim_procedure`, `bridge_admission_diagnosis`, and `bridge_admission_procedure`.

## 6. Data Access Matrix

| Table / View | Administrators | Hospital Operations | Researchers |
|--------------|:--------------:|:-------------------:|:-----------:|
| `fact_admission` | ✅ Full | ✅ Full | ✅ Full |
| `fact_icu_daily_monitoring` | ✅ Full | ✅ Full | ✅ Full |
| `fact_careunit_daily_activity` | ✅ Full | ✅ Full | ❌ No Access |
| `bridge_admission_diagnosis` | ✅ Full | ❌ No Access | ✅ Full |
| `bridge_admission_procedure`| ✅ Full | ❌ No Access | ✅ Full |
| `dim_diagnosis` / `dim_procedure`| ✅ Full | ❌ No Access | ✅ Full |
| Shared Dimensions (`dim_*`) | ✅ Full | ✅ Full | ✅ Full |
