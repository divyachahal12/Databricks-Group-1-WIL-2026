# Clinical Data Repository - Solution Design

**Project:** Enterprise CDR Solution Accelerator
**Platform:** Databricks Data Intelligence Platform
**Reference Dataset:** MIMIC-IV v3.1 (static scope)
**Architecture:** Medallion (Bronze → Silver → Gold)
**Governance:** Unity Catalog
**AI/BI Layer:** Databricks Genie

---

## 1. Overview

This document describes the architecture of a reusable Clinical Data Repository (CDR) solution accelerator built on Databricks. The accelerator implements a Medallion architecture, with Bronze and Silver using a config-driven processing pattern and Gold using reusable dimensional modelling patterns to produce business-ready analytical models and governed consumption views.

MIMIC-IV serves as the reference implementation. The design aims to minimise the work required to onboard a new clinical dataset by reusing common ingestion, cleaning, deployment and governance patterns, while allowing dataset-specific Gold models to be developed where analytical requirements differ.

---

## 2. Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Config-driven ingestion and cleaning** | Dataset-specific Bronze and Silver behaviour is declared in JSON configuration |
| **Separation of orchestration and reusable logic** | Driver notebooks orchestrate processing while shared utilities contain reusable transformation logic |
| **Medallion layering** | Bronze stores raw data, Silver cleans and standardises it, and Gold provides analytical models |
| **Least-privilege governance** | Unity Catalog groups, governed views, row filtering and selective column masking restrict access by role |
| **Auditability** | Bronze and Silver processing record run IDs, row counts, timing and errors |
| **Bounded parallelism** | Independent workflow tasks run concurrently where dependencies allow |
| **Three-level namespace** | Data objects use `<catalog>.<schema>.<table>` naming |
| **Governed consumption layer** | Dashboards, Genie and applications consume governed Gold views rather than underlying fact and dimension tables |

---

## 3. The Framework Pattern

Bronze and Silver follow a shared config-driven processing pattern:

| Component | Role | Knows | Doesn't Know |
|-----------|------|-------|--------------|
| **Driver notebook** | Orchestration | Which tables to process and when | Detailed transformation implementation |
| **Shared utilities** | Reusable logic | How to ingest, clean, validate and write | Which specific dataset is being processed |
| **JSON config** | Declarative behaviour | Tables, keys, mappings and processing rules | How those rules are executed |

The general rule for Bronze and Silver is:

**Reusable logic in utilities. Orchestration in drivers. Dataset behaviour in configuration.**

Gold follows a different pattern because analytical modelling is more heterogeneous. Gold notebooks explicitly define dimensions, facts, bridges and governed consumption views while following common modelling and validation conventions.

Metadata and Genie deployment return to a config-driven pattern so that documentation and semantic-layer behaviour can be version controlled and reproduced.

### Repository Structure

    cdr-accelerator/
        drivers/
            bronze_layer/ 
                 bronze_ingest_mimic_iv
            silver_layer/ 
                01_silver_core_reference
                02_silver_clinical_events
                03_silver_orders_meds_icu
            gold_layer/ 
                dimensions/
                    01_build_dimensions
                facts/
                    02_build_admission_star
                    03_build_icu_daily_fact
                    04_build_operational_activity_fact
                marts/
                    05_build_consumption_views
        utils/
            00_silver_utils
        deployment/
            01_apply_gold_metadata
            02_apply_gold_governance
            03_deploy_genie_agent
            apply_gold_metadata.py
            build_genie_config.py
            deploy_genie_agent.py
            
        configs/
            bronze_config.json
            silver_config.json
            metadata/
                admission_journey.json
                hospital_operational_activity.json
                icu_clinical_monitoring.json
            genie/ 
                instructions.json
                sample_questions.json
                sql_examples.json
                benchmarks.json
                joins.json
                sql_snippets.json
        governance/
            roles_and_groups.md
            app/
                app.py
                app.yaml
                requirements.txt
                README.md

---

## 4. Layer Specifications

### 4.1 Bronze Layer

**Purpose:** Ingest raw source files into Delta tables exactly as sourced, with full lineage metadata.

**Driver:** `drivers/bronze_layer/bronze_ingest_mimic_iv`
**Config:** `bronze_config.json` at `/Volumes/cdr_bronze/config/table_config/`

#### Behaviour

- Recursively scans the S3 landing zone for `.csv` files
- Derives table names from filenames
- Reads merge keys from `bronze_config.json`
- Falls back to SHA-256 row hash when no reliable key exists
- Supports `auto`, `historical`, `incremental` load modes
- Writes Delta tables with `_ingest_timestamp`, `_source_file`, `_run_id`
- Logs every file to an audit table

**Input format:** CSV. MIMIC-IV ships as CSV.
**Storage format:** Delta Lake, which stores Parquet files plus a transaction log.


#### Load Type Resolution

| Widget | Table Exists? | Effective Load Type |
|--------|---------------|---------------------|
| `historical` | any | `HISTORICAL_FULL_LOAD` (overwrite) |
| `incremental` | yes | `INCREMENTAL_MERGE` |
| `incremental` | no | `INITIAL_LOAD` |
| `auto` | yes | `INCREMENTAL_MERGE` |
| `auto` | no | `INITIAL_LOAD` |

#### Key Handling

| Scenario | Behaviour |
|----------|-----------|
| Config has key list | Uses key list for merge |
| Config value is `null` | Row hash fallback |
| Key not unique in source | Logs warning, row hash fallback |
| Duplicate rows on merge key | Deduplicates before write |

Keyless tables in MIMIC-IV: `chartevents`, `emar_detail`

#### Audit Table

**Table:** `cdr_bronze.raw_mimic_iv.ingestion_audit_log`

**Columns:** `run_id`, `source_file_path`, `target_table`, `load_type`, `status`, `row_count`, `rows_inserted`, `rows_updated`, `start_time`, `end_time`, `duration_seconds`, `notes`, `error_message`

#### Widgets

| Widget | Default | Purpose |
|--------|---------|---------|
| `base_folder_path` | `s3://mimic-iv-datasets/mimic-iv-dataset-3.1` | Source S3 folder |
| `run_id` | *(empty)* | Shared run identifier |
| `load_type` | `auto` | Dropdown: `auto`/`historical`/`incremental` |
| `table_filter` | *(empty)* | Comma-separated list for testing |
| `table_config_path` | `/Volumes/.../bronze_config.json` | Path to merge-key config |

#### Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Input format | CSV | Matches MIMIC-IV distribution format |
| Storage format | Delta Lake | Parquet files plus a transaction log |
| S3 scan | Recursive | Handles nested folders in MIMIC-IV (`hosp/`, `icu/`) |
| Keyless tables | SHA-256 row hash fallback | Deterministic, no manual keys needed |
| Write mode | Delta merge on existing tables | Preserves history, supports incremental loads |
| Metadata columns | Three added | `_ingest_timestamp`, `_source_file`, `_run_id` |
| Load modes | Three supported | auto, historical, incremental |
| Audit | One table per layer | Self-contained retention |


#### Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **Streaming source** | Replace CSV scan with Auto Loader |
| **JSON/Parquet sources** | Add `file_format` field to config |
| **Multiple sources per table** | Add `file_pattern` glob support |
| **Historical backfill** | Use `historical` load type; overwrites cleanly |
| **Near-real-time** | Auto Loader + Delta Live Tables |
| **Additional metadata columns** | Extend the `df_bronze` transformation block |

---

### 4.2 Silver Layer

**Purpose:** Clean, validate, deduplicate, and standardise Bronze tables.

**Driver notebooks:** `drivers/silver_layer/01_silver_core_reference`, `02_silver_clinical_events`, `03_silver_orders_meds_icu`
**Shared logic:** `utils/00_silver_utils`
**Config:** `/Volumes/cdr_silver/config/silver_config/silver_config.json`

#### Behaviour

- Reads `silver_config.json` to determine which tables each driver owns (via `silver_notebook` field)
- Applies column mappings, derived columns, deduplication, quality rules
- Generates a SHA-256 `_natural_key` for tables with `needs_surrogate_key: true`
- Writes cleansed tables with `_silver_timestamp` and `_run_id`
- Shares `run_id` with Bronze for full lineage
- Logs every table to a Silver audit table

#### Quality Rule Actions

| Action | Effect |
|--------|--------|
| `quarantine` | Invalid rows written to quarantine table; removed from flow |
| `flag` | Flag column added; rows remain |

#### Initial Run vs Subsequent Runs

| Run | Behaviour |
|-----|-----------|
| First run (table does not exist) | Creates the table with a full load |
| Later run (table exists) | Merges into the existing table on the configured keys |

Reruns are safe. They do not duplicate rows. They update existing rows and insert new ones.

#### Cleaning Rule Dispatch

The cleaning rules are declared in config and dispatched by name from a function registry in `00_silver_utils`. Available functions:

| Function | Purpose |
|----------|---------|
| `fill_missing` | Replace null or empty values with a placeholder |
| `standardize_category` | Trim, collapse spaces, drop trailing periods, uppercase |
| `rename_column` | Rename a column |
| `coalesce_and_drop` | Pick the longer of two text columns, drop both originals |
| `drop_columns` | Drop a list of columns |
| `strip_html` | Remove HTML tags from free text |
| `cast_boolean` | Cast a column to boolean |
| `map_values_to_default` | Replace specific values (case-insensitive) with a default |
| `set_constant` | Overwrite every value in a column with a fixed literal |

Adding a new cleaning rule type means writing one function, adding it to `FN_REGISTRY`, and referencing it by name from config.

#### Special Transforms

Some tables require logic that cannot be expressed as declarative rules. These are registered by table name in the driver notebook and applied after the config-driven cleaning rules. Example: `omr` BMI recompute, which groups height and weight, filters missing values, and recomputes BMI.

#### Audit Table

**Table:** `cdr_silver.processed_mimic_iv.silver_audit_log`

**Columns:** `run_id`, `layer`, `source_table`, `target_table`, `load_type`, `status`, `row_count`, `rows_inserted`, `rows_updated`, `start_time`, `end_time`, `duration_seconds`, `error_message`.


#### Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Driver split | Three drivers by domain | Enables parallel execution after Bronze |
| Table routing | `silver_notebook` field in config | Adding a table does not require editing a notebook |
| Cleaning dispatch | `FN_REGISTRY` in utils | Adding a rule type is one function and one config key |
| Surrogate keys | SHA-256 `_natural_key` for keyless tables | Deterministic and idempotent |
| Bespoke logic | `special_transform` per driver | Applied after config-driven rules |
| Run ID | Shared with Bronze | Full traceability across layers |
| Rerun safety | Merge on configured keys | Reruns are idempotent |
| Audit fields | Includes layer and source_table | Distinguishes Silver runs from Bronze |

#### Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **OMOP CDM** | Map Silver tables to OMOP standard entities |
| **FHIR alignment** | Add FHIR resource mapping in config |
| **Multi-language data** | Add language-specific cleaning rules |
| **Trial data** | Add visit-based partitioning |
| **De-identification** | Add PHI removal as a `special_transform` |

---

### 4.3 Gold Layer

**Purpose:** The Gold layer builds business-ready dimensional models and governed consumption views on top of Silver. It follows reusable modelling patterns while allowing dataset-specific analytical models to be implemented where required.

**Build notebooks:**

- `drivers/gold_layer/dimensions/01_build_dimensions`
- `drivers/gold_layer/facts/02_build_admission_star`
- `drivers/gold_layer/facts/03_build_icu_daily_fact`
- `drivers/gold_layer/facts/04_build_operational_activity_fact`
- `drivers/gold_layer/marts/05_build_consumption_views`

**Deployment notebooks:**

- `deployment/01_apply_gold_metadata`
- `deployment/02_apply_gold_governance`
- `deployment/03_deploy_genie_agent`

**Configuration:**

- `Configs/metadata/*.json`
- `Configs/genie/*.json`

**Target schema:** `cdr_gold.analytics_<dataset>`

#### The Gold Pattern

Gold follows a five-stage build pattern that applies to any clinical dataset, followed by three deployment stages.


| Stage | What It Produces | Reusable? |
|-------|------------------|-----------|
| 1. Dimensions | Shared lookup tables (patient, date, careunit, service, diagnosis, procedure) | Pattern reusable, content dataset-specific |
| 2. Fact tables | One fact per analytical grain (admission, ICU day, careunit day) | Pattern reusable, content dataset-specific |
| 3. Bridges | Many-to-many link tables between facts and dimensions | Pattern reusable, content dataset-specific |
| 4. Consumption views | Governed views that combine facts and dimensions for downstream consumers | Pattern reusable, audience rules dataset-specific |
| 5. Build orchestration | Databricks Workflow that sequences stages 1 to 4 | Fully reusable |

After the Gold build completes, three deployment stages run in sequence:

| Stage | What It Produces | Reusable? |
|-------|------------------|-----------|
| 6. Metadata deployment | Unity Catalog table and column comments applied from version-controlled metadata config | Fully reusable |
| 7. Governance deployment | Catalog/schema usage and governed-view access for healthcare roles | Group and view definitions are dataset-specific |
| 8. Genie deployment | Builds and deploys the Clinical Data Agent from version-controlled semantic configuration | Config-driven and reusable |

The deployment sequence is intentionally:

**Metadata → Governance → Genie**

This ensures the governed consumption views are documented and secured before they are exposed through the natural-language analytics layer.

#### Stage 1: Dimensions

Each dimension declares a grain and a surrogate key strategy. The pattern is:

1. Read the Silver source
2. Deduplicate to the grain
3. Generate a deterministic surrogate key
4. Validate row count, key uniqueness, and null key count
5. Publish

For MIMIC-IV, seven dimensions are built:

| Dimension | Grain | Surrogate Key |
|-----------|-------|---------------|
| `dim_patient` | One row per `subject_id` | `xxhash64(subject_id)` |
| `dim_date` | One row per calendar date between first admission and last discharge | `yyyymmdd` integer |
| `dim_careunit` | One row per standardised careunit name | `xxhash64(careunit_name)` |
| `dim_service` | One row per hospital service code | `xxhash64(service_code)` |
| `dim_diagnosis` | One row per `icd_code` + `icd_version` | `xxhash64(icd_code, icd_version)` |
| `dim_procedure` | One row per `icd_code` + `icd_version` | `xxhash64(icd_code, icd_version)` |
| `dim_medication` | One row per `drug` + `formulary_drug_code` + `prod_strength` | `xxhash64(drug, formulary_drug_code, prod_strength)` |

**For a new dataset:** the same six dimensions apply if the source has patients, dates, care units, services, and coded diagnoses or procedures. If a dataset lacks one of these, that dimension is skipped. If it has an extra dimension (for example, a provider dimension), a new entry is added following the same pattern.

#### Stage 2: Fact Tables

Each fact declares a grain, its measure columns, and its foreign keys to dimensions. The pattern is:

1. Build a spine at the fact's grain
2. Join Silver sources for measures
3. Aggregate to the declared grain
4. Join dimension keys
5. Validate
6. Publish

For MIMIC-IV, three facts are built:

| Fact | Grain | Measures | Foreign Keys |
|------|-------|----------|--------------|
| `fact_admission` | One row per `hadm_id` | Length of stay, age at admission, recorded race, mortality flag, ICU flag, transfer count, service change count, diagnosis count, procedure count | patient, admission date, discharge date, first and last careunit, initial and final service, primary diagnosis |
| `fact_icu_daily_monitoring` | One row per `stay_id` + `clinical_date` | Vitals, labs, fluid balance, procedure counts | patient, date, careunit |
| `fact_careunit_daily_activity` | One row per `activity_date` + `careunit` | Active patient count, arrival count, departure count, ICU activity count | date, careunit |

**For a new dataset:** the fact pattern is the same. What changes is which facts matter. A clinical trial dataset might have `fact_visit` and `fact_treatment_administration` instead of `fact_admission` and `fact_icu_daily_monitoring`.

#### Stage 3: Bridges

Bridges preserve many-to-many relationships. In MIMIC-IV, admissions have multiple diagnoses and multiple procedures, so two bridges link them:

| Bridge | Grain | Purpose |
|--------|-------|---------|
| `bridge_admission_diagnosis` | One row per admission diagnosis | Links `fact_admission` to `dim_diagnosis`, flags primary diagnosis |
| `bridge_admission_procedure` | One row per admission procedure | Links `fact_admission` to `dim_procedure` |
| `bridge_admission_medication` | One row per `hadm_id` + `medication_key` | Links `fact_admission` to `dim_medication` for medications prescribed during the admission |

**For a new dataset:** any dataset with many-to-many relationships uses bridges. The pattern is identical. Add or remove bridges based on the model.

#### Stage 4: Consumption Views

Consumption views provide the governed analytical interface between the internal Gold dimensional model and downstream consumers.

Downstream tools do not query the Gold facts and dimensions directly. Instead, dashboards, Genie and applications query these wide consumption views.

For MIMIC-IV, three governed views are built:

| View | Primary Source | Authorised Audience |
|------|----------------|--------------------|
| `admission_journey` | `fact_admission` plus relevant dimensions | Researchers, hospital operations, administrators |
| `icu_clinical_monitoring` | `fact_icu_daily_monitoring` plus relevant dimensions | Researchers, administrators |
| `hospital_operational_activity` | `fact_careunit_daily_activity` plus relevant dimensions | Hospital operations, administrators |

The views implement role-aware behaviour using `is_account_group_member()`.

Two governance techniques are used:

- **Row filtering:** users outside the authorised audience receive no rows from a restricted view.
- **Column masking:** selected sensitive fields remain part of the view but their values are replaced or suppressed for roles that are not authorised to see them.

This provides a stable analytical interface while keeping the underlying Gold facts, dimensions and bridges private.

#### Stage 5: Build Orchestration

The Gold build runs as a Databricks Workflow:

| Task | Depends On | Purpose |
|------|------------|---------|
| `gold_dimensions` | none | Build all shared dimensions |
| `gold_admissions` | `gold_dimensions` | Build `fact_admission` and both bridges |
| `gold_icu_daily` | `gold_dimensions` | Build `fact_icu_daily_monitoring` |
| `gold_operational` | `gold_dimensions` | Build `fact_careunit_daily_activity` |
| `gold_consumption_views` | all three fact tasks | Build the three governed views |

The three fact tasks run in parallel after dimensions complete. The views task runs only after all facts succeed.

The workflow is configured with `queue.enabled = true` and `max_concurrent_runs = 1` so overlapping runs queue rather than conflict.

#### Stage 6: Metadata Deployment

Metadata deployment is performed by `deployment/01_apply_gold_metadata`.

The notebook reads JSON metadata definitions from `Configs/metadata/` and applies table and column comments to the governed Gold consumption views in Unity Catalog.

The deployment performs three stages:

1. **Dry-run validation** — compares configured metadata with the deployed view schemas without changing Unity Catalog.
2. **Live apply** — applies table and column comments.
3. **Post-deployment validation** — queries Unity Catalog metadata to confirm the persisted descriptions match the configuration.

The metadata files act as a shared source of truth for:

- Unity Catalog documentation;
- field descriptions used by the Genie semantic layer.

