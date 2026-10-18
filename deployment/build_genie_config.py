import json
import re
from pathlib import Path


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]

GENIE_CONFIG_DIR = REPO_ROOT / "configs" / "genie"
METADATA_DIR = REPO_ROOT / "configs" / "metadata"

BUILD_DIR = REPO_ROOT / "build"
OUTPUT_FILE = BUILD_DIR / "serialized_space.json"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def load_json(path):
    """Load a JSON configuration file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def combine_text(parts):
    """Combine multiple text fragments into one clean string."""
    return " ".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )

def validate_id(value, location):
    """Validate Databricks Genie object IDs."""
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"Invalid ID at {location}: {value}. "
            "IDs must be 32-character lowercase hexadecimal strings."
        )


def validate_unique_ids(items, location):
    """Check IDs within a collection for format and uniqueness."""
    ids = []

    for item in items:
        item_id = item.get("id")
        validate_id(item_id, location)
        ids.append(item_id)

    if len(ids) != len(set(ids)):
        raise ValueError(
            f"Duplicate IDs found in {location}."
        )


def build_table_config(metadata):
    """
    Convert reusable Gold metadata into Genie table configuration.
    """
    identifier = metadata["table"]

    description_parts = [
        metadata["description"],
        f"Grain: {metadata['grain']}"
    ]

    primary_key = metadata.get(
        "primary_key",
        []
    )

    if primary_key:
        description_parts.append(
            f"Primary key / unique grain columns: "
            f"{', '.join(primary_key)}."
        )

    column_configs = []

    for column_name, column_info in metadata["columns"].items():
        column_configs.append(
            {
                "column_name": column_name,
                "description": [
                    column_info["description"]
                ]
            }
        )

    column_configs.sort(
        key=lambda item: item["column_name"]
    )

    return {
        "identifier": identifier,
        "description": [
            combine_text(description_parts)
        ],
        "column_configs": column_configs
    }

# -------------------------------------------------------------------
# Load source configuration
# -------------------------------------------------------------------

instructions = load_json(
    GENIE_CONFIG_DIR / "instructions.json"
)

sample_questions = load_json(
    GENIE_CONFIG_DIR / "sample_questions.json"
)

sql_examples = load_json(
    GENIE_CONFIG_DIR / "sql_examples.json"
)

joins = load_json(
    GENIE_CONFIG_DIR / "joins.json"
)

benchmarks = load_json(
    GENIE_CONFIG_DIR / "benchmarks.json"
)

sql_snippets_config = load_json(
    GENIE_CONFIG_DIR / "sql_snippets.json"
)


metadata_files = [
    METADATA_DIR / "admission_journey.json",
    METADATA_DIR / "icu_clinical_monitoring.json",
    METADATA_DIR / "hospital_operational_activity.json"
]

metadata_configs = [
    load_json(path)
    for path in metadata_files
]


# -------------------------------------------------------------------
# Build Genie table configurations
# -------------------------------------------------------------------

tables = [
    build_table_config(metadata)
    for metadata in metadata_configs
]

tables.sort(
    key=lambda item: item["identifier"]
)


# -------------------------------------------------------------------
# Sort Genie collections
# -------------------------------------------------------------------

text_instructions = sorted(
    instructions["text_instructions"],
    key=lambda item: item["id"]
)

sample_question_list = sorted(
    sample_questions["sample_questions"],
    key=lambda item: item["id"]
)

example_question_sqls = sorted(
    sql_examples["example_question_sqls"],
    key=lambda item: item["id"]
)

join_specs = sorted(
    joins["join_specs"],
    key=lambda item: item["id"]
)

benchmark_questions = sorted(
    benchmarks["questions"],
    key=lambda item: item["id"]
)


# -------------------------------------------------------------------
# Normalise multi-part text
# -------------------------------------------------------------------

for example in example_question_sqls:
    if "usage_guidance" in example:
        example["usage_guidance"] = [
            combine_text(
                example["usage_guidance"]
            )
        ]


for join_spec in join_specs:
    if "comment" in join_spec:
        join_spec["comment"] = [
            combine_text(
                join_spec["comment"]
            )
        ]

    if "instruction" in join_spec:
        join_spec["instruction"] = [
            combine_text(
                join_spec["instruction"]
            )
        ]


# -------------------------------------------------------------------
# SQL snippets
# -------------------------------------------------------------------

sql_snippets = sql_snippets_config[
    "sql_snippets"
]

sql_snippets["filters"] = sorted(
    sql_snippets.get("filters", []),
    key=lambda item: item["id"]
)

sql_snippets["expressions"] = sorted(
    sql_snippets.get("expressions", []),
    key=lambda item: item["id"]
)

sql_snippets["measures"] = sorted(
    sql_snippets.get("measures", []),
    key=lambda item: item["id"]
)


# -------------------------------------------------------------------
# Validate IDs
# -------------------------------------------------------------------

validate_unique_ids(
    sample_question_list,
    "sample_questions"
)

validate_unique_ids(
    benchmark_questions,
    "benchmarks"
)

validate_unique_ids(
    text_instructions,
    "text_instructions"
)

validate_unique_ids(
    example_question_sqls,
    "example_question_sqls"
)

validate_unique_ids(
    join_specs,
    "join_specs"
)

validate_unique_ids(
    sql_snippets["filters"],
    "sql_snippets.filters"
)

validate_unique_ids(
    sql_snippets["expressions"],
    "sql_snippets.expressions"
)

validate_unique_ids(
    sql_snippets["measures"],
    "sql_snippets.measures"
)


# Sample questions and benchmarks share a question ID namespace
question_ids = (
    [item["id"] for item in sample_question_list]
    + [item["id"] for item in benchmark_questions]
)

if len(question_ids) != len(set(question_ids)):
    raise ValueError(
        "Duplicate IDs found across sample questions and benchmarks."
    )


# Instruction objects share an instruction ID namespace
instruction_ids = (
    [item["id"] for item in text_instructions]
    + [item["id"] for item in example_question_sqls]
    + [item["id"] for item in join_specs]
    + [item["id"] for item in sql_snippets["filters"]]
    + [item["id"] for item in sql_snippets["expressions"]]
    + [item["id"] for item in sql_snippets["measures"]]
)

if len(instruction_ids) != len(set(instruction_ids)):
    raise ValueError(
        "Duplicate IDs found across Genie instruction objects."
    )


# -------------------------------------------------------------------
# Build complete serialized_space configuration
# -------------------------------------------------------------------

serialized_space = {
    "version": 2,

    "config": {
        "sample_questions": sample_question_list
    },

    "data_sources": {
        "tables": tables
    },

    "instructions": {
        "text_instructions": text_instructions,
        "example_question_sqls": example_question_sqls,
        "join_specs": join_specs,
        "sql_snippets": sql_snippets
    },

    "benchmarks": {
        "questions": benchmark_questions
    }
}


# -------------------------------------------------------------------
# Export helpers
# -------------------------------------------------------------------

def build_genie_config():
    """Return the complete Genie serialized_space dictionary."""
    return serialized_space


def build_genie_config_string():
    """
    Return serialized_space as the JSON string required by
    the Databricks Genie Management API.
    """
    return json.dumps(
        serialized_space,
        ensure_ascii=False,
        separators=(",", ":")
    )


def export_genie_config():
    """Write a readable generated config for inspection/testing."""
    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            serialized_space,
            file,
            indent=2,
            ensure_ascii=False
        )

    return OUTPUT_FILE


# -------------------------------------------------------------------
# Local validation / preview
# -------------------------------------------------------------------

if __name__ == "__main__":

    output_path = export_genie_config()

    print("Genie configuration built successfully.")
    print()
    print(f"Tables: {len(tables)}")
    print(f"Sample questions: {len(sample_question_list)}")
    print(f"SQL examples: {len(example_question_sqls)}")
    print(f"Join specs: {len(join_specs)}")
    print(f"SQL filters: {len(sql_snippets['filters'])}")
    print(f"SQL expressions: {len(sql_snippets['expressions'])}")
    print(f"SQL measures: {len(sql_snippets['measures'])}")
    print(f"Benchmarks: {len(benchmark_questions)}")
    print()
    print(f"Generated config: {output_path}")