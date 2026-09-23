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
        bronze_layer/ 
             bronze_ingest_mimic_iv
        silver_layer/ 
            01_silver_core_reference
            02_silver_clinical_events
            03_silver_orders_meds_icu
        gold_layer/ 
        utils/
            00_silver_utils
        configs/
            bronze_config.json
            silver_config.json
        mimic_iv/ 



---

## 4. Layer Specifications

### 4.1 Bronze Layer

**Purpose:** Ingest raw source files into Delta tables exactly as sourced, with full lineage metadata.

**Driver:** `bronze_layer/bronze_ingest_mimic_iv`
**Config:** `bronze_config.json` at `/Volumes/cdr_bronze/config/table_config/`

#### Behaviour

- Recursively scans the S3 landing zone for `.csv` files
- Derives table names from filenames
- Reads merge keys from `bronze_config.json`
- Falls back to SHA-256 row hash when no reliable key exists
- Supports `auto`, `historical`, `incremental` load modes
- Writes Delta tables with `_ingest_timestamp`, `_source_file`, `_run_id`
- Logs every file to an audit table

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

| Decision | Alternatives | Why This Choice |
|----------|--------------|-----------------|
| CSV over Parquet ingestion | Parquet is faster | MIMIC-IV ships as CSV; conversion adds no value at Bronze |
| Recursive S3 scan | Explicit file list in config | Handles nested folder structures (MIMIC-IV uses `hosp/`, `icu/`) |
| Row hash fallback | Reject keyless tables | No manual intervention; deterministic; idempotent |
| Delta merge over overwrite | Overwrite is simpler | Merge preserves history and supports incremental loads |
| `_row_key` in row hash | Use hash of specific columns | Full-row hash handles schema changes without config updates |
| Audit table per layer | Single audit table | Layer separation; easier to query per layer |
| Three load modes | Always overwrite | Supports both initial load and incremental updates |

#### Use Case Extensions

| Scenario | Extension |
|----------|-----------|
| **Streaming source** | Replace CSV scan with Auto Loader |
| **JSON/Parquet sources** | Add `file_format` field to config |
| **Multiple sources per table** | Add `file_pattern` glob support |
| **Historical backfill** | Use `historical` load type; overwrites cleanly |
| **Near-real-time** | Auto Loader + Delta Live Tables |

---

### 4.2 Silver Layer

**Purpose:** Clean, validate, deduplicate, and standardise Bronze tables.

**Driver notebooks:** `01_silver_core_reference`, `02_silver_clinical_events`, `03_silver_orders_meds_icu`
**Shared logic:** `utils/00_silver_utils`
**Config:** `/Volumes/cdr_silver/config/silver_config/silver_config.json`

#### Behaviour

- Reads `silver_config.json` to determine which tables each driver owns (via `silver_notebook` field)
- Applies column mappings, derived columns, deduplication, quality rules
- Routes tables to the correct driver automatically
- Supports `special_transform` for bespoke logic
- Shares `run_id` with Bronze for full lineage
- Logs every table to a Silver audit table

#### Quality Rule Actions

| Action | Effect |
|--------|--------|
| `quarantine` | Invalid rows written to quarantine table; removed from flow |
| `flag` | Flag column added; rows remain |

#### Special Transforms

Registered by table name in the driver notebook and referenced from config. Used when logic cannot be expressed as declarative rules. Example: `omr` BMI recompute (groups height/weight, drops missing values, recomputes BMI).

#### Design Decisions

| Decision | Alternatives | Why This Choice |
|----------|--------------|-----------------|
| 3 driver notebooks over 1 | 1 notebook is simpler | Parallelism: 3 drivers run concurrently after Bronze |
| 3 drivers over 30+ | 30 drivers maximises parallelism | Diminishing returns; maintenance burden |
| Config-based routing | Hardcoded lists per notebook | Config keeps routing visible without editing notebooks |
| `special_transform` slot | Force all rules into declarative format | Some clinical logic (BMI recompute, unit conversion) resists declarative expression |
| Shared run_id with Bronze | Independent run_id | Full traceability across layers |
| Quarantine vs reject | Reject rows entirely | Preserves evidence; allows post-hoc review |
| Flag vs quarantine | Force decisions upfront | Some rules are informational; not all violations are fatal |

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

**Purpose:** Build business-ready dimensional models (star schema) for analytics and AI/BI.

**Driver notebooks:** 
**Shared logic:** 
**Config:** 

#### Behaviour



#### Reference Entities

| Type | Entity | Source |
|------|--------|--------|
 
**Note:** Choice of which dimensions and facts to build is a human design decision. The framework executes the build; the config declares what to build.

#### Design Decisions

| Decision | Alternatives | Why This Choice |
|----------|--------------|-----------------|

#### Use Case Extensions

| Scenario | Extension |
|----------|-----------|


---

## 5. Governance

Governance is applied at Unity Catalog level, not in pipeline code.


---

## 6. Reusability & Onboarding

## 7. Orchestration

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

## 8. Known Limitations

| Limitation | Impact | Future Work |
|------------|--------|-------------|
| Static/batch only | No real-time data | Auto Loader + streaming |
| Gold requires human design | Facts/dimensions declared per dataset | Templated Gold per domain |
| `special_transform` requires code | Some tables need custom logic | Expand declarative rules |
| Single-tenant catalog naming | One catalog per layer | Multi-tenant strategy |


---

## 9. Summary


---

## Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | [Date] | [Author] | Initial solution design |