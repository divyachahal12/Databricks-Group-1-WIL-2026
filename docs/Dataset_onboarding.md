# Dataset Onboarding Guide

This guide explains how to onboard a new clinical dataset into the CDR accelerator. It is intended for data engineers and solution architects.

## Prerequisites

- Access to the Databricks workspace.
- The raw data files (CSV format) uploaded to an S3 bucket or Unity Catalog Volume.
- An understanding of the source data schema (column names and data types).

## Step 1: Bronze Layer Setup (Config Only)

1. Create a new folder for your dataset under `configs/` (e.g., `configs/my_new_dataset/`).
2. Create a `bronze_config.json` file.
3. Map every table you want to ingest. If the table has a primary key, list the columns. If not, use `null` (the engine will use a SHA-256 row hash instead).

**Example:**
```json
{
  "patients": ["subject_id"],
  "lab_results": ["lab_id"],
  "unstructured_notes": null
}
```
4. Upload this JSON file to the Unity Catalog volume (`/Volumes/cdr_bronze/config/table_config/`).

## Step 2: Silver Layer Setup (Config Only)

1. Create a `silver_config.json` file in your dataset config folder.
2. For each table, define the target table name, merge keys, and cleaning rules.
3. Assign the table to one of the three Silver drivers (`core_reference`, `clinical_events`, or `orders_meds_icu`).

**Example:**

```json
{
  "patients": {
    "silver_notebook": "core_reference",
    "target_table": "patients",
    "merge_keys": ["subject_id"],
    "needs_surrogate_key": false,
    "cleaning_rules": [
      {
        "fn": "fill_missing",
        "args": { "column": "gender", "value": "Unknown" }
      }
    ]
  }
}
```

4. Upload this JSON file to the Silver config volume (`/Volumes/cdr_silver/config/silver_config/`).

## Step 3: Gold Layer Setup (Code Required)

Because Gold modeling is specific to business questions, you cannot just write a config file. You must build the notebooks.

1. Copy the existing drivers/gold_layer/ structure.
2. Adapt 01_build_dimensions to map your new dataset's dimensions (e.g., dim_patient).
3. Adapt the fact notebooks to aggregate your specific clinical measures.
4. Adapt 05_build_consumption_views to create your wide analytical views, ensuring you add the is_account_group_member() logic for governance.

## Step 4: Metadata & Genie Configuration

1. Write new metadata JSON files under configs/metadata/ for your new Gold views.
2. Write new Genie JSON files under configs/genie/ (instructions, sample questions, etc.).
3. Update the deployment notebooks to point to the new dataset name.

## Step 5: Execution

1. Run the Bronze workflow using your new bronze_config.json.
2. Run the Silver workflow.
3. Run the Gold workflow.
4. Run the deployment sequence: **Metadata** → **Governance** → **Genie**.
