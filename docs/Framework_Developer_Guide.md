# Framework Developer Guide

This guide provides a high-level overview of how the Clinical Data Repository (CDR) accelerator works. It is designed for developers, architects, or Cevo consultants who need to understand the data flow and architectural patterns without reading the detailed technical specifications in the Solution Design document.

## 1. The Core Philosophy: Config over Code

The primary goal of this accelerator is to minimize the amount of code required to onboard a new clinical dataset. We achieve this by separating **what** the pipeline does from **how** it does it.

The framework is built on three pillars:
1. **Driver Notebooks:** Handle the orchestration (e.g., "Run the Bronze pipeline for the patients table").
2. **Shared Utilities:** Contain the reusable Python/PySpark logic (e.g., a function that cleans strings or generates a hash).
3. **JSON Configs:** Tell the driver notebooks which tables, columns, and rules to apply.

## 2. The Medallion Flow

The accelerator processes data through three distinct layers:

```text
[ Raw Source Data (S3) ]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ BRONZE LAYER (Raw)                                     │
│ - Driver: bronze_ingest_mimic_iv                       │
│ - Config: bronze_config.json                           │
│ - Action: Ingests CSVs, adds audit metadata.           │
└────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ SILVER LAYER (Cleaned)                                 │
│ - Drivers: 01_core, 02_clinical, 03_orders             │
│ - Config: silver_config.json                           │
│ - Utils: 00_silver_utils                               │
│ - Action: Deduplicates, casts types, cleans strings.   │
└────────────────────────────────────────────────────────┘
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ GOLD LAYER (Business Ready)                            │
│ - Drivers: dimensions/, facts/, marts/                 │
│ - Action: Builds star schema, surrogate keys, metrics. │
│ - Output: Governed views for Dashboards and Genie.     │
└────────────────────────────────────────────────────────┘

```
## 3. Data Flow and Governance

Data does not flow directly from Bronze to Genie. Governance is applied at the very top layer to ensure security.

1. **Gold Build:** Produces `fact` and `dimension` tables, plus three wide `consumption views` (`admission_journey`, `icu_clinical_monitoring`, `hospital_operational_activity`).
2. **Governance:** The consumption views use `is_account_group_member()` to filter rows and mask columns based on the user's Databricks group.
3. **Consumption:** Users only interact with the governed views. They cannot access the underlying fact/dim tables.
4. **Interfaces:** The Streamlit app acts as a unified front door, routing users to the specific Dashboard and Genie Room their role is allowed to see.

## 4. How to Extend the Framework

| If you want to... | What you need to change |
|-------------------|-------------------------|
| **Add a new table to Bronze** | Add a new entry to `bronze_config.json`. No code changes. |
| **Add a new cleaning rule to Silver** | Add a new entry to `silver_config.json` referencing an existing function in `00_silver_utils`. |
| **Add a completely new cleaning function** | Write the Python function in `00_silver_utils`, add it to the registry, then reference it in `silver_config.json`. |
| **Add a new dimension or fact in Gold** | Create a new notebook in the `gold_layer/` folder following the existing patterns (surrogate keys, validation, overwrite logic). |
| **Onboard a completely new dataset** | Follow the `Dataset_Onboarding.md` guide. |

## 5. Key Technologies Used

*   **Storage:** Delta Lake (ACID transactions, time travel).
*   **Compute:** Databricks Workflows (job scheduling), PySpark.
*   **Governance:** Unity Catalog (RBAC, dynamic view security).
*   **AI:** Databricks Genie (Text-to-SQL).
*   **Frontend:** Streamlit (Databricks Apps).
