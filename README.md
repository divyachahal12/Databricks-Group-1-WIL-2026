# Databricks-Group-1-WIL-2026

This guide explains how to set up the MIMIC-IV bronze and silver pipeline in Databricks. It covers the Unity Catalog objects, notebook folders, configuration files, and job needed to run the pipeline.

The pipeline uses the following files:

- 5 notebooks: `bronze_ingest_mimic_iv`, `00_silver_utils`, `01_silver_core_reference`, `02_silver_clinical_events`, `03_silver_orders_meds_icu`
- 2 config files: `bronze_config.json`, `silver_config.json`


## 1. Prerequisites

- Databricks workspace access with permission to create catalogs, schemas, and volumes (or ask an admin to run Step 2 for you).
- Read access to the S3 bucket the MIMIC-IV CSVs live in.
- A Git-linked Repo (or Workspace folder) to hold the notebooks.


## 2. Create the Unity Catalog objects

Run this once, in a SQL editor or a setup notebook:

```sql
-- Catalogs
CREATE CATALOG IF NOT EXISTS cdr_bronze;
CREATE CATALOG IF NOT EXISTS cdr_silver;

-- Schemas
CREATE SCHEMA IF NOT EXISTS cdr_bronze.raw_mimic_iv;
CREATE SCHEMA IF NOT EXISTS cdr_silver.processed_mimic_iv;

-- Volumes to hold the two config files
CREATE SCHEMA IF NOT EXISTS cdr_bronze.config;
CREATE VOLUME IF NOT EXISTS cdr_bronze.config.table_config;

CREATE SCHEMA IF NOT EXISTS cdr_silver.config;
CREATE VOLUME IF NOT EXISTS cdr_silver.config.silver_config;
```

`CDR` stands for Clinical Data Repository. Bronze holds raw ingested tables (`cdr_bronze.raw_mimic_iv`); silver holds cleaned, deduplicated tables (`cdr_silver.processed_mimic_iv`).


## 3. Organise the notebook folders

Use the folder structure below in your Repo or Workspace folder. The silver notebooks use relative paths to load the shared utility notebook:

```
<repo root>/
  bronze_layer/
    bronze_ingest_mimic_iv
  silver_layer/
    01_silver_core_reference
    02_silver_clinical_events
    03_silver_orders_meds_icu
  gold_layer/          (empty for now)
  utils/
    00_silver_utils
```

Import each notebook into its matching folder. Each silver notebook's first cell is `%run ../utils/00_silver_utils` — if your folder names differ from this layout, update that line to match.

Keep the `%run` command in a cell of its own. Adding comments above or below it in the same cell can prevent the utility notebook from loading.


## 4. Upload the config files

Upload the two JSON files to the Volumes created in Step 2:

| File | Upload to |
|---|---|
| `bronze_config.json` | `/Volumes/cdr_bronze/config/table_config/bronze_config.json` |
| `silver_config.json` | `/Volumes/cdr_silver/config/silver_config/silver_config.json` |

Drag-and-drop these into the Volume from the Catalog Explorer UI (Catalog → cdr_bronze → config → table_config → Upload), or use `dbutils.fs.cp` from a notebook.

These paths match the default widget values in the notebooks, so using them avoids having to update the code. `bronze_config.json` gives each table its merge key (or `null` if the table has none — see "How duplicates are handled" below). `silver_config.json` additionally defines cleaning rules and which of the three silver notebooks owns each table.


## 5. Set the S3 source path

Open `bronze_ingest_mimic_iv` and check that the `base_folder_path` widget points to the S3 folder containing your data. For example:
```
s3://mimic-iv-datasets/mimic-iv-dataset-3.1
```
Update it if your bucket/path differs.


## 6. Build the Databricks Job

**Workflows → Jobs → Create job.**

### 6a. Add the shared job parameters

At the top of the job page, open **Job parameters → Edit parameters** and add the values below. Set these at job level rather than within individual tasks:

