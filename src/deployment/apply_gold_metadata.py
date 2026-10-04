import json
from pathlib import Path


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]

METADATA_DIR = REPO_ROOT / "config" / "metadata"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def load_json(path):
    """Load a JSON metadata file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def quote_identifier(identifier):
    """Safely quote a Databricks SQL identifier."""
    return ".".join(
        f"`{part.replace('`', '``')}`"
        for part in identifier.split(".")
    )


def quote_column(column_name):
    """Safely quote a column name."""
    return f"`{column_name.replace('`', '``')}`"


def sql_string(value):
    """Convert text into a safe SQL string literal."""
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def load_metadata_configs():
    """Load all Gold metadata JSON files."""
    metadata_files = sorted(
        METADATA_DIR.glob("*.json")
    )

    if not metadata_files:
        raise RuntimeError(
            f"No metadata files found in {METADATA_DIR}"
        )

    return [
        load_json(path)
        for path in metadata_files
    ]


# -------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------

def validate_metadata(spark, metadata):
    """
    Confirm that the configured table exists and that its
    configured columns match the deployed Gold table.
    """
    table_name = metadata["table"]

    try:
        actual_columns = set(
            spark.table(table_name).columns
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not access table: {table_name}"
        ) from exc

    configured_columns = set(
        metadata["columns"].keys()
    )

    missing_from_table = (
        configured_columns - actual_columns
    )

    missing_from_metadata = (
        actual_columns - configured_columns
    )

    if missing_from_table:
        raise ValueError(
            f"{table_name}: metadata contains columns "
            f"not found in the table: "
            f"{sorted(missing_from_table)}"
        )

    if missing_from_metadata:
        raise ValueError(
            f"{table_name}: table contains columns "
            f"without metadata: "
            f"{sorted(missing_from_metadata)}"
        )


# -------------------------------------------------------------------
# Apply metadata
# -------------------------------------------------------------------

def apply_table_metadata(
    spark,
    metadata,
    dry_run=True
):
    """Apply table and column comments from one metadata file."""
    table_name = metadata["table"]
    quoted_table = quote_identifier(table_name)

    validate_metadata(
        spark,
        metadata
    )

    commands = []

    # Table comment
    table_description = metadata["description"]

    commands.append(
        f"COMMENT ON TABLE {quoted_table} "
        f"IS {sql_string(table_description)}"
    )

    # Column comments
    for column_name, column_info in sorted(
        metadata["columns"].items()
    ):
        description = column_info["description"]

        commands.append(
            f"ALTER TABLE {quoted_table} "
            f"ALTER COLUMN {quote_column(column_name)} "
            f"COMMENT {sql_string(description)}"
        )

    print()
    print(f"Table: {table_name}")
    print(f"Columns: {len(metadata['columns'])}")

    if dry_run:
        print("DRY RUN ONLY")
        print(
            f"{len(commands)} metadata commands "
            "validated but not executed."
        )
        return

    for command in commands:
        spark.sql(command)

    print(
        f"Metadata applied successfully "
        f"({len(commands)} commands)."
    )


def apply_gold_metadata(
    spark,
    dry_run=True
):
    """
    Apply repository metadata to all configured Gold tables.
    """
    metadata_configs = load_metadata_configs()

    print(
        f"Gold metadata files found: "
        f"{len(metadata_configs)}"
    )

    for metadata in metadata_configs:
        apply_table_metadata(
            spark=spark,
            metadata=metadata,
            dry_run=dry_run
        )

    if dry_run:
        print()
        print(
            "DRY RUN COMPLETE - "
            "no Unity Catalog metadata was changed."
        )
    else:
        print()
        print(
            "Gold Unity Catalog metadata "
            "applied successfully."
        )