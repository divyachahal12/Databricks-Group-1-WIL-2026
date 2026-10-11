# Clinical Data Repository - Solution Design

**Project:** Enterprise CDR Solution Accelerator
**Platform:** Databricks Data Intelligence Platform
**Reference Dataset:** MIMIC-IV v3.1 (static scope)
**Architecture:** Medallion (Bronze → Silver → Gold)
**Governance:** Unity Catalog
**AI/BI Layer:** Databricks Genie

---

## 1. Overview

This document describes the architecture of a reusable Clinical Data Repository (CDR) solution accelerator built on Databricks. The accelerator implements the Medallion architecture using a config-driven pattern, separating orchestration from logic and declaring dataset-specific behaviour in JSON config files.

MIMIC-IV serves as the reference implementation. The design goal: onboarding a new clinical dataset requires writing new configs - not new notebooks.

---

## 2. Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Config-driven behaviour** | Dataset-specific logic lives in JSON configs |
| **Separation of orchestration and logic** | Driver notebooks orchestrate; shared utils contain logic |
| **Medallion layering** | Bronze (raw), Silver (cleaned), Gold (dimensional) |
| **Zero-trust governance** | PII/PHI masked by default; RBAC via Unity Catalog |
| **Auditability** | Every run logged with run ID, row counts, timing, errors |
| **Bounded parallelism** | Independent tasks run concurrently via Workflows |
| **Three-level namespace** | All tables use `<catalog>.<schema>.<table>` |

---

## 3. The Framework Pattern

Every layer follows the same pattern:

| Component | Role | Knows | Doesn't Know |
|-----------|------|-------|--------------|
| **Driver notebook** | Orchestration | Which tables, when to run | How to clean/aggregate |
| **Shared utils notebook** | Reusable logic | How to ingest, clean, write | Which dataset it operates on |
| **JSON config** | Declarative behaviour | What columns, keys, rules | How to execute |

**The rule:** logic in utils. Orchestration in drivers. Behaviour in config.

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
            02_deploy_genie_agent
            03_apply_gold_governance
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
            sql/
                01_catalogs.sql 
                02_schemas.sql
                03_volumes.sql
                04_grants.sql
                05_masking_policies.sql
                06_row_filters.sql
                07_tags.sql
            app/
                app.py
                app.yaml
                requirements.txt
                README.md
            docs/
                roles_and_groups.md
                masking_policies.md
                tags.md
                app_deployment.md

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

**Purpose:** The Gold layer builds business-ready dimensional models and governed consumption views on top of Silver. It is structured as a reusable pattern so that any clinical dataset can be modelled the same way.

**Build notebooks:** `drivers/gold_layer/dimensions/01_build_dimensions`, `drivers/gold_layer/facts/02_build_admission_star`, `drivers/gold_layer/facts/03_build_icu_daily_fact`, `drivers/gold_layer/facts/04_build_operational_activity_fact`, `drivers/gold_layer/marts/05_build_consumption_views`

**Deployment notebooks:** `deployment/01_apply_gold_metadata`, `deployment/02_deploy_genie_agent`, `deployment/03_apply_gold_governance`

**Config:** `configs/metadata/*.json`, `configs/genie/*.json`

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

After the build completes, three deployment stages run as separate notebooks:

| Stage | What It Produces | Reusable? |
|-------|------------------|-----------|
| 6. Metadata deployment | Unity Catalog table and column comments applied from config | Fully reusable |
| 7. Governance deployment | Group grants applied to governed views | Group list and view list dataset-specific |
| 8. Downstream consumers | Genie agent and Streamlit app deployed on the governed views | Config-driven, reusable |

#### Stage 1: Dimensions

Each dimension declares a grain and a surrogate key strategy. The pattern is:

1. Read the Silver source
2. Deduplicate to the grain
3. Generate a deterministic surrogate key
4. Validate row count, key uniqueness, and null key count
5. Publish

For MIMIC-IV, six dimensions are built:

| Dimension | Grain | Surrogate Key |
|-----------|-------|---------------|
| `dim_patient` | One row per `subject_id` | `xxhash64(subject_id)` |
| `dim_date` | One row per calendar date between first admission and last discharge | `yyyymmdd` integer |
| `dim_careunit` | One row per standardised careunit name | `xxhash64(careunit_name)` |
| `dim_service` | One row per hospital service code | `xxhash64(service_code)` |
| `dim_diagnosis` | One row per `icd_code` + `icd_version` | `xxhash64(icd_code, icd_version)` |
| `dim_procedure` | One row per `icd_code` + `icd_version` | `xxhash64(icd_code, icd_version)` |

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
| `fact_admission` | One row per `hadm_id` | Length of stay, age at admission, mortality flag, ICU flag, transfer count, service change count, diagnosis count, procedure count | patient, admission date, discharge date, first and last careunit, initial and final service, primary diagnosis |
| `fact_icu_daily_monitoring` | One row per `stay_id` + `clinical_date` | Vitals, labs, fluid balance, procedure counts | patient, date, careunit |
| `fact_careunit_daily_activity` | One row per `activity_date` + `careunit` | Active patient count, arrival count, departure count, ICU activity count | date, careunit |

**For a new dataset:** the fact pattern is the same. What changes is which facts matter. A clinical trial dataset might have `fact_visit` and `fact_treatment_administration` instead of `fact_admission` and `fact_icu_daily_monitoring`.

#### Stage 3: Bridges

Bridges preserve many-to-many relationships. In MIMIC-IV, admissions have multiple diagnoses and multiple procedures, so two bridges link them:

| Bridge | Grain | Purpose |
|--------|-------|---------|
| `bridge_admission_diagnosis` | One row per admission diagnosis | Links `fact_admission` to `dim_diagnosis`, flags primary diagnosis |
| `bridge_admission_procedure` | One row per admission procedure | Links `fact_admission` to `dim_procedure` |

**For a new dataset:** any dataset with many-to-many relationships uses bridges. The pattern is identical. Add or remove bridges based on the model.

#### Stage 4: Consumption Views

Consumption views are governed views that combine facts and dimensions into wide analytical surfaces. They are what Genie, dashboards, and the Streamlit app query.

For MIMIC-IV, three views are built:

| View | Source | Audience |
|------|--------|----------|
| `admission_journey` | `fact_admission` joined to patient, careunit, service, and diagnosis dimensions | Researchers, hospital operations, admins |
| `icu_clinical_monitoring` | `fact_icu_daily_monitoring` joined to patient, admission, and careunit | Researchers, admins |
| `hospital_operational_activity` | `fact_careunit_daily_activity` | Hospital operations, admins |

Each view applies row-level filtering and column-level masking inline using `is_account_group_member()`.

**For a new dataset:** the view pattern is the same. What changes is which audiences exist and which columns are sensitive. The audience rules are declared per view, not in a shared config, because audience needs vary by use case.

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

Built by 01_apply_gold_metadata. This notebook reads the JSON metadata files from configs/metadata/ and applies them to the three governed views in Unity Catalog.

The notebook performs three steps:

1.A dry run that validates configured metadata against the deployed Gold view schemas without making changes.
2.A live apply that sets table and column comments.
3.A validation step that queries information_schema.tables and information_schema.columns to confirm the persisted metadata matches the config. Any mismatch raises an assertion error.
The JSON metadata files are the source of truth for both Unity Catalog documentation and Genie table and column descriptions.

**For a new dataset:** write one metadata file per Gold view. The notebook does not change.

#### Stage 7: Governance Deployment

Built by 03_apply_gold_governance. This notebook grants access to the three healthcare groups.

| Step	| What It Does|
|----------|---------------|
|Pre-check	|Confirms all three governed views exist before granting|
|Catalog and schema grants	|Grants USE CATALOG on cdr_gold and USE SCHEMA on analytics_mimic_iv to each group|
|View grants	|Grants SELECT on each of the three governed views to each group|
|Post-check	|Runs SHOW GRANTS on catalogs, schemas, and views to confirm|

Users only receive access to the governed consumption views. Underlying fact, dimension, and bridge tables are not granted directly.

**Check this according to actual governance -> ** Row-level filtering and column masking are enforced inside the view SQL using is_account_group_member(). This is simpler than Unity Catalog row filters and masking policies but couples security logic to the view code.

**For a new dataset:** update the group list and view list at the top of the notebook. The grant logic does not change.

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
|Row-level security	|Inline in view SQL	|Couples security to view code but avoids Unity Catalog setup complexity|
|Column masking	|Inline CASE statement	|Same trade-off|
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

---
## 6. AI/BI Genie

**Purpose:** Provide a natural-language interface on top of the Gold governed views so that researchers, hospital operations staff, and administrators can query clinical data without writing SQL.

**Deployment notebook:** `deployment/02_deploy_genie_agent`

**Config:** `configs/genie/*.json` (six files)

**Agent title:** Clinical Data Agent

