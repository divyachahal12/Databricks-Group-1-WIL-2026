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

    When run inside Databricks, WorkspaceClient() uses the
    workspace's default authentication.
    """
    return WorkspaceClient()


# -------------------------------------------------------------------
# Genie API helpers
# -------------------------------------------------------------------

def get_genie_space(space_id):
    """
    Retrieve a Genie space including its serialized configuration.
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


def list_genie_spaces():
    """
    Retrieve all Genie spaces available in the current workspace.

    Handles pagination automatically.
    """
    workspace = get_workspace_client()

    spaces = []
    page_token = None

    while True:
        params = {
            "page_size": 100
        }

        if page_token:
            params["page_token"] = page_token

        response = requests.get(
            f"{workspace.config.host}/api/2.0/genie/spaces",
            headers=workspace.config.authenticate(),
            params=params,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        spaces.extend(
            result.get("spaces", [])
        )

        page_token = result.get(
            "next_page_token"
        )

        if not page_token:
            break

    return spaces


def find_genie_space_by_title(title):
    """
    Find a Genie space by exact title.

    Returns None when the space does not yet exist.
    """
    spaces = list_genie_spaces()

    matches = [
        space
        for space in spaces
        if space.get("title") == title
    ]

    if len(matches) > 1:
        raise ValueError(
            f"Multiple Genie spaces found with title '{title}'. "
            "The deployment requires a unique Genie space title."
        )

    if not matches:
        return None

    return matches[0]


def backup_genie_space(space_id):
    """
    Save the current Genie space before updating it.

    Backups are written to build/, which is excluded from Git.
    """
    current_space = get_genie_space(
        space_id
    )

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
    title,
    warehouse_id,
    description=None,
    parent_path=None,
    dry_run=True
):
    """
    Create or update the repository-managed Genie space.

    If a space with the supplied title exists, its current
    configuration is backed up and updated.

    If no matching space exists, a new Genie space is created.

    Parameters
    ----------
    title : str
        Genie space title.

    warehouse_id : str
        SQL warehouse used by the Genie space.

    description : str, optional
        Genie space description.

    parent_path : str, optional
        Workspace folder in which the Genie space is stored.

    dry_run : bool
        When True, validate the repository configuration and
        report the intended action without changing Genie.
    """

    if not title:
        raise ValueError(
            "A Genie space title is required."
        )

    if not warehouse_id:
        raise ValueError(
            "A SQL warehouse ID is required."
        )

    # Build and validate repository Genie configuration
    serialized_space = (
        build_genie_config_string()
    )

    # Look for the space in the current workspace
    existing_space = (
        find_genie_space_by_title(title)
    )

    workspace = get_workspace_client()

    # ---------------------------------------------------------------
    # Create
    # ---------------------------------------------------------------

    if existing_space is None:

        print("Genie deployment")
        print()
        print(f"Title: {title}")
        print(f"Warehouse ID: {warehouse_id}")
        print("Action: CREATE")
        print()

        if dry_run:
            print("DRY RUN ONLY")
            print(
                "Repository configuration built successfully."
            )
            print(
                "No Genie space was created."
            )

            return {
                "status": "dry_run_create",
                "action": "create",
                "title": title,
                "warehouse_id": warehouse_id
            }

        payload = {
            "title": title,
            "warehouse_id": warehouse_id,
            "serialized_space": serialized_space
        }

        if description:
            payload["description"] = description

        if parent_path:
            payload["parent_path"] = parent_path

        response = requests.post(
            f"{workspace.config.host}/api/2.0/genie/spaces",
            headers={
                **workspace.config.authenticate(),
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        created_space = response.json()

        print(
            "Genie space created successfully."
        )
        print(
            f"Space ID: "
            f"{created_space.get('space_id')}"
        )
        print(
            f"Title: "
            f"{created_space.get('title')}"
        )

        return created_space

    # ---------------------------------------------------------------
    # Update
    # ---------------------------------------------------------------

    space_id = existing_space["space_id"]

    if dry_run:
        current_space = get_genie_space(
            space_id
        )

        print("Genie deployment")
        print()
        print(f"Title: {title}")
        print(f"Space ID: {space_id}")
        print(f"Warehouse ID: {warehouse_id}")
        print("Action: UPDATE")
        print()

        print("DRY RUN ONLY")
        print(
            "Repository configuration built successfully."
        )
        print(
            "No changes were applied to the Genie space."
        )

        return {
            "status": "dry_run_update",
            "action": "update",
            "space_id": space_id,
            "title": current_space.get("title"),
            "etag": current_space.get("etag")
        }

    # Back up the existing space before changing it
    current_space, backup_file = (
        backup_genie_space(space_id)
    )

    current_etag = current_space.get(
        "etag"
    )

    print("Genie deployment")
    print()
    print(f"Title: {title}")
    print(f"Space ID: {space_id}")
    print(f"Warehouse ID: {warehouse_id}")
    print("Action: UPDATE")
    print(f"Backup: {backup_file}")
    print()

    payload = {
        "serialized_space": serialized_space,
        "title": title,
        "warehouse_id": warehouse_id
    }

    if description:
        payload["description"] = description

    if parent_path:
        payload["parent_path"] = parent_path

    # Prevent accidental overwrite of concurrent changes
    if current_etag:
        payload["etag"] = current_etag

    response = requests.patch(
        (
            f"{workspace.config.host}"
            f"/api/2.0/genie/spaces/{space_id}"
        ),
        headers={
            **workspace.config.authenticate(),
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    updated_space = response.json()

    print(
        "Genie space updated successfully."
    )
    print(
        f"Space ID: "
        f"{updated_space.get('space_id')}"
    )
    print(
        f"Title: "
        f"{updated_space.get('title')}"
    )
    print(
        f"New ETag: "
        f"{updated_space.get('etag')}"
    )

    return updated_space


# -------------------------------------------------------------------
# Validation helper
# -------------------------------------------------------------------

def validate_deployed_agent(space_id):
    """
    Retrieve the deployed Genie space and summarise the main
    repository-managed configuration counts.
    """
    space = get_genie_space(
        space_id
    )

    serialized_space = space.get(
        "serialized_space"
    )

    if not serialized_space:
        raise ValueError(
            "The Genie space did not return serialized_space."
        )

    config = json.loads(
        serialized_space
    )

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
        print(
            f"{key}: {value}"
        )

    return summary