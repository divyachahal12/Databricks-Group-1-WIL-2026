import streamlit as st
from databricks.sdk import WorkspaceClient

# --- Configurations ---
wc = WorkspaceClient()

st.set_page_config(
    page_title = "Hospital Data Portal",
    layout = "wide",
    initial_sidebar_state = "collapsed"
)

WORKSPACE_URL = "https://dbc-e99163ad-cc83.cloud.databricks.com"
WORKSPACE_ID = "7474648421005201"

GENIE_ID = "01f1c7a2168c12ac9ac94b6ce053c1dc"

HEALTHCARE_ADMIN_DASHBOARD_ID = "01f1c75cfc5b10f68e5248d66127d430"
HEALTHCARE_HOSPITAL_OPERATIONS_DASHBOARD_ID = "01f1c7877138187ebbec58b2f8e0d339"
HEALTHCARE_HOSPITAL_RESEARCHERS_DASHBOARD_ID = "01f1c788a2881834b33c80f742c38e85"
USAGE_DASHBOARD_ID = "01f1ae706dcb13a0aa0cc74b2bb89284"

GENIE_ID_MAPPING = {
    "healthcare_admins": {
        "health_data_dashboard": HEALTHCARE_ADMIN_DASHBOARD_ID,
        "usage_dashboard": USAGE_DASHBOARD_ID
    },
    "healthcare_hospital_operations": {
        "health_data_dashboard": HEALTHCARE_HOSPITAL_OPERATIONS_DASHBOARD_ID,
    },
    "healthcare_researchers": {
        "health_data_dashboard": HEALTHCARE_HOSPITAL_RESEARCHERS_DASHBOARD_ID,
    },
}

# --- Get User's User Group (WS Level) ---
def Get_Selective_User_Group(user_email):
    users = list(wc.users.list(
        filter = f'userName eq "{user_email}"'
    ))

    if not users:
        return None
    
    user = wc.users.get(users[0].id)
    user_groups =  [g.display for g in (user.groups or [])]
    
    for authorised_user_group in GENIE_ID_MAPPING.keys():
        if authorised_user_group in user_groups:
            return authorised_user_group
        
    return None

# --- Set dashboard and genie ID's ---
user_email = st.context.headers.get("X-Forwarded-Email")
selective_user_group = Get_Selective_User_Group(user_email)

if selective_user_group:
    genie_url = f"{WORKSPACE_URL}/embed/genie/rooms/{GENIE_ID}?o={WORKSPACE_ID}"

    health_data_dashboard_id = GENIE_ID_MAPPING[selective_user_group]["health_data_dashboard"]
    health_data_dashboard_url = f"{WORKSPACE_URL}/embed/dashboardsv3/{health_data_dashboard_id}?o={WORKSPACE_ID}"

    usage_dashboard_url = (
        f"{WORKSPACE_URL}/embed/dashboardsv3/{USAGE_DASHBOARD_ID}?o={WORKSPACE_ID}" 
        if selective_user_group == "healthcare_admins" else None
    )
    
else:
    genie_url = None
    health_data_dashboard_url = None
    usage_dashboard_url = None

# --- Header ---
st.markdown(
    """
    <style>
        .main-header {
            text-align: center;
            padding: .5rem 0 1rem 0;
        }
        .main-header h1 {
            margin: 0;
            font-size: 1.8rem;
        }
        .main-header p {
            margin: .2rem 0 0 0;
            color: #888888;
            font-size: .95rem;
        }
        iframe {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }
    </style>
    <div class = "main-header">
        <h1>Hospital Data Portal</h1>
        <p>Dashboard &amp; AI Assistant for Hospitalisation Data</p>
    </div>
    """,
    unsafe_allow_html = True
)

# --- Tabs for Dashboard and AI Genie ---
tab_ai_assistant, tab_heatlh_dashboard, tab_usage_dashboard  = st.tabs(["AI Assistant", "Health Data Dashboard", "Usage Dashboard"])

with tab_ai_assistant:
    if genie_url:
        st.markdown(
            """
            <div style = "background: linear-gradient(135deg, #e8f4f8, #f0e6ff);
                            border-radius:12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem;">
                <h3 style = "margin: 0 0 .3rem 0;">
                    Hi There! Welcome to the Hospital Data Assistant
                </h3>
                <p style = "margin: 0; color: #555555; font-size: .95rem;">
                    Ask me anything about patients, admissions and transfers.
                    You can try questions like:
                </p>
                <ul style = "margin: .5rem 0 0 0; color: #444444; font-size: .9rem;">
                    <li>How many patients were admitted to the hospital last year?</li>
                    <li>What is the average length of stay all types of admissions?</li>
                </ul>
            </div>
            """,
            unsafe_allow_html = True
        )
        st.components.v1.iframe(genie_url, height = 800, scrolling = True)
    else:
        st.info(
            "You do not have access to the AI Assistant."
            "Please contact your administrator to be added to an authorised group."
        )

with tab_heatlh_dashboard:
    if health_data_dashboard_url:
        st.markdown("#### Health Data Dashboard")
        st.components.v1.iframe(health_data_dashboard_url, height = 800, scrolling = True)
    else:
        st.info(
            "You do not have access to the Dashboard."
            "Please contact your administrator to be added to an authorised group."
        )

with tab_usage_dashboard:
    if usage_dashboard_url:
        st.markdown("#### Usage Dashboard")
        st.components.v1.iframe(usage_dashboard_url, height = 800, scrolling = True)
    else:
        st.info(
            "You do not have access to the Dashboard.\n"
            "Please contact your administrator to be added to an authorised group."
        )