For a new dataset, new metadata files are created for its governed consumption views while the deployment logic remains unchanged.


#### Stage 7: Governance Deployment

Governance deployment is performed by `deployment/02_apply_gold_governance`.

The implementation uses three Databricks account groups:

- `healthcare_admins`
- `healthcare_hospital_operations`
- `healthcare_researchers`

The deployment notebook performs four main steps:

| Step | What It Does |
|------|--------------|
| **Pre-check** | Confirms that all governed consumption views exist |
| **Namespace grants** | Grants `USE CATALOG` on `cdr_gold` and `USE SCHEMA` on `analytics_mimic_iv` |
| **View grants** | Grants `SELECT` on the governed views |
| **Post-check** | Reviews catalog, schema and view grants to verify the intended access model |

Healthcare consumer groups are not granted direct access to the underlying Gold fact, dimension or bridge tables.

`USE CATALOG` and `USE SCHEMA` only allow users to resolve and navigate the namespace. They do not provide access to the underlying data.

`SELECT ON VIEW` allows a user to query the governed view, while the SQL definition of that view determines which rows and values are visible to the user's role.

Role-specific filtering and masking are implemented using `is_account_group_member()` inside the governed view SQL.

This separates two concerns:

1. **Unity Catalog privileges** determine whether the user may query the governed object.
2. **Dynamic view logic** determines what that authorised user may see.

Because the consumption views are recreated during the Gold build, governance deployment must run after the views are rebuilt so that the required explicit view grants are restored.

##### Role Access Matrix

| Role | `admission_journey` | `icu_clinical_monitoring` | `hospital_operational_activity` |
|------|---------------------|---------------------------|---------------------------------|
| Administrator | Full access | Full access | Full access |
| Researcher | Governed access | Full access | No rows |
| Hospital Operations | Governed access | No rows | Full access |

Within `admission_journey`, additional column-level rules apply:

- Administrators can see all exposed fields.
- Researchers can see diagnosis information but do not receive precise `admittime` or `dischtime` timestamps.
- Researchers retain generalised temporal fields such as `admission_date`, `admission_year` and `admission_month` for analytical filtering.
- Hospital Operations users retain admission and operational measures, but primary diagnosis fields are masked as `RESTRICTED`.

The distinction between `UNKNOWN` and `RESTRICTED` is intentional:

- `UNKNOWN` means the user is authorised to see the field but the source value is unavailable.
- `RESTRICTED` means the field exists but is not available to the current role.

#### Stage 8: Downstream Consumers

After the governed views are built and secured, two downstream consumers are deployed on top of them:

- **AI/BI Genie.** A natural-language agent configured on the three governed views. Deployment, semantic layer, and accuracy evaluation are described in Section 6.
- **Streamlit app.** A Databricks App that presents dashboards and Genie in a single interface. Described in Section 7.
Neither consumer changes the Gold data model. Both read from the governed views only.

#### Design Decisions

| Decision | What Was Built | Note|
|----------|--------------|-----------------|
|Build pattern	|Code in notebooks, not config-driven	|Gold build logic is heterogeneous; config-driven build would require a query DSL|
|Deployment pattern	|Config-driven for metadata and Genie	|Strongest accelerator layer|
|Surrogate key strategy	|xxhash64 of natural keys	|Deterministic and stable across runs|
|Date dimension key	|Integer yyyymmdd	|Human-readable and sorts correctly as a number|
|Write mode	|Full overwrite each run	|Gold rebuilds from Silver; merge not required|
|Primary diagnosis selection	|Prefer ICD-10, then lowest ICD code	|Deterministic when multiple seq_num = 1 rows exist|
|Fluid input allocation	|Proportional by overlap seconds	|Handles multi-day infusions without double counting|
|Null fluid balance	|Null when input or output missing	|Prevents incomplete days being treated as zero|
|High activity flag	|Per-careunit 95th percentile	|Activity is relative to each careunit's own baseline|
| Role-based row filtering | `is_account_group_member()` conditions in governed view SQL | Allows a single governed view to return different datasets according to the signed-in user's account group |
| Selective column masking | Role-aware `CASE` expressions in governed view SQL | Allows permitted rows to remain available while sensitive values are suppressed for selected roles |
|Consumption surface	|Views, not tables	|Consumers query governed surfaces, not raw facts|

#### Use Case Extensions

| Scenario | Extension |
|----------|-----------|
|New dataset with a similar clinical model	|Write new metadata and Genie config. Update governance notebook. Build new dimension and fact notebooks using the existing pattern.|
|Dataset with no ICU data	|Skip ICU dimensions and facts. Remove ICU views. The rest of the pattern is unchanged.|
|Dataset with no diagnoses or procedures	|Skip diagnosis and procedure dimensions and bridges.|
|Dataset with a provider dimension	|Add dim_provider following the same surrogate key pattern.|
|Config-driven Gold build	|Add a gold_config.json declaring entity names, grains, and keys. Refactor notebooks to loop over config.|
|Incremental Gold	|Replace overwrite with merge on surrogate keys.|
|Unity Catalog row filters	|Move is_account_group_member() from view SQL to a row filter on underlying tables.|
|Unity Catalog masking policies	|Move CASE WHEN ... RESTRICTED from view SQL to a masking policy on the underlying column.|
|Additional Genie agents	|Duplicate configs/genie/ for a new dataset and point a new deployment notebook at it.|
|OMOP CDM	|Map Gold dimensions and facts to OMOP standard tables.|

---
## 5. Reusability & Onboarding

The accelerator separates reusable processing engines from dataset-specific analytical modelling.

Bronze and Silver are designed to onboard new datasets primarily through configuration.

Gold provides reusable modelling patterns, validation approaches and deployment tooling, but new datasets may require new dimension, fact and consumption-view notebooks because analytical grains and business requirements differ between datasets.

Metadata and Genie deployment remain strongly config-driven.

### 5.1 What Changes and What Does Not

| Component | Changes per new dataset |
|-----------|--------------------------|
| Bronze driver notebook | No |
| Silver driver notebooks | No |
| Gold dimension notebook | Yes, new dimensions follow the existing pattern |
| Gold fact notebook | Yes, new facts follow the existing pattern |
| Gold view notebook | Yes, new views follow the existing pattern |
| Metadata config | Yes |
| Genie config | Yes |
| Governance notebook| Yes, group and view lists updated as per role type|
| Bronze and Silver configs | Yes |
| Unity Catalog objects | Yes |
| Workflows | Parameter changes only |

### 5.2 Layer-by-Layer Reusability

