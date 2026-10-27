# Operations Guide

This guide covers the day-to-day operations of the CDR accelerator, including running the pipeline, monitoring health, and troubleshooting.

## 1. Running the Pipeline

The pipeline is orchestrated via **Databricks Jobs & Pipelines**. 

Because the pipeline is split into distinct phases, you will find three separate Jobs in the UI:
1. **Running both Bronze and Silver Layer MIMIC-IV Dataset** (Handles ingestion and cleaning)
2. **Gold Layer Build** (Builds dimensions, facts, and views)
3. **Gold Genie Deployment** (Applies metadata, governance, and deploys the Genie agent)

### Standard Full Run
To run a complete end-to-end pipeline:
1. Go to **Jobs & Pipelines** in the Databricks UI.
2. Click on the **Running both Bronze and Silver Layer MIMIC-IV Dataset** job.
3. Click **Run now**. (Leave the `table_filter` parameter blank to run all tables).
4. Once this succeeds, open the **Gold Layer Build** job and click **Run now**.
5. Once the Gold build succeeds, open the **Gold Genie Deployment** job and click **Run now**.

### Test Run (Single Table)
To run the Bronze/Silver pipeline for a specific table (e.g., during debugging):
1. Open the **Running both Bronze and Silver...** job.
2. Click **Run now**.
3. Under parameters, set `table_filter` to `patients` (or a comma-separated list like `patients,admissions`).
4. Click **Run**.

## 2. Monitoring & Audit Tables

Every layer logs its execution to a dedicated Delta audit table. You can query these to monitor health.

| Layer | Audit Table Name | Key Columns to Check |
|-------|------------------|----------------------|
| Bronze | `cdr_bronze.raw_mimic_iv.ingestion_audit_log` | `status`, `row_count`, `error_message` |
| Silver | `cdr_silver.processed_mimic_iv.silver_audit_log` | `status`, `rows_inserted`, `rows_updated` |

### Checking for Failed Runs
Run this SQL to find any failed tables in the last 24 hours:

```sql
SELECT run_id, target_table, error_message, start_time
FROM cdr_bronze.raw_mimic_iv.ingestion_audit_log
WHERE status = 'FAILED' 
  AND start_time >= CURRENT_DATE() - INTERVAL 1 DAY;
  ```

  ### 3. Deployment Sequence

If you make changes to the Gold layer, you must follow this exact deployment order to ensure security and metadata are not lost:

1. **Gold Layer Build Job:** Recreates the views (this drops and recreates them, wiping out previous grants).
2. **`deployment/01_apply_gold_metadata`:** Applies Unity Catalog descriptions. (Usually triggered as part of the Gold Genie Deployment Job).
3. **`deployment/02_apply_gold_governance`:** Restores grants to the new views. (Usually triggered as part of the Gold Genie Deployment Job).
4. **`deployment/03_deploy_genie_agent`:** Updates the Genie semantic layer. (Usually triggered as part of the Gold Genie Deployment Job).

> **Warning:** If you do not run the Governance deployment (Step 3) after a Gold rebuild, users will lose access to the dashboards and Genie because the views will have been recreated without the necessary `GRANT SELECT` statements.

### 4. Troubleshooting Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| **Bronze ingestion fails on a specific file** | File encoding issue or delimiter mismatch. | Check the `error_message` in the audit log. Verify the CSV format in S3. |
| **Silver table fails to merge** | The merge key in `silver_config.json` is not unique in the source data. | The pipeline automatically falls back to a row hash, but logs a warning. Check the data for duplicates. |
| **Users get "Access Denied" on Gold views** | Governance grants were not reapplied after a Gold rebuild. | Run the **Gold Genie Deployment** job to restore grants. |
| **Genie gives "Table not found" errors** | The Genie deployment was not run after a metadata change. | Run the **Gold Genie Deployment** job to update the semantic layer. |
| **A specific task fails inside a Job** | A bug in the notebook or a missing dependency. | Open the Job run, click on the specific failed **Task** (Notebook), and review the error traceback in the output. |
