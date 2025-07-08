import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import json
creds_dict = st.secrets["gcp_service_account"]
# Streamlit setup
st.set_page_config(page_title="Application Tracker", layout="wide")

# Google Sheets auth
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(json.loads(json.dumps(creds_dict)), scopes=SCOPES)
client = gspread.authorize(creds)

# Open Sheet
SHEET_URL = "https://docs.google.com/spreadsheets/d/1YCeP2ewMZvdef4-Rjl5yHjcp3ipQhamfmHwJs-2rQkQ"
sheet = client.open_by_url(SHEET_URL).worksheet("Sheet2")

@st.cache_data(ttl=60)
def load_data():
    return pd.DataFrame(sheet.get_all_records())

df = load_data()
df = df.drop_duplicates(subset="Company", keep="first")


# Convert 'Applied' to boolean
df["Applied"] = df["Applied"].astype(str).str.lower().map({"true": True, "false": False})
df["Applied"] = df["Applied"].fillna(False)

# Sidebar filters
st.sidebar.title("🔍 Filters")
search = st.sidebar.text_input("Search Company")
locations = st.sidebar.multiselect("Filter by Location", df["Location"].unique())
only_applied = st.sidebar.checkbox("Only Applied")

filtered_df = df.copy()
if search:
    filtered_df = filtered_df[filtered_df["Company"].str.contains(search, case=False)]
if locations:
    filtered_df = filtered_df[filtered_df["Location"].isin(locations)]
if only_applied:
    filtered_df = filtered_df[filtered_df["Applied"] == True]

# Tabs
tab1, tab2 = st.tabs(["📋 Tracker", "📊 Analytics"])

with tab1:
    st.title("📋 Job Application Tracker")
    updated = st.data_editor(
        filtered_df[["Company", "Location", "Applied", "Role Applied", "Email", "Response"]],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Applied": st.column_config.CheckboxColumn("Applied?"),
            "Response": st.column_config.SelectboxColumn("Response", options=["", "Ignored", "Responded", "Step 2"]),
        },
        key="tracker_table"
    )

    if st.button("🔄 Update Google Sheet"):
        df.update(updated)
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.success("✅ Sheet updated!")

with tab2:
    st.title("📊 Application Analytics")

    total = len(df)
    applied = df["Applied"].sum()
    responded = df[df["Response"].isin(["Responded", "Step 2"])].shape[0]
    ignored = df[df["Response"] == "Ignored"].shape[0]

    ratio = f"{responded}/{applied}" if applied else "0"
    ignore_rate = f"{(ignored / applied) * 100:.1f}%" if applied else "0%"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Applications", total)
    col2.metric("Applied", applied)
    col3.metric("Responses", responded)
    col4.metric("Ignore Rate", ignore_rate)

    # 📊 Response Breakdown
    response_chart = df["Response"].value_counts().reset_index()
    response_chart.columns = ["Response", "Count"]
    fig1 = px.bar(response_chart, x="Response", y="Count", color="Response", title="📬 Response Breakdown")
    st.plotly_chart(fig1, use_container_width=True)

    # 📍 Applied by Location
    applied_by_location = df[df["Applied"] == True]["Location"].value_counts().reset_index()
    applied_by_location.columns = ["Location", "Applications"]
    fig2 = px.pie(applied_by_location, names="Location", values="Applications", title="📍 Applications by Location")
    st.plotly_chart(fig2, use_container_width=True)

    # 🎯 Response by Role
    response_vs_role = df[df["Applied"] == True].groupby("Role Applied")["Response"].value_counts().unstack().fillna(0)
    fig3 = px.bar(response_vs_role, barmode="stack", title="🎯 Response by Role Applied")
    st.plotly_chart(fig3, use_container_width=True)
