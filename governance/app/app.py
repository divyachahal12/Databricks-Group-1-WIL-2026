import html
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

GENIE_ID = "01f1d2631b231c36a2aee078674dfe33"

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

USER_GROUP_DISPLAY_NAMES = {
    "healthcare_admins": "Healthcare Admin",
    "healthcare_hospital_operations": "Healthcare Hospital Operations",
    "healthcare_researchers": "Healthcare Researchers",
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
        .block-container, [data-testid="stMainBlockContainer"] {
            padding-top: 3rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        .main-header {
            text-align: center;
            padding: 0 0 .75rem 0;
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
        /* --- Tab Nav Bar Styling --- */
        [data-testid="stTabs"] [role="tab"] {
            background-color: #FFFFFF;
            color: #333333;
            border: 1px solid #e0e0e0;
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 1.25rem;
            margin-right: 0.25rem;
            transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
        }
        [data-testid="stTabs"] [role="tab"]:hover {
            background-color: #FF9901;
            color: #FFFFFF;
            border-color: #FF9901;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background-color: #FF0061;
            color: #FFFFFF;
            border-color: #FF0061;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"]:hover {
            background-color: #FF9901;
            color: #FFFFFF;
            border-color: #FF9901;
        }
        /* --- Profile Button Styling --- */
        .profile-wrapper {
            display: flex;
            justify-content: flex-end;
            margin-bottom: .5rem;
        }
        .profile-container {
            position: relative;
            display: inline-block;
        }
        .profile-button {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #FF0061;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 1.1rem;
            cursor: default;
            user-select: none;
            transition: background-color 0.2s ease;
        }
        .profile-container:hover .profile-button {
            background-color: #FF9901;
        }
        .profile-tooltip {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            top: 48px;
            right: 0;
            width: max-content;
            min-width: 240px;
            max-width: calc(100vw - 4rem);
            background-color: #FFFFFF;
            color: #333333;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            padding: .75rem 1rem;
            font-size: .85rem;
            z-index: 1000;
            transition: opacity 0.2s ease;
            pointer-events: none;
        }
        .profile-container:hover .profile-tooltip {
            visibility: visible;
            opacity: 1;
        }
        .profile-tooltip .profile-label {
            color: #888888;
            font-size: .75rem;
            margin: 0;
        }
        .profile-tooltip .profile-value {
            margin: 0 0 .5rem 0;
            white-space: nowrap;
        }
        .profile-tooltip .profile-value:last-child {
            margin-bottom: 0;
        }
    </style>
    """,
    unsafe_allow_html = True
)

# --- Profile Button (hover to view email and user group) ---
profile_email = html.escape(user_email or "Unknown user")
profile_group = html.escape(
    USER_GROUP_DISPLAY_NAMES.get(selective_user_group, selective_user_group)
    if selective_user_group else "No authorised group"
)
profile_initial = html.escape((user_email or "?")[0].upper())

st.markdown(
    f'<div class="profile-wrapper"><div class="profile-container">'
    f'<div class="profile-button">{profile_initial}</div>'
    f'<div class="profile-tooltip">'
    f'<p class="profile-label">Email</p><p class="profile-value">{profile_email}</p>'
    f'<p class="profile-label">User Group</p><p class="profile-value">{profile_group}</p>'
    f'</div></div></div>',
    unsafe_allow_html = True
)

# --- Tabs for Dashboard and AI Genie ---
tab_labels = ["Genie Assistant", "Health Data Dashboard"]
if usage_dashboard_url:
    tab_labels.append("Usage Dashboard")

tabs = st.tabs(tab_labels)

with tabs[0]: # Genie Assistant
    if genie_url:
        st.markdown("#### Clinical Data Agent")
        st.write("Helpful Genie Assistant to answer your queries")
        st.components.v1.iframe(genie_url, height = 700, scrolling = True)
    else:
        st.info(
            "You do not have access to the AI Assistant."
            "Please contact your administrator to be added to an authorised group."
        )

with tabs[1]: # Health Data Dashboard
    if health_data_dashboard_url:
        st.markdown("#### Health Data Dashboard")
        st.write("Visual Dashboard for MIMIC-IV Health Data Repository")
        st.components.v1.iframe(health_data_dashboard_url, height = 700, scrolling = True)
    else:
        st.info(
            "You do not have access to the Dashboard.\n"
            "Please contact your administrator to be added to an authorised group."
        )

if usage_dashboard_url:
    with tabs[2]: # Usage Dashboard
        st.markdown("#### Usage Dashboard")
        st.write("Breakdown of current cost usage within Databricks")
        st.components.v1.iframe(usage_dashboard_url, height = 700, scrolling = True)