| Layer | Reusable without change | Requires new config | Requires new code |
|-------|------------------------|---------------------|-------------------|
| Bronze | Full | New `bronze_config.json` | No |
| Silver | Full | New `silver_config.json` | No |
| Gold dimensions | Pattern | No | New dimension notebook per dimension |
| Gold facts | Pattern | No | New fact notebook per fact |
| Gold views | Pattern | No | New view SQL per view |
| Metadata deployment | Full | New metadata JSON | No |
| Governance deployment(TO BE UPDATED) | Full | Updated group and view lists | No |
| Genie deployment | Full | New Genie JSON files | No |

### 5.3 Onboarding Steps

To add a new clinical dataset:

1. Write `bronze_config.json` (source paths, table list, merge keys)
2. Write `silver_config.json` (column mappings, quality rules, routing)
3. Write new dimension, fact, and view notebooks by copying existing patterns
4. Write metadata JSON files under `configs/metadata/`
5. Write Genie JSON files under `configs/genie/`
6. Define the required audience groups and governance rules for the new consumption views.
7. Create Unity Catalog objects for the new dataset
8. Point the workflows at the new configs
9. Run the Bronze, Silver, and Gold workflows in order
10. Run the deployment notebooks in order

Bronze, Silver, metadata and Genie deployment are primarily configuration-driven. Gold analytical modelling requires dataset-specific notebooks that follow the established dimensional modelling patterns.

---
## 6. AI/BI Genie

**Purpose:** Provide a natural-language analytical interface over the governed Gold consumption views so that researchers, hospital operations staff and administrators can query permitted clinical data without writing SQL.

**Deployment notebook:** `deployment/03_deploy_genie_agent`

**Configuration:** `Configs/genie/*.json`

**Agent title:** Genie Agent

**Data sources:**

- `admission_journey`
- `icu_clinical_monitoring`
- `hospital_operational_activity`

### 6.1 Overview

Genie is Databricks' natural-language-to-SQL feature. It reads annotated tables and columns, plus a configured semantic layer, and translates user questions into SQL against the governed Gold views.

The accelerator treats Genie configuration as a first-class artifact. Every part of the semantic layer lives in a config file, is version-controlled, and is deployed by a notebook rather than configured through the Databricks UI. This means the Genie agent can be rebuilt for any dataset by writing new config files, not by clicking through the UI.

### 6.2 Configuration Files

Six JSON files define the Genie agent. Each has a specific role.

| File | Purpose |
|------|---------|
| `instructions.json` | Plain-text guidance on grain, joins, metric rules, and governance. The most important file. |
| `sample_questions.json` | Starter questions shown to users in the Genie UI |
| `sql_examples.json` | Reference SQL queries with usage guidance, teaching the agent how to query each view |
| `benchmarks.json` | Test questions with expected SQL, used to score agent accuracy |
| `joins.json` | Declared joins between Gold views, including relationship type and when to use them |
| `sql_snippets.json` | Reusable filters, expressions, and measures (currently empty) |

### 6.3 The Semantic Layer

The Genie semantic layer has four parts.

**Grain declarations.** Each view's grain is stated so the agent knows what "one row" means. For example, `admission_journey` is one row per `hadm_id`, and `icu_clinical_monitoring` is one row per `stay_id` + `clinical_date`.

**Join specifications.** `joins.json` declares the supported direct relationship between the governed views. For MIMIC-IV, `icu_clinical_monitoring` joins to `admission_journey` on `hadm_id` as a many-to-one relationship. Because ICU monitoring contains multiple stay-days for the same admission, instructions require ICU measures to be aggregated to the intended analytical grain before admission-level measures are combined with them.

**Metric rules.** `instructions.json` defines what each metric means and how it should be calculated. This includes:
- Hospital LOS uses `hospital_los_days`
- ICU LOS averages exclude rows where `total_icu_los_days` is NULL
- Fluid balance uses `net_fluid_balance_ml` only when `fluid_balance_complete = TRUE`
- Total patient movement is arrivals plus departures
- Daily patient turnover is total movement divided by active patient count

**Governance rules.** `instructions.json` also defines how the agent should behave when a user's role restricts access to a view or column. For example, if a researcher queries `hospital_operational_activity`, the agent explains that the view is restricted for their role rather than saying the dataset is empty.

### 6.4 Interpretation Rules

The semantic layer includes explicit guidance on how to phrase findings. The agent is instructed to describe observed patterns without implying causation, clinical severity, or operational causes.

Preferred phrasing:
- "had a higher observed mortality rate"
- "was associated with longer LOS"
- "had greater recorded patient movement"

Avoided phrasing:
- "these patients were more severe"
- "the unit was overcrowded"
- "the hospital exceeded capacity"

This keeps Genie responses descriptive, not diagnostic, which is critical for non-technical users.

### 6.5 Benchmark Set

The accelerator was evaluated against a set of **29 benchmark questions** derived from clinical research papers and standard analytical scenarios. 

Of these 29 questions:
- **26 questions** are defined in the version-controlled `benchmarks.json` file.
- **3 questions** (including the Metoprolol prescription mortality comparison) were configured directly in the Genie UI for extended testing against the new prescriptions view.

The benchmark set covers:

| Domain | Question Focus |
|--------|---------------|
| **Admission & Demographics** | Average/median LOS by admission type and age group, mortality rates by service. |
| **ICU Clinical Monitoring** | Mortality based on first-day labs (haemoglobin, sodium), 3-day fluid balance, vital-sign warnings. |
| **Operational Activity** | Care units with the most direct admissions, patient workload, daily arrivals/departures. |
| **Cross-view & Prescriptions** | Abnormal lab activity and LOS, Metoprolol mortality comparison, yearly movement comparisons. |

### 6.6 Accuracy Evaluation

Agent accuracy is measured by running each benchmark question through the deployed Genie agent and comparing the returned SQL result against the expected SQL result.

To avoid mixing analytical accuracy with intentional role-based restrictions, the evaluation is split into two parts:
1. **Semantic accuracy:** Whether Genie generates a correct analytical result.
2. **Governance validation:** Whether Genie correctly respects role-based access restrictions.

For semantic accuracy, benchmarks were run using an administrator account so that all governed views were available.

**Scoring Method:** The evaluation used strict result set matching. A response was marked as "Correct" only if the resulting table structure and values matched the ground truth. 

**Final Result:** The Genie agent achieved **97% semantic accuracy (28 out of 29 benchmarks passed)**, significantly exceeding the 80% target. 

