# Databricks notebook source
display(
    spark.sql(
        "DESCRIBE TABLE cdr_gold.analytics_mimic_iv.hospital_operational_activity"
    )
)

# COMMAND ----------

