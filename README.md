# Clinical Data Repository - Solution Accelerator

## Databricks-Group-1-WIL-2026

A Databricks-based solution accelerator for building Clinical Data Repositories (CDRs) on the Medallion Architecture. The accelerator is config-driven: onboarding a new dataset means writing new configs, not new notebooks.

**Reference dataset:** MIMIC-IV v3.1
**Platform:** Databricks Data Intelligence Platform (Delta Lake, Unity Catalog, AI/BI Genie)

---

## What This Accelerator Provides

- **Config-driven ingestion** - Bronze, Silver, and Gold layers driven by JSON config files
- **Reusable utility modules** - shared logic for ingestion, cleaning, and aggregation
- **Audit trail** - every table processed is logged with run ID, row counts, timing, and status
- **Governance** - Unity Catalog for RBAC, column masking, and audit logging
- **Natural language access** - AI/BI Genie configured on Gold for researcher self-service

---

## Repository Structure

    cdr-accelerator/
        drivers/
            bronze_layer/ # Raw CSV ingestion into Delta
            silver_layer/ # Cleaning, dedup, standardisation
            gold_layer/ # Dimensional model for analytics
        utils/ # Shared utility notebooks per layer
        configs/
        mimic_iv/ # Reference dataset configs


---

## Setup

1. **Unity Catalog objects** - create catalogs, schemas, and volumes (see Step 2 below)
2. **Import notebooks** - place them in the folder structure shown above
3. **Upload configs** - to `/Volumes/<catalog>/config/<layer>/`
4. **Configure the workflow** - create a Databricks Job with the tasks described in the Operations Guide
5. **Run** - start with a small `table_filter` (e.g., `patients,admissions`)

Full setup instructions: `docs/Operations_guide.md`
Onboarding a new dataset: `docs/Dataset_onboarding.md`

## Pipeline Overview

The pipeline runs as a single Databricks Workflow. Each task in a run shares one `run_id`:

- The Bronze task generates the run ID, then publishes it as a Databricks task value.
- Each Silver task reads that value via `get_shared_run_id()`, which fetches it from the upstream task key `bronze_ingest`.
- If a Silver notebook is run standalone, it falls back to a fresh UUID and logs a warning that the run will not share an audit trail with Bronze.

Every table processed writes an audit row carrying the same `run_id`. This means any run can be traced across layers using a single identifier.

---

## Load Modes

The Bronze driver supports three load modes, set through the `load_type` widget:

- **auto** (default): Creates the table if it does not exist, merges into it if it does.
- **historical**: Always overwrites the target table. Used for a full reload, for example after fixing source data or changing a merge key.
- **incremental**: Merges if the table exists, creates it if not. Used when the intent is to update rather than to load for the first time.

Silver follows the same idea without the widget. On first run, the table is created with a full load. On later runs, the driver merges into it on the configured keys. Reruns do not duplicate rows.


---

## Layer Overview

### Bronze Layer

Ingests raw MIMIC-IV CSVs from S3 into Delta tables exactly as sourced, adding lineage metadata and full audit logging.

**Driver notebook:** `drivers/bronze_layer/bronze_ingest_mimic_iv`
**Config:** `/Volumes/cdr_bronze/config/table_config/bronze_config.json`

**What it does:**
- Recursively scans the S3 landing zone for `.csv` files
- Derives table names from filenames (`patients.csv` → `patients`)
- Reads merge keys from `bronze_config.json`
- Falls back to a SHA-256 row hash when no reliable key exists
- Supports three load modes: `auto`, `historical`, `incremental`
- Writes Delta tables with metadata columns (`_ingest_timestamp`, `_source_file`, `_run_id`)
- Logs every file processed to `cdr_bronze.raw_mimic_iv.ingestion_audit_log`

**Target tables:** `cdr_bronze.raw_mimic_iv.<table_name>`

### Silver Layer

Cleans, validates, deduplicates, and standardises Bronze tables into a harmonised Silver schema.

**Driver notebooks:** `drivers/silver_layer/01_silver_core_reference`, `02_silver_clinical_events`, `03_silver_orders_meds_icu`
**Shared logic:** `utils/00_silver_utils`
**Config:** `/Volumes/cdr_silver/config/silver_config/silver_config.json`

**What it does:**
- Routes tables to the correct Silver driver via the `silver_notebook` field in config
- Applies column mappings, derived columns, quality rules, and deduplication
- Supports `special_transform` for bespoke logic (e.g., `omr` BMI recompute)
- Writes cleansed tables with shared `run_id` for full lineage
- Logs every table to a Silver audit table

**Target tables:** `cdr_silver.processed_mimic_iv.<table_name>`

