# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # Genie import: Gold layer agent
# MAGIC Builds or updates the Genie agent from the 7 JSON files in `config/genie_validated`.
# MAGIC
# MAGIC
# MAGIC - `MODE = "update"` overwrites the existing agent in place (same URL).
# MAGIC - `MODE = "create"` makes a brand new agent and leaves the old one alone.
# MAGIC
# MAGIC Backup of the agent before this import: `/Workspace/Users/<you>/genie_backup.json`

# COMMAND ----------

from databricks.sdk import WorkspaceClient
import json

w = WorkspaceClient()
user = spark.sql("SELECT current_user()").first()[0]

# "update" = overwrite the existing agent in place, "create" = make a brand new agent
MODE = "update"
SPACE_ID = "01f1b7cffffb1bf4b3a78f8e67af3a2a"   # Hospital Admission Analytics, only used when MODE = "update"

# Folder holding the 7 validated JSON files
CONFIG_DIR = f"/Workspace/Users/{user}/hansen/Databricks-Group-1-WIL-2026/config/genie_validated"

# COMMAND ----------

def load(name):
    with open(f"{CONFIG_DIR}/{name}") as f:
        return json.load(f)

space = {
    "version": 2,
    "config": {"sample_questions": load("sample_questions.json")["sample_questions"]},
    "data_sources": load("data_sources.json"),
    "instructions": {
        "text_instructions": load("instructions.json")["text_instructions"],
        "example_question_sqls": load("sql_examples.json")["example_question_sqls"],
        "join_specs": load("joins.json")["join_specs"],
        "sql_snippets": load("sql_snippets.json")["sql_snippets"],
    },
    "benchmarks": {"questions": load("benchmarks.json")["questions"]},
}

snips = space["instructions"]["sql_snippets"]
print("Tables:     ", [t["identifier"].split(".")[-1] for t in space["data_sources"]["tables"]])
print("Examples:   ", len(space["instructions"]["example_question_sqls"]))
print("Measures:   ", len(snips["measures"]))
print("Filters:    ", len(snips["filters"]))
print("Expressions:", len(snips["expressions"]))
print("Joins:      ", len(space["instructions"]["join_specs"]))
print("Benchmarks: ", len(space["benchmarks"]["questions"]))

# COMMAND ----------

if MODE == "update":
    w.api_client.do(
        "PATCH",
        f"/api/2.0/genie/spaces/{SPACE_ID}",
        body={"serialized_space": json.dumps(space)},
    )
    target_id = SPACE_ID
    print("Updated existing agent:", target_id)

elif MODE == "create":
    warehouse_id = next(wh.id for wh in w.warehouses.list() if "Serverless Starter" in wh.name)
    created = w.api_client.do(
        "POST",
        "/api/2.0/genie/spaces",
        body={
            "title": "Clinical Data Repository Analytics",
            "description": "Genie agent over the three MIMIC-IV Gold tables. Built from config/genie_validated JSON files.",
            "warehouse_id": warehouse_id,
            "parent_path": f"/Workspace/Users/{user}",
            "serialized_space": json.dumps(space),
        },
    )
    target_id = created.get("space_id") or created.get("id")
    print("New agent created:", target_id)

else:
    raise ValueError("MODE must be 'update' or 'create'")

# COMMAND ----------

# Read back what Genie actually stored, so the counts are confirmed rather than assumed
check = w.api_client.do(
    "GET",
    f"/api/2.0/genie/spaces/{target_id}",
    query={"include_serialized_space": "true"},
)
saved = json.loads(check["serialized_space"])
s = saved["instructions"].get("sql_snippets", {})

print("Tables:     ", [t["identifier"].split(".")[-1] for t in saved["data_sources"]["tables"]])
print("Examples:   ", len(saved["instructions"].get("example_question_sqls", [])))
print("Measures:   ", len(s.get("measures", [])))
print("Filters:    ", len(s.get("filters", [])))
print("Expressions:", len(s.get("expressions", [])))
print("Joins:      ", len(saved["instructions"].get("join_specs", [])))
print("Benchmarks: ", len(saved.get("benchmarks", {}).get("questions", [])))