**Data sources:** `admission_journey`, `icu_clinical_monitoring`, `hospital_operational_activity`

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

**Join specifications.** `joins.json` declares the one supported join between Gold views. For MIMIC-IV, `icu_clinical_monitoring` joins to `admission_journey` on `hadm_id` as a many-to-one relationship. The join also includes an instruction that warns the agent to aggregate ICU data to the admission grain before joining, so admission-level measures are not overweighted by admissions with longer ICU stays.

**Metric rules.** `instructions.json` defines what each metric means and how it should be calculated. This includes:

- Hospital LOS(Length of Stay) uses `hospital_los_days`
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

This matters because Genie responses go to non-technical users who may interpret them as clinical findings. The phrasing rules keep responses descriptive, not diagnostic.

### 6.5 Benchmark Set (Double check this)

The accelerator ships with ten benchmark questions that test agent accuracy. Each benchmark pairs a question with the expected SQL. This allows the agent to be scored against a fixed set.

Benchmark questions cover:

| Domain | Question Type |
|--------|---------------|
| Admission | Average LOS by age group |
| Admission | Mortality rate by clinical service |
| ICU | Average lab results per ICU stay-day by care unit |
| ICU | Proportion of days with large fluid imbalance by care unit |
| Operational | Average daily arrivals and departures by care unit |
| Operational | Weekday versus weekend high-activity rates |
| Cross-view | Abnormal lab activity and hospital LOS |
| Cross-view | Admissions and patient movement by year |
| Cross-view | ICU lab activity and hospital movement by date |
| Cross-view | Admissions, ICU stay-days, and high-activity share by year |

The cross-view benchmarks are the most valuable. They test whether the agent can aggregate correctly before joining, which is the hardest part of the semantic layer.

### 6.6 Accuracy Evaluation

Agent accuracy is measured by running each benchmark question through the deployed Genie agent and comparing the returned SQL to the expected SQL.

Three scoring approaches are possible:

| Method | Definition | Effort |
|--------|------------|--------|
| Exact SQL match | Agent SQL is identical to expected SQL | Trivial to automate, too strict |
| Result set match | Agent result set is identical to expected result set | Requires running both queries, most accurate |
| Human judgement | A reviewer rates the response as correct or incorrect | Subjective but flexible |

**Recommended:** result set match. It allows different SQL that produces the same answer, which reflects how a human would judge correctness.

The accuracy metric is:
Accuracy = (benchmarks answered with matching result set) / (total benchmarks)

For MIMIC-IV, the t**arget is to answer at least eight of ten benchmarks correctly**, giving an accuracy of 80 percent or higher. The four cross-view benchmarks are the most likely to fail if the semantic layer is not working correctly.

#### 6.6.1 How to Run the Evaluation

The evaluation runs in five steps.

**Step 1: Confirm preconditions.**

Before running the evaluation, confirm that:

- The Gold views have been built and are queryable
- Metadata has been applied via `01_apply_gold_metadata`
- Governance grants have been applied via `03_apply_gold_governance`
- The Genie agent has been deployed via `02_deploy_genie_agent`

**Step 2: Open the Genie agent.**

Open the deployed Clinical Data Agent in the Databricks workspace. If the agent is embedded in the Streamlit app, open it there to test the user-facing experience.

**Step 3: Run each benchmark question.**

For each of the ten benchmark questions:

1. Submit the question through the Genie UI exactly as written in `benchmarks.json`
2. Capture the SQL that Genie returns
3. Run the returned SQL
4. Compare the result set against the expected result set from the benchmark

**Step 4: Score each benchmark.**

Score each benchmark as one of:

| Score | Meaning |
|-------|---------|
| Correct | Result set matches the expected result set |
| Partially correct | Query runs without error but returns an incorrect result set or incorrect aggregation |
| Incorrect | Query fails, or Genie refuses to answer, or the SQL is not relevant |
| Blocked | Query requires access the user does not have, and Genie correctly explains the restriction |

The Blocked score exists because governance rules intentionally restrict some views for some roles. If a benchmark is run under a role that does not have access to a view, and the agent correctly explains the restriction, that is a pass for governance behaviour even though no result is produced.

**Step 5: Report results.**

Report the results in the final report with:

- The accuracy figure (correct benchmarks divided by total benchmarks)
- A table showing each benchmark, its score, and a one-line note on any failure
- A list of failure modes observed (for example, agent aggregated at the wrong grain, agent joined without aggregation, agent chose the wrong view)
- Any changes made to the semantic layer in response to failures