**First run vs later runs:**
- First run: the table is created with a full load.
- Later runs: the driver merges into the existing table on the configured merge keys.
- Reruns update existing rows and insert new ones. They never duplicate.


### Gold Layer

Builds business-ready dimensional models (star schema) for analytics and AI/BI consumption.

**Driver notebooks:** 
**Shared logic:** 
**Config:** 

**What it does:**


**Target tables:** 

---

## Framework Pattern

Every layer follows the same three-part pattern:

| Component | Role | Contains |
|-----------|------|----------|
| **Driver notebook** | Orchestration | Which tables to process, when to run |
| **Shared utils notebook** | Reusable logic | How to ingest, clean, aggregate, audit |
| **JSON config** | Declarative behaviour | What columns, keys, rules, targets apply |

This separation means new datasets require only new configs. No notebook edits.

---

## Framework Structure

| Component | Role |
|-----------|------|
| `bronze_layer/` | Ingests raw CSVs into Bronze Delta tables |
| `silver_layer/` | Cleans and harmonises Bronze into Silver |
| `gold_layer/` | Builds dimensional models for analytics |
| `utils/` | Shared functions used by driver notebooks |
| `configs/` | JSON configs that declare behaviour per dataset |

---

## Onboarding a New Dataset

To add a new clinical dataset:

1. Write `bronze_config.json` (source paths, table list, merge keys)
2. Write `silver_config.json` (column mappings, quality rules, routing)
3. Write `gold_config.json` (dimension and fact definitions)
4. Create Unity Catalog objects for the new dataset
5. Point the workflow at the new configs

**Estimated onboarding time:** 2-3 days of config work for a dataset of similar complexity to MIMIC-IV.

See `docs/DATASET_ONBOARDING.md`.

---

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/Solution_design.md` | Architecture, pattern, design decisions |
| `docs/Dataset_onboarding.md` | Step-by-step guide to add a new dataset |
| `docs/Framework_Developer-Guide.md` | How to extend the framework |
| `docs/Operations_guide.md` | Running, monitoring, troubleshooting |

---

## Common Issues

See `docs/Operations_guide.md` for the full troubleshooting list.

- **`%run` cells must contain only the magic command** - see folder structure notes
- **Run cells top-to-bottom, or use Run All** - Databricks does not auto-run cells
- **First run creates tables (`INITIAL_LOAD`); subsequent runs merge (`INCREMENTAL_MERGE`)**
- **Spark session timeout on large tables (`chartevents`, `labevents`) is normal** - click "Remove session timeout"
- **Free Edition throttling** - wait a few minutes and retry

---

## Design Decisions

Key architectural choices and the reasoning behind them:

| Decision | What Was Built | Note |
|----------|----------------|------|
| Config format | JSON | Native to Databricks widgets and Unity Catalog volumes |
| Bronze input format | CSV | Matches MIMIC-IV distribution format |
| Storage format | Delta Lake | Stores Parquet files plus a transaction log; ACID and time travel on Databricks |
| Orchestration | Databricks Workflows | Native integration, no external orchestrator |
| Keyless table handling | SHA-256 row hash fallback | Deterministic and idempotent, no manual key assignment |
| Silver driver split | Three drivers by domain | Enables parallel execution after Bronze |
| Table routing | `silver_notebook` field in config | Adding a table does not require editing a notebook |
| Cleaning rule dispatch | `FN_REGISTRY` in utils | Adding a new rule type requires one function and one config key |
| Bespoke logic | `special_transform` per driver | Some clinical logic cannot be expressed as declarative rules |
| Run ID | Shared via Databricks task values | Bronze publishes, Silver reads; full cross-layer traceability |
| Audit tables | One per layer | Self-contained, simpler retention |


---

## Use Case Extensions

The accelerator is designed for static/batch clinical data. Extensions for other scenarios:

| Use Case | What Changes | What Stays the Same |
|----------|--------------|---------------------|
| **Streaming ingestion** | Add Auto Loader or Structured Streaming to Bronze | Config pattern, Silver/Gold layers |
| **Federated multi-source** | Add source adapters to Bronze config (JDBC, API) | Driver/engine separation, audit pattern |
| **Multi-tenant deployment** | One catalog per tenant; same driver notebooks | Configs, utils, workflow structure |
| **(TBD)OMOP CDM compliance** | Map Silver to OMOP standard tables | Framework pattern unchanged |
| **(TBD)Real-time dashboards** | Add Databricks SQL warehouses on Gold | Gold layer unchanged |
| **(TBD)Federated learning** | Add Delta Sharing on Gold | Governance unchanged |


