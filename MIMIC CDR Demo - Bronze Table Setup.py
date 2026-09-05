# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Create Bronze Managed Tables from S3
catalog = "hive_metastore"
schema = "mimic_cdr_demo"
base_path = "s3://mimic-iii-demo-bucket/mimic-iv-dataset-demo-2.2-folder/"

tables = {
    "bronze_patients": base_path + "hosp/patients.csv",
    "bronze_admissions": base_path + "hosp/admissions.csv",
    "bronze_transfers": base_path + "hosp/transfers.csv",
    "bronze_services": base_path + "hosp/services.csv",
    "bronze_icustays": base_path + "icu/icustays.csv",
}

for table_name, location in tables.items():
    df = spark.read.csv(
        location,
        header=True,
        inferSchema=True,
        quote='"',
        escape='"',
        ignoreLeadingWhiteSpace=True,
        ignoreTrailingWhiteSpace=True
    )
    full_table = f"{catalog}.{schema}.{table_name}"
    df.write.mode("overwrite").saveAsTable(full_table)
    print(f"Created {table_name} ({df.count()} rows)")

# COMMAND ----------

# MAGIC %sql
# MAGIC USE CATALOG hive_metastore;
# MAGIC USE SCHEMA mimic_cdr_demo;

# COMMAND ----------

# DBTITLE 1,Show all bronze tables
# MAGIC %sql
# MAGIC SHOW TABLES IN hive_metastore.mimic_cdr_demo;

# COMMAND ----------

# DBTITLE 1,Cell 4
catalog = "hive_metastore"
schema = "mimic_cdr_demo"

# List of your bronze tables
bronze_tables = [
    "bronze_patients",
    "bronze_admissions", 
    "bronze_transfers",
    "bronze_services",
    "bronze_icustays"
]

# COMMAND ----------

for table in bronze_tables:
    df = spark.table(f"{catalog}.{schema}.{table}")
    print(f"\n{'='*50}")
    print(f"TABLE: {table}")
    print(f"{'='*50}")
    print(f"Row count: {df.count()}")
    print("\nSchema:")
    df.printSchema()
    print("\nSample rows (first 3):")
    display(df.limit(3))

# COMMAND ----------

from pyspark.sql.functions import isnan, isnull, when, sum as spark_sum, col

for table in bronze_tables:
    df = spark.table(f"{catalog}.{schema}.{table}")
    total = df.count()
    if total == 0:
        print(f"\n{table} is empty – skipping null check")
        continue
    
    print(f"\n{'='*50}")
    print(f"NULL PERCENTAGES: {table}")
    print(f"{'='*50}")
    
    # Count nulls per column
    null_counts = df.select([
        spark_sum(when((isnull(c)) | (col(c).cast('string').rlike('^\s*$')), 1).otherwise(0)).alias(c) 
        for c in df.columns
    ]).collect()[0]
    
    for col_name, null_count in null_counts.asDict().items():
        pct = (null_count / total) * 100
        # Only show columns with > 0% nulls to keep output clean
        if pct > 0:
            print(f"  {col_name}: {pct:.2f}% null")

# COMMAND ----------

# DBTITLE 1,Cell 7
# List of categorical columns to inspect per table
categorical_checks = {
    "bronze_patients": ["gender"],
    "bronze_admissions": ["admission_type", "admission_location", "discharge_location", "insurance", "language", "marital_status", "race", "hospital_expire_flag"],
    "bronze_transfers": ["eventtype", "careunit"],
    "bronze_services": ["prev_service", "curr_service"],
    "bronze_icustays": []  # no obvious categoricals, but we can check later
}

