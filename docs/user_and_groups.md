# User and Groups

## 1. Overview
This document describes how users and user groups are set up and maintained in Databricks. It covers where each type of object is managed (account level or workspace level) and the steps for configuring groups so that access to Unity Catalog resources can be granted consistently.

**Scope:**
1. Creating and maintaining users and user groups
2. How account-level and workspace-level configuration relate to each other

## 2. Role and Group Configuration

All user and group configuration is done in **Databricks**.

**Requirement:** Access to **Unity Catalog**, since groups are used as the principals when granting permissions on catalogs, schemas, and tables.

### Steps

1. **Create users and groups at the account level.**

   Open the Databricks Account Console and go to **User management**. From here you can create users and add them to user groups.

2. **Mirror each group at the workspace level.**
   
   For every user group created at the account level, create a group with the same name in the workspace. You do **not** need to create individual users at the workspace level.

3. **Maintain users and groups in the right place.**
   
   - **Users** are maintained at the **account level** only.
   - **User groups** must be managed at **both** the account level and the workspace level.

| Object | Account Level | Workspace Level |
|--------|:-------------:|:---------------:|
| Users  | ✅ Managed here | ❌ Not required |
| Groups | ✅ Managed here | ✅ Must mirror account groups |

> **Note:** Keep group names identical across both levels so that permissions resolve correctly.