(TO BE UPDATED : The report should state the accuracy figure for MIMIC-IV, list any benchmarks that failed, and describe the failure mode for each.)

#### 6.6.2 Reporting Format

The results table in the report should follow this shape:

| # | Question | Score | Notes |
|---|----------|-------|-------|
| 1 | Average LOS by age group | Correct | |
| 2 | Mortality rate by service | Correct | |
| 3 | Lab results per ICU stay-day | Correct | |
| 4 | Large fluid imbalance by care unit | Correct | |
| 5 | Daily arrivals and departures | Correct | |
| 6 | Weekday versus weekend activity | Correct | |
| 7 | Abnormal labs and hospital LOS | [score] | [note on any failure] |
| 8 | Admissions and movement by year | [score] | [note on any failure] |
| 9 | ICU lab activity and hospital movement | [score] | [note on any failure] |
| 10 | Admissions, ICU stay-days, activity by year | [score] | [note on any failure] |

If a benchmark fails, the notes column should record the specific failure mode. For example: "Agent joined ICU stay-days directly to admission rows without aggregating, causing admission measures to be overweighted."


### 6.7 Deployment

The deployment notebook `02_deploy_genie_agent` runs after the Gold views are built and after metadata has been applied.

Deployment flow:

1. Locate the repository root and import the deployment modules
2. Build the Genie configuration by reading the six config files
3. Export a readable preview of the built configuration
4. Run a dry run of the deployment
5. Check whether a Genie space with the target title already exists
6. Create or update the space
7. Validate the deployed agent

The notebook supports both first-time deployment and updates. If the space exists, it is updated rather than duplicated.

### 6.8 Design Decisions

| Decision | What Was Built | Note |
|----------|----------------|------|
| Config-driven agent | All six config files live in the repo | Version-controlled, reproducible |
| Table metadata source | `configs/metadata/` shared with Unity Catalog | Single source of truth for descriptions |
| Benchmark set | Ten fixed questions with expected SQL | Enables accuracy scoring |
| Accuracy metric | Result set match | Allows equivalent SQL |
| Governance behaviour | Agent explains access restrictions | Prevents misleading "no data" responses |
| Interpretation rules | Descriptive, not causal | Keeps responses appropriate for non-technical users |

### 6.9 Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| Multiple Genie agents | Duplicate `configs/genie/` per dataset and point a new deployment notebook at it |
| Domain-specific agents | Build separate agents for ICU, admissions, and operational audiences |
| (TO BE UPDATED)Additional benchmarks | Extend `benchmarks.json` with questions from published MIMIC-IV literature |
| Automated scoring | Add a scoring script that runs all benchmarks and reports accuracy |
| SQL snippet library | Populate `sql_snippets.json` with reusable filters and measures |
| Multi-language | Configure Genie instructions in additional languages |



---
## 7. Streamlit app

---

## 8. Governance

Governance is applied at Unity Catalog level, not in pipeline code.


---




## 9. Orchestration

Databricks Workflow with:

| Task | Depends On | Purpose |
|------|------------|---------|
| `bronze_ingest` | — | Ingests all source files |
| `silver_core_reference` | `bronze_ingest` | Cleans core/reference tables |
| `silver_clinical_events` | `bronze_ingest` | Cleans clinical event tables |
| `silver_orders_meds_icu` | `bronze_ingest` | Cleans orders/ICU tables |


**Job parameters:**

| Key | Purpose |
|-----|---------|
| `run_id` | Shared identifier (`{{job.start_time.iso_datetime}}`) |
| `table_filter` | Optional comma-separated list for testing |

### Design Decisions

| Decision | Alternatives | Why This Choice |
|----------|--------------|-----------------|
| Workflows over Airflow | Airflow is more flexible | Native Databricks; no external infra |
| Parallel Silver | Sequential Silver | Faster; 3 tasks fit comfortably |


### Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **Streaming** | Add continuous jobs |
| **Multiple clusters** | Use task-level cluster config |
| **External dependencies** | Add pre-flight HTTP task |
| **Notification chains** | Add webhook task on completion |

---

## 10. Known Limitations

| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Static/batch only | No real-time data | Auto Loader + streaming |
| Gold requires human design | Facts/dimensions declared per dataset | Templated Gold per domain |
| `special_transform` requires code | Some tables need custom logic | Expand declarative rules |
| Single-tenant catalog naming | One catalog per layer | Multi-tenant strategy |


---

## 11. Summary


---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | [Date] | [Author] | Initial solution design |