for table, cols in categorical_checks.items():
    if not cols:
        continue
    df = spark.table(f"{catalog}.{schema}.{table}")
    print(f"\n{'='*50}")
    print(f"DISTINCT VALUES: {table}")
    print(f"{'='*50}")
    for col_name in cols:
        distinct_vals = df.select(col_name).distinct().orderBy(col_name).collect()
        val_list = [str(row[0]) for row in distinct_vals]
        print(f"  {col_name}: {', '.join(val_list[:20])}" + (f" ... (and {len(val_list)-20} more)" if len(val_list) > 20 else ""))

# COMMAND ----------

from pyspark.sql.functions import min, max

date_columns = {
    "bronze_patients": ["anchor_year"],  # anchor_year is integer, but check range
    "bronze_admissions": ["admittime", "dischtime", "deathtime", "edregtime", "edouttime"],
    "bronze_transfers": ["intime", "outtime"],
    "bronze_services": ["transfertime"],
    "bronze_icustays": ["intime", "outtime"]
}

for table, cols in date_columns.items():
    df = spark.table(f"{catalog}.{schema}.{table}")
    print(f"\n{'='*50}")
    print(f"DATE RANGES: {table}")
    print(f"{'='*50}")
    for col_name in cols:
        # For anchor_year, min/max directly
        if col_name == "anchor_year":
            min_val, max_val = df.select(min(col_name), max(col_name)).collect()[0]
            print(f"  {col_name}: min = {min_val}, max = {max_val}")
        else:
            min_val, max_val = df.select(min(col_name), max(col_name)).collect()[0]
            # Check if the column has nulls – if both are null, skip
            if min_val is None and max_val is None:
                print(f"  {col_name}: all null")
            else:
                print(f"  {col_name}: min = {min_val}, max = {max_val}")

# COMMAND ----------

# DBTITLE 1,Cell 9
# Check for duplicate subject_id in patients (should be unique)
df_pat = spark.table(f"{catalog}.{schema}.bronze_patients")
dup_count = df_pat.groupBy("subject_id").count().filter("count > 1").count()
print(f"\nDuplicate subject_id in bronze_patients: {dup_count}")

# Check for duplicate hadm_id in admissions (should be unique)
df_adm = spark.table(f"{catalog}.{schema}.bronze_admissions")
dup_count = df_adm.groupBy("hadm_id").count().filter("count > 1").count()
print(f"Duplicate hadm_id in bronze_admissions: {dup_count}")

# Check for duplicate stay_id in icustays (should be unique)
df_icu = spark.table(f"{catalog}.{schema}.bronze_icustays")
dup_count = df_icu.groupBy("stay_id").count().filter("count > 1").count()
print(f"Duplicate stay_id in bronze_icustays: {dup_count}")

# COMMAND ----------

# Count patients that have admissions
df_pat = spark.table(f"{catalog}.{schema}.bronze_patients")
df_adm = spark.table(f"{catalog}.{schema}.bronze_admissions")

patients_with_admissions = df_adm.select("subject_id").distinct().count()
total_patients = df_pat.count()
patients_without_admissions = total_patients - patients_with_admissions
print(f"\nPatients without any admission record: {patients_without_admissions}")