| Key | Value |
|---|---|
| `run_id` | `{{job.start_time.iso_datetime}}` |
| `table_filter` | *(leave blank for a full run — see Step 7 for testing)* |

The `run_id` value is set when the job starts and passed to the matching widget in each task. This lets the bronze notebook and all three silver notebooks use the same identifier for the run. You can use `{{job.run_id}}` instead if you prefer a numeric job run ID to a timestamp.

### 6b. Add the four tasks

| Task key | Notebook path | Depends on |
|---|---|---|
| `bronze_ingest` | `bronze_layer/bronze_ingest_mimic_iv` | — |
| `silver_core_reference` | `silver_layer/01_silver_core_reference` | `bronze_ingest` |
| `silver_clinical_events` | `silver_layer/02_silver_clinical_events` | `bronze_ingest` |
| `silver_orders_meds_icu` | `silver_layer/03_silver_orders_meds_icu` | `bronze_ingest` |

For each: Type = Notebook, Source = Workspace, Compute = Serverless (or a job cluster if you prefer).

All three silver tasks depend on `bronze_ingest`. Once bronze finishes successfully, the silver tasks can run in parallel.


## 7. Test with a small `table_filter` first

Before running all 31 tables, set the `table_filter` job parameter to something small, e.g.:
```
patients,admissions
```
Click **Run now** and check that all four tasks finish successfully.

Check each task log for `run_id = ...`. All four tasks should show the same value. If a task shows a different value or the warning `No run_id widget value supplied`, check that its widget is named exactly `run_id` and receives the job parameter.


## 8. Run the full pipeline

After the small test succeeds, leave `table_filter` blank and click **Run now** again to process all 31 tables. The full run may take an hour or more, depending on the available compute. The largest table, `chartevents`, contains approximately 433 million rows.


## How duplicates are handled

Some MIMIC-IV tables contain duplicate rows in the source data. `bronze_config.json` marks a table's key as `null` when no reliable natural key exists (currently `chartevents` and `emar_detail`) — for those, the pipeline falls back to hashing every column in the row as a substitute key.

Before the initial load and each later merge, the pipeline checks for duplicate keys. It removes extra records with the same key and logs a warning so duplicates do not stop the table from loading. This step is separate from the silver cleaning rules: it compares the configured key rather than judging whether records look similar.


## Common issues

- **`%run` cells must contain *only* the magic command** — see the note in Step 3. If a downstream cell throws `NameError: name 'X' is not defined` for something that should have come from `00_silver_utils`, check this first.
- **Run cells top-to-bottom, or use Run All** — Databricks doesn't auto-run cells in order just because they're stacked. If you jump straight to a later cell without running the `%run` cell above it first this session, you'll get the same `NameError`.
- **First-ever run creates tables (`INITIAL_LOAD`); every run after that merges into them (`INCREMENTAL_MERGE`).** If you ever change a table's merge key structure in `silver_config.json` or `bronze_config.json` after it's already been built once, drop that specific table (`DROP TABLE IF EXISTS <catalog>.<schema>.<table>`) before rerunning, since a changed key can mean the existing table's schema no longer lines up with what the new merge condition expects.
- **A Spark session timeout warning after ~5 minutes is normal** for the largest tables (`chartevents`, `labevents`) — click "Remove session timeout" if it appears, or it'll resolve itself as long as the query is still progressing.
- **Databricks Free Edition sometimes throttles job triggering** ("Triggering new runs for organization ... is currently disabled temporarily") during high demand. This is a platform-level limit, not a pipeline issue — wait a few minutes and retry.


## File locations

| File | Location |
|---|---|
| `bronze_ingest_mimic_iv` | `bronze_layer/` |
| `00_silver_utils` | `utils/` |
| `01_silver_core_reference` | `silver_layer/` |
| `02_silver_clinical_events` | `silver_layer/` |
| `03_silver_orders_meds_icu` | `silver_layer/` |
| `bronze_config.json` | `/Volumes/cdr_bronze/config/table_config/` |
| `silver_config.json` | `/Volumes/cdr_silver/config/silver_config/` |
