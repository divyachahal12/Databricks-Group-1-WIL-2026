import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from databricks.sdk import WorkspaceClient

from build_genie_config import build_genie_config_string


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]

BUILD_DIR = REPO_ROOT / "build"


# -------------------------------------------------------------------
# Databricks client
# -------------------------------------------------------------------

def get_workspace_client():
    """
    Create an authenticated Databricks workspace client.

    When run inside a Databricks notebook, WorkspaceClient()
    uses the notebook's default Databricks authentication.
    """
    return WorkspaceClient()


# -------------------------------------------------------------------
# Genie API helpers
# -------------------------------------------------------------------

def get_genie_space(space_id):
    """
    Retrieve the current Genie space including its serialized config.
    """
    workspace = get_workspace_client()

    response = requests.get(
        f"{workspace.config.host}/api/2.0/genie/spaces/{space_id}",
        headers=workspace.config.authenticate(),
        params={
            "include_serialized_space": "true"
        },
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def backup_genie_space(space_id):
    """
    Save the current Genie configuration before deployment.

    The backup is written to build/, which is excluded from Git.
    """
    current_space = get_genie_space(space_id)

    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S")

    backup_file = (
        BUILD_DIR
        / f"genie_space_backup_{timestamp}.json"
    )

    with backup_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            current_space,
            file,
            indent=2,
            ensure_ascii=False
        )

    return current_space, backup_file


# -------------------------------------------------------------------
# Deployment
# -------------------------------------------------------------------

def deploy_genie_agent(
    space_id,
    expected_title=None,
    dry_run=True
):
    """
    Build and deploy the repository Genie configuration.

    Parameters
    ----------
    space_id : str
        Existing Databricks Genie Space ID.

    dry_run : bool
        When True, validate and preview the deployment without
        updating the Genie Agent.

        When False, PATCH the existing Genie Agent.
    """

    # Build the new config from repository JSON files
    serialized_space = build_genie_config_string()

    # Retrieve and back up the current Agent configuration
    current_space, backup_file = backup_genie_space(
        space_id
    )

    current_etag = current_space.get("etag")

    current_title = current_space.get("title")

    if expected_title and current_title != expected_title:
        raise ValueError(
            f"Genie Agent title mismatch. "
            f"Expected '{expected_title}', "
            f"but found '{current_title}'."
        )

    

    print("Current Genie Agent retrieved successfully.")
    print(f"Space ID: {space_id}")
    print(f"Title: {current_space.get('title')}")
    print(f"ETag: {current_etag}")
    print(f"Backup: {backup_file}")
    print()

    # Stop here when running in preview mode
    if dry_run:
        print("DRY RUN ONLY")
        print("No changes were applied to the Genie Agent.")
        print()
        print(
            "Repository configuration built successfully "
            "and is ready for deployment."
        )

        return {
            "status": "dry_run",
            "space_id": space_id,
            "etag": current_etag,
            "backup_file": str(backup_file)
        }

    # Databricks recommends using the current ETag so a deployment
    # cannot silently overwrite changes made since the GET request.
    payload = {
        "serialized_space": serialized_space
    }

    if current_etag:
        payload["etag"] = current_etag

    workspace = get_workspace_client()

    response = requests.patch(
        f"{workspace.config.host}/api/2.0/genie/spaces/{space_id}",
        headers={
            **workspace.config.authenticate(),
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    updated_space = response.json()

    print("Genie Agent deployed successfully.")
    print(f"Space ID: {updated_space.get('space_id')}")
    print(f"Title: {updated_space.get('title')}")
    print(f"New ETag: {updated_space.get('etag')}")

    return updated_space


# -------------------------------------------------------------------
# Validation helper
# -------------------------------------------------------------------

def validate_deployed_agent(space_id):
    """
    Retrieve the deployed Agent and summarise the main config counts.
    """
    space = get_genie_space(space_id)

    serialized = space.get(
        "serialized_space"
    )

    if not serialized:
        raise ValueError(
            "The Genie space did not return serialized_space."
        )

    config = json.loads(serialized)

    tables = (
        config
        .get("data_sources", {})
        .get("tables", [])
    )

    sample_questions = (
        config
        .get("config", {})
        .get("sample_questions", [])
    )

    instructions = config.get(
        "instructions",
        {}
    )

    sql_examples = instructions.get(
        "example_question_sqls",
        []
    )

    join_specs = instructions.get(
        "join_specs",
        []
    )

    benchmarks = (
        config
        .get("benchmarks", {})
        .get("questions", [])
    )

    summary = {
        "tables": len(tables),
        "sample_questions": len(sample_questions),
        "sql_examples": len(sql_examples),
        "join_specs": len(join_specs),
        "benchmarks": len(benchmarks)
    }

    print("Deployed Genie configuration:")
    print()

    for key, value in summary.items():
        print(f"{key}: {value}")

    return summary