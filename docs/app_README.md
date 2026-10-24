# Streamlit Application

## 1. Overview

This document describes how to create and deploy a Streamlit application using Databricks Apps. It covers the prerequisites, how to create the app, and the files that make up a basic app.

## 2. Steps

**Requirement:** Administrative access to the Databricks workspace.

1. **Open the App Management Portal.**
   
   Access the app management portal through Databricks Apps in your workspace.

2. **Create the app.**

   Create a new app from the portal. Keep the following in mind:

   - **The app name cannot be changed once created.** Choose a name carefully before confirming.
   - **Serverless usage policies (optional).**
     These can be configured under your workspace settings. Serverless usage policies allow budget administrators to enforce cost attribution tags on serverless compute.
   - **A basic app consists of three files:**

     | File | Purpose |
     |------|---------|
     | `app.py` | The main entry point of the app. It contains the Streamlit code for the user interface and application logic. As the app grows, this can be split into separate front-end and back-end code. |
     | `app.yaml` | The configuration file that tells Databricks how to run the app, such as the start command and any environment variables. |
     | `requirements.txt` | Lists the Python packages the app depends on, which are installed when the app is deployed. |

4. **Deploy the app.**
   When starting the app for the first time, make sure all the files are in the same folder and deploy from that folder.