# Count admissions without a patient record
admissions_without_patient = df_adm.join(df_pat, "subject_id", "left_anti").count()
print(f"Admissions without a matching patient record: {admissions_without_patient}")

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_patients
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     gender,
# MAGIC     anchor_age,
# MAGIC     anchor_year,
# MAGIC     anchor_year_group,
# MAGIC     dod,
# MAGIC     anchor_age AS age_at_anchor
# MAGIC FROM bronze_patients
# MAGIC WHERE subject_id IS NOT NULL
# MAGIC   AND gender IN ('M', 'F');

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_admissions
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     hadm_id,
# MAGIC     admittime,
# MAGIC     dischtime,
# MAGIC     deathtime,
# MAGIC     admission_type,
# MAGIC     admit_provider_id,                      -- new column, keep
# MAGIC     admission_location,
# MAGIC     -- Standardise discharge_location: null -> 'UNKNOWN'
# MAGIC     COALESCE(discharge_location, 'UNKNOWN') AS discharge_location,
# MAGIC     insurance,
# MAGIC     -- Standardise language: '?' -> 'UNKNOWN'
# MAGIC     CASE WHEN language = '?' THEN 'UNKNOWN' ELSE COALESCE(language, 'UNKNOWN') END AS language,
# MAGIC     -- marital_status: 'None' -> 'UNKNOWN'
# MAGIC     CASE WHEN marital_status = 'None' THEN 'UNKNOWN' ELSE COALESCE(marital_status, 'UNKNOWN') END AS marital_status,
# MAGIC     -- race (was ethnicity in my earlier assumption)
# MAGIC     race,
# MAGIC     edregtime,
# MAGIC     edouttime,
# MAGIC     hospital_expire_flag,
# MAGIC     -- Derived: length of stay in days
# MAGIC     DATEDIFF(dischtime, admittime) AS los_hospital_days,
# MAGIC     -- Derived: year/month for partitioning
# MAGIC     YEAR(admittime) AS adm_year,
# MAGIC     MONTH(admittime) AS adm_month,
# MAGIC     -- Derived: ED LOS (minutes) – only if both times exist
# MAGIC     CASE 
# MAGIC         WHEN edregtime IS NOT NULL AND edouttime IS NOT NULL 
# MAGIC         THEN DATEDIFF(edouttime, edregtime) 
# MAGIC         ELSE NULL 
# MAGIC     END AS ed_los_minutes
# MAGIC FROM bronze_admissions
# MAGIC WHERE subject_id IS NOT NULL 
# MAGIC   AND hadm_id IS NOT NULL
# MAGIC   AND admittime IS NOT NULL
# MAGIC   AND admittime >= '2000-01-01'   -- filter obviously invalid shifted dates (all are in 21xx)
# MAGIC   AND admittime <= '2300-01-01';  -- MIMIC-IV shifted dates go up to ~2200

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_transfers
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     hadm_id,
# MAGIC     transfer_id,                         -- new primary key
# MAGIC     eventtype,
# MAGIC     careunit,                            -- single unit column
# MAGIC     intime,
# MAGIC     outtime,
# MAGIC     -- Derived: LOS in hours (using intime/outtime)
# MAGIC     CASE 
# MAGIC         WHEN intime IS NOT NULL AND outtime IS NOT NULL 
# MAGIC         THEN DATEDIFF(outtime, intime) / 60.0   -- since DATEDIFF gives minutes? Actually DATEDIFF on timestamps returns days in Spark SQL? Wait – in Spark SQL, DATEDIFF returns days. We need to use (unix_timestamp(outtime) - unix_timestamp(intime))/3600 for hours.
# MAGIC         ELSE NULL 
# MAGIC     END AS los_hours,
# MAGIC     -- Also compute in days
# MAGIC     CASE 
# MAGIC         WHEN intime IS NOT NULL AND outtime IS NOT NULL 
# MAGIC         THEN DATEDIFF(outtime, intime)   -- this returns days (Spark SQL)
# MAGIC         ELSE NULL 
# MAGIC     END AS los_days
# MAGIC FROM bronze_transfers
# MAGIC WHERE subject_id IS NOT NULL
# MAGIC   AND hadm_id IS NOT NULL
# MAGIC   AND eventtype IN ('admit', 'transfer', 'discharge', 'ED')
# MAGIC   AND intime IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_transfers
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     hadm_id,
# MAGIC     transfer_id,
# MAGIC     eventtype,
# MAGIC     careunit,
# MAGIC     intime,
# MAGIC     outtime,
# MAGIC     -- LOS in hours (using unix timestamps)
# MAGIC     CASE 
# MAGIC         WHEN intime IS NOT NULL AND outtime IS NOT NULL 
# MAGIC         THEN (UNIX_TIMESTAMP(outtime) - UNIX_TIMESTAMP(intime)) / 3600.0
# MAGIC         ELSE NULL 
# MAGIC     END AS los_hours,
# MAGIC     -- LOS in days
# MAGIC     CASE 
# MAGIC         WHEN intime IS NOT NULL AND outtime IS NOT NULL 
# MAGIC         THEN DATEDIFF(outtime, intime)
# MAGIC         ELSE NULL 
# MAGIC     END AS los_days
# MAGIC FROM bronze_transfers
# MAGIC WHERE subject_id IS NOT NULL
# MAGIC   AND hadm_id IS NOT NULL
# MAGIC   AND eventtype IN ('admit', 'transfer', 'discharge', 'ED')
# MAGIC   AND intime IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_services
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     hadm_id,
# MAGIC     transfertime,
# MAGIC     prev_service,
# MAGIC     curr_service,
# MAGIC     -- Next service time within the same admission
# MAGIC     LEAD(transfertime) OVER (PARTITION BY hadm_id ORDER BY transfertime) AS next_transfertime,
# MAGIC     -- Duration in hours under the current service
# MAGIC     CASE 
# MAGIC         WHEN LEAD(transfertime) OVER (PARTITION BY hadm_id ORDER BY transfertime) IS NOT NULL
# MAGIC         THEN (UNIX_TIMESTAMP(LEAD(transfertime) OVER (PARTITION BY hadm_id ORDER BY transfertime)) - UNIX_TIMESTAMP(transfertime)) / 3600.0
# MAGIC         ELSE NULL 
# MAGIC     END AS service_duration_hours
# MAGIC FROM bronze_services
# MAGIC WHERE subject_id IS NOT NULL
# MAGIC   AND hadm_id IS NOT NULL
# MAGIC   AND curr_service IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE silver_icustays
# MAGIC USING DELTA
# MAGIC AS
# MAGIC SELECT 
# MAGIC     subject_id,
# MAGIC     hadm_id,
# MAGIC     stay_id,                             -- PK in MIMIC-IV
# MAGIC     first_careunit,
# MAGIC     last_careunit,
# MAGIC     intime,
# MAGIC     outtime,
# MAGIC     -- Original LOS from table (double) – keep as-is
# MAGIC     los AS los_icu_days_original,
# MAGIC     -- Recompute LOS from timestamps for validation
# MAGIC     CASE 
# MAGIC         WHEN intime IS NOT NULL AND outtime IS NOT NULL 
# MAGIC         THEN DATEDIFF(outtime, intime)
# MAGIC         ELSE NULL 
# MAGIC     END AS los_icu_days_computed
# MAGIC FROM bronze_icustays
# MAGIC WHERE subject_id IS NOT NULL
# MAGIC   AND hadm_id IS NOT NULL
# MAGIC   AND stay_id IS NOT NULL
# MAGIC   AND intime IS NOT NULL;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'silver_patients' AS table_name, COUNT(*) FROM silver_patients
# MAGIC UNION ALL
# MAGIC SELECT 'silver_admissions', COUNT(*) FROM silver_admissions
# MAGIC UNION ALL
# MAGIC SELECT 'silver_transfers', COUNT(*) FROM silver_transfers
# MAGIC UNION ALL
# MAGIC SELECT 'silver_services', COUNT(*) FROM silver_services
# MAGIC UNION ALL
# MAGIC SELECT 'silver_icustays', COUNT(*) FROM silver_icustays;

# COMMAND ----------

# MAGIC %sql
# MAGIC OPTIMIZE silver_patients ZORDER BY (subject_id);
# MAGIC OPTIMIZE silver_admissions ZORDER BY (subject_id, hadm_id);
# MAGIC OPTIMIZE silver_transfers ZORDER BY (subject_id, hadm_id);
# MAGIC OPTIMIZE silver_services ZORDER BY (subject_id, hadm_id);
# MAGIC OPTIMIZE silver_icustays ZORDER BY (subject_id, hadm_id, stay_id);