#### 6.6.1 How to Run the Evaluation

The evaluation runs in five steps.

**Step 1: Confirm preconditions.**
Ensure Gold views are built, metadata is applied (`01_apply_gold_metadata`), governance is applied (`02_apply_gold_governance`), and the agent is deployed (`03_deploy_genie_agent`).

**Step 2: Open the Genie agent.**
Open the deployed Genie Agent in the Databricks workspace using an administrator account.

**Step 3: Run each benchmark question.**
Submit the questions through the Genie UI. You must test the 26 questions defined in `benchmarks.json`, plus the 3 additional questions configured directly in the Genie UI. For each:
1. Capture the SQL that Genie returns.
2. Run the returned SQL.
3. Compare the returned result sets against the expected SQL.

**Step 4: Score each benchmark.**
Score each semantic benchmark as one of:

| Score | Meaning |
|-------|---------|
| Correct | Result set matches the expected result set |
| Partially correct | Query runs but returns incorrect aggregations |
| Incorrect | Query fails or the SQL does not answer the question |

Governance behaviour is scored separately as **Pass** or **Fail**. A correctly restricted query is a successful governance test, but not a correct analytical benchmark.

**Step 5: Report results.**
Report the semantic accuracy figure, a summary table of results, a failure analysis, and a separate governance validation summary.

#### 6.6.2 Failure Analysis

One benchmark failed. Understanding *why* it failed provides critical insight into the semantic layer's behaviour.

**Failed Question:** *"Do admissions with a vital-sign warning in ICU have a longer hospital stay?"*

**Failure Mode:** Missing columns and substituted logic. 
The evaluation's ground truth expected a table returning four specific metrics: `admissions`, `median_los_days`, `mean_los_days`, and `mortality_pct`. Genie correctly calculated the LOS metrics but substituted `mortality_pct` with `p90_los_days` (the 90th percentile of length of stay). 

Because the resulting table did not match the ground truth's structure, the evaluation failed. This indicates that while Genie understood the LOS comparison perfectly, it autonomously decided to expand the analysis to the upper tail of the distribution (90th percentile) instead of strictly adhering to the requested mortality metric.

#### 6.6.3 Reporting Format

*(Note: The 28 passing questions are summarized by domain below. The single failure is detailed in the table).*

| Category | Passed | Notes |
|----------|--------|-------|
| Admission Demographics | 7/7 | Average LOS, median LOS, ICU involvement, mortality by service. |
| ICU Clinical Monitoring | 8/8 | Haemoglobin/Sodium mortality, 3-day fluid balance, vital-sign warnings. |
| Operational Activity | 6/6 | Direct admissions, workload, patient-days, daily arrivals/departures. |
| Cross-View & Prescriptions | 7/8 | Metoprolol mortality, abnormal lab activity, yearly movement comparisons. |

**Detailed Benchmark Failure:**

| # | Question | Score | Notes |
|---|----------|-------|-------|
| 1 | Do admissions with a vital-sign warning in ICU have a longer hospital stay? | **Incorrect** | **Missing Logic:** Genie returned `p90_los_days` instead of the ground truth's `mortality_pct`. The resulting table structure did not match the strict evaluation criteria. |

**Overall Semantic Accuracy:** 28/29 (97%).

#### 6.6.4 Governance Validation Summary

Governance validation was performed separately from the semantic accuracy benchmarks to ensure that role-based security rules were correctly enforced.

| Test Scenario | Role Tested | Expected Behaviour | Result |
|---------------|-------------|--------------------|--------|
| Query `hospital_operational_activity` | `healthcare_researchers` | Genie explains access restriction | **PASS** |
| Query `icu_clinical_monitoring` | `healthcare_hospital_operations` | Genie explains access restriction | **PASS** |
| Query primary diagnosis in `admission_journey` | `healthcare_hospital_operations` | Diagnosis field returns `RESTRICTED` | **PASS** |
| Query all views | `healthcare_admins` | Full unmasked access to all views | **PASS** |

*Detailed screenshots demonstrating Genie responding to the Researcher and Hospital Operations roles are provided in:
[**Genie Governance Validation**](https://github.com/divyachahal12/Databricks-Group-1-WIL-2026/tree/feature/darren/docs/AI%20Genie%20Governance%20Pics)

### 6.7 Deployment

The deployment notebook `03_deploy_genie_agent` runs after the Gold views are built and after metadata has been applied.

Deployment flow:
1. Locate the repository root and import the deployment modules.
2. Build the Genie configuration by reading the six config files.
3. Export a readable preview of the built configuration.
4. Run a dry run of the deployment.
5. Check whether a Genie space with the target title already exists.
6. Create or update the space.
7. Validate the deployed agent.

The notebook supports both first-time deployment and updates. If the space exists, it is updated rather than duplicated.

### 6.8 Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Config-driven agent | All six config files live in the repo | Version-controlled, reproducible |
| Table metadata source | `configs/metadata/` shared with Unity Catalog | Single source of truth for descriptions |
| Benchmark set | 29 fixed questions with expected SQL | Enables accuracy scoring |
| Accuracy metric | Result set match | Allows equivalent SQL |
| Governance behaviour | Agent explains access restrictions | Prevents misleading "no data" responses |
| Interpretation rules | Descriptive, not causal | Keeps responses appropriate for non-technical users |

### 6.9 Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| Multiple Genie agents | Duplicate `configs/genie/` per dataset and point a new deployment notebook at it |
| Domain-specific agents | Build separate agents for ICU, admissions, and operational audiences |
| Automated scoring | Add a scoring script that runs all benchmarks and reports accuracy |
| SQL snippet library | Populate `sql_snippets.json` with reusable filters and measures |
| Multi-language | Configure Genie instructions in additional languages |

---
## 7. AI/BI Dashboard and Databricks App

### 7.1 AI/BI Dashboard

The solution provides two user-facing consumption layers on top of the governed Gold views: a native Databricks AI/BI Dashboard for visual analytics, and a Databricks App that combines dashboards and Genie into a single interface.

The dashboard contains three analytical pages:

1. **Admission Journey Overview**
2. **ICU Clinical Monitoring Overview**
3. **Hospital Operational Activity**

The pages are aligned with the main analytical audiences: 

- Admission Journey supports all authorised healthcare roles.
- ICU Clinical Monitoring is intended for Researchers and Administrators.
- Hospital Operational Activity is intended for Hospital Operations and Administrators.

The dashboard uses the same governed Gold views as Genie, ensuring dashboard results and natural-language analytics are based on the same curated data definitions.

Dashboard access should use individual user data permissions so that Unity Catalog and dynamic-view governance are evaluated using the signed-in user's identity.

### 7.2 Databricks App

A Databricks App provides the primary user-facing entry point for the accelerator. It combines the AI/BI dashboards and the Clinical Data Agent (Genie) into a single, unified Streamlit interface.

The application uses account-group membership to control which navigation options and data tools are presented to the signed-in user.

#### Routing and Authentication

The Streamlit application (`app.py`) enforces application-level routing through three steps:

1. **Authentication:** The app retrieves the logged-in user's email from the `X-Forwarded-Email` header provided by the Databricks App environment.
2. **Group Lookup:** The app uses the Databricks SDK (`WorkspaceClient`) to query the workspace and retrieve the user's group memberships.
3. **Routing:** Based on the user's group, the app loads the specific Dashboard ID and Genie Room ID configured for that role via a hardcoded mapping dictionary (`GENIE_ID_MAPPING`).

For example, a user in `healthcare_hospital_operations` is routed to the operational dashboard and the operational Genie room. A user in `healthcare_researchers` is routed to the clinical dashboard and clinical Genie room.

#### Navigation Matrix

| Role | Admission | ICU | Operations | Genie |
|------|-----------|-----|------------|-------|
| Administrator | Yes | Yes | Yes | Yes |
| Researcher | Yes | Yes | No | Yes |
| Hospital Operations | Yes | No | Yes | Yes |


Application-level navigation is a user-experience control rather than the primary security boundary. Unity Catalog and the governed consumption views continue to enforce data security independently. 
This means that even if a hidden application route is bypassed, data-level access control still prevents the user from seeing unauthorised data.

---

## 8. Governance

Governance is implemented using Unity Catalog privileges together with dynamic security logic in the Gold consumption views.  It is not just a single configuration; it operates at two distinct layers: the data layer and the application layer.

### 8.1 Healthcare Roles

Three Databricks account-level groups are used:

- `healthcare_admins`
- `healthcare_hospital_operations`
- `healthcare_researchers`

These groups represent the main analytical audiences supported by the reference implementation.

### 8.2 Privilege Model

The healthcare groups receive:

- `USE CATALOG` on `cdr_gold`
- `USE SCHEMA` on `cdr_gold.analytics_mimic_iv`
- `SELECT` on the governed consumption views

Users are not granted direct access to the underlying Gold facts, dimensions or bridge tables.

Namespace privileges and data privileges are intentionally separated:

- `USE CATALOG` allows the catalog to be referenced.
- `USE SCHEMA` allows the schema to be referenced.
- `SELECT ON VIEW` allows the governed view to be queried.

These privileges alone do not determine what rows and values the user can see.

### 8.3 Dynamic View Security

Role-specific data restrictions are implemented inside the SQL definitions of the governed consumption views using:

`is_account_group_member()`

Two forms of security are used.

**Row filtering**

Entire datasets are hidden from roles that do not require them.

Examples:

- `icu_clinical_monitoring` returns rows only for Administrators and Researchers.
- `hospital_operational_activity` returns rows only for Administrators and Hospital Operations users.

**Column masking**

Users may retain access to an admission record while selected values are replaced or suppressed.

Within `admission_journey`:

- Hospital Operations users receive `RESTRICTED` for primary diagnosis fields.
- Researchers retain diagnosis information.
- Researchers do not receive precise admission and discharge timestamps.
- Generalised admission date, year and month fields remain available to all authorised roles.

### 8.4 Role Matrix

| Role | Admission Journey | ICU Clinical Monitoring | Hospital Operational Activity |
|------|-------------------|-------------------------|-------------------------------|
| Administrator | Full | Full | Full |
| Researcher | Governed | Full | No rows |
| Hospital Operations | Governed / diagnosis masked | No rows | Full |

### 8.5 Application-Level Access (Streamlit App)

While Unity Catalog enforces data security at the database level, the Databricks App provides a unified, curated interface for Dashboards and Genie. It enforces application-level governance through group-based routing.

1. **Authentication:** The app retrieves the user's email from the `X-Forwarded-Email` header.
2. **Group Lookup:** It queries the Databricks workspace to find the user's group memberships.
3. **Routing:** Based on the group, it loads the specific Dashboard ID and Genie Room ID configured for that group.

For example, a user in `healthcare_hospital_operations` sees the operational dashboard and the operational Genie room. A user in `healthcare_researchers` sees the clinical dashboard and the clinical Genie room.

### 8.6 Defence in Depth

The application and dashboard layers may hide interfaces that are irrelevant to a user's role, but this is not relied upon as the security boundary.

Data access remains protected by Unity Catalog and the governed views.

Therefore, even if a user attempts to query a restricted dataset outside the intended interface, the underlying governance rule still applies.

### 8.7 Genie Governance

Genie queries the same governed consumption views used by SQL and dashboards.

The agent therefore does not define a separate security model.

Its semantic instructions include additional guidance so that restricted results are explained appropriately.

For example, if a Researcher requests operational activity, an empty governed result should not automatically be interpreted as evidence that no operational data exists. Where appropriate, Genie explains that the information is unavailable to the current role.

### 8.8 Validation

Governance was validated using role-specific user testing.

Validation included:

- successful access to permitted views;
- zero-row responses for restricted views;
- masked diagnosis fields for Hospital Operations;
- access to clinical ICU data for Researchers;
- denial of direct access to underlying Gold fact tables;
- Genie responses under restricted roles.

This verifies both the Unity Catalog privilege model and the dynamic behaviour implemented in the governed views.

### 8.9 Deployment Dependency

Governance deployment runs after the Gold consumption views are created.

Because recreating the views can replace their explicit view-level grants, the deployment sequence is:

**Gold Build → Metadata → Governance → Genie Deployment**

This ensures every rebuilt consumption surface is documented, secured and then exposed to downstream consumers.

### 8.10 Framework for Governance Setup for New Datasets

In this project, the Unity Catalog setup and groups were configured manually via the UI due to time constraints. However, for the accelerator to be reusable by Cevo, the following process should be codified.

To onboard a new dataset:

1. **Define the Personas:** Decide the user groups for the new dataset (e.g., `finance_admins`, `clinical_reviewers`).
2. **Create Unity Catalog Groups:** Create these groups at the account or workspace level.
3. **Map the Venn Diagram:** Decide which facts and dimensions each group can access, mirroring the role boundaries used in this project.
4. **Update View SQL:** Apply the `is_account_group_member()` logic in the new Gold views.
5. **Update Streamlit Config:** Update the `GENIE_ID_MAPPING` dictionary in `app.py` to route the new groups to the new dashboards and Genie spaces.
6. **(Future Framework Step) Generate SQL Scripts:** Export the `CREATE GROUP`, `GRANT USE CATALOG`, and `GRANT SELECT` statements into the `governance/sql/` folder so the environment can be rebuilt via code.

### 8.11 Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Data-level enforcement | Inline `is_account_group_member()` in view SQL | Avoids the complexity of setting up Unity Catalog row filters and masking policies. |
| App-level enforcement | Streamlit group-based routing | Prevents users from accessing tools (dashboards/Genie) meant for other roles. |
| Group structure | Three distinct groups | Balances the need for data isolation with the administrative overhead of managing too many groups. |
| Tagging | Not implemented | Removed from scope due to time constraints. Documented as a future extension. |
| Script-based setup | Not implemented | Setup was done manually via UI for this project. SQL script generation is listed as a future extension for the accelerator. |

### 8.12 Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **Unity Catalog Row Filters** | Move the `is_account_group_member()` logic from the view SQL into a Unity Catalog row filter function on the underlying tables. |
| **Unity Catalog Masking Policies** | Move the `CASE WHEN ... RESTRICTED` logic into a Unity Catalog masking policy on the underlying columns. |
| **Data Classification Tags** | Implement Unity Catalog tags (e.g., `PII`, `PHI`, `Sensitive`) to automate masking based on tag presence rather than hardcoded column names. |
| **Automated Group Provisioning** | Use SCIM or the Databricks Account API to automatically create and manage user groups based on an external Identity Provider (IdP). |
| **Configuration as Code** | Move the Streamlit `GENIE_ID_MAPPING` dictionary into a JSON config file, so new group routing can be added without editing Python code. |
| **Audit Logging** | Enable and monitor Databricks audit logs to track who accessed which governed view and when, ensuring compliance with internal policies. |

---


## 9. Orchestration

The pipeline is orchestrated using **Databricks Jobs & Pipelines**. To maintain clear separation of concerns and allow independent re-runs, the pipeline is split into three distinct Jobs.

### 9.1 Job 1: Bronze & Silver Pipeline

This job handles the ingestion and cleaning phases. 

| Task | Depends On | Purpose |
|------|------------|---------|
| `bronze_ingest` | — | Ingests all source files |
| `silver_core_reference` | `bronze_ingest` | Cleans core/reference tables |
| `silver_clinical_events` | `bronze_ingest` | Cleans clinical event tables |
| `silver_orders_meds_icu` | `bronze_ingest` | Cleans orders/ICU tables |

The three Silver tasks run in parallel after Bronze completes.

### 9.2 Job 2: Gold Layer Build

This job builds the dimensional models and governed views. It is separate from the deployment so that it can be run independently during development.

| Task | Depends On | Purpose |
|------|------------|---------|
| `gold_dimensions` | none | Build all shared dimensions |
| `gold_admissions` | `gold_dimensions` | Build `fact_admission` and both bridges |
| `gold_icu_daily` | `gold_dimensions` | Build `fact_icu_daily_monitoring` |
| `gold_operational` | `gold_dimensions` | Build `fact_careunit_daily_activity` |
| `gold_consumption_views` | all three fact tasks | Build the three governed views |

The three fact tasks run in parallel after dimensions complete. The views task runs only after all facts succeed.

### 9.3 Job 3: Gold Genie Deployment

This job handles the post-build deployment steps. It must run immediately after the Gold Layer Build Job completes to restore security and update the AI layer.

| Task | Depends On | Purpose |
|------|------------|---------|
| `apply_gold_metadata` | — | Apply and validate Unity Catalog metadata |
| `apply_gold_governance` | `apply_gold_metadata` | Restore and validate role-based access |
| `deploy_genie_agent` | `apply_gold_governance` | Build and deploy the Clinical Data Agent |

The deployment order is significant because the downstream Genie layer should only be deployed after the governed views have been rebuilt, documented and secured.

### 9.4 Shared Run ID

Each pipeline run uses one `run_id`:
- The Bronze task generates the run ID.
- Bronze publishes it as a Databricks task value.
- Each Silver task reads it via `get_shared_run_id()`, fetching from the upstream task key `bronze_ingest`.
- If a Silver notebook is run standalone, it falls back to a fresh UUID and logs a warning.

The same `run_id` appears in every Bronze audit row and every Silver audit row for that run, enabling end-to-end traceability. The Gold build workflow does not currently share the run ID with Bronze and Silver. Gold uses a separate `_gold_timestamp` audit column per row instead.

### 9.5 Job Parameters

| Key | Purpose |
|-----|---------|
| `run_id` | Shared identifier (`{{job.start_time.iso_datetime}}`) |
| `table_filter` | Optional comma-separated list for testing (Bronze/Silver only) |

### 9.6 Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Orchestrator | Databricks Jobs | Native, no external infrastructure |
| Job structure | Three separate jobs | Allows independent re-runs of Bronze/Silver, Gold Build, and Gold Deployment |
| Silver tasks | Parallel after Bronze | Three tasks run concurrently |
| Gold facts | Parallel after dimensions | Three tasks run concurrently |
| Run ID | Databricks task values | Bronze publishes, Silver reads |
| Standalone fallback | Fresh UUID with warning | Prevents silent divergence of audit trail |
| Test parameter | `table_filter` | Enables fast iteration |

### 9.7 Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **Streaming** | Add continuous jobs |
| **Multiple clusters** | Use task-level cluster config |
| **External dependencies** | Add pre-flight HTTP task |
| **Notification chains** | Add webhook task on completion |
| **Gold run ID sharing** | Extend the task value pattern to Gold tasks |
---

## 10. Known Limitations

| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Static/batch only | No real-time data | Auto Loader + streaming |
| Gold requires human design | Facts/dimensions declared per dataset | Templated Gold per domain |
| `special_transform` requires code | Some tables need custom logic | Expand declarative rules |
| Single-tenant catalog naming | One catalog per layer | Multi-tenant strategy |
| Dynamic security is embedded in governed view SQL | Role rules are coupled to consumption-view definitions | Consider Unity Catalog row filters and column masks for larger deployments |
| Role-aware App navigation is not the primary security boundary | Hidden UI elements alone cannot secure data | Continue enforcing all access through Unity Catalog and governed views |

---

## 11. Summary


---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | [Date] | [Author] | Initial solution design |
