import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json

# --- Page Setup ---
st.set_page_config(page_title="Poultry Ledger", layout="wide")
st.title("🐔 Poultry Management Dashboard")

# --- Connect to Google Sheets ---
@st.cache_resource
def connect_to_sheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        secret_data = st.secrets["GCP_SERVICE_ACCOUNT"]
        if isinstance(secret_data, str):
            secret_data = json.loads(secret_data)
        creds = Credentials.from_service_account_info(secret_data, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open("Poultry_Data_Vault")
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        st.stop()

sheet = connect_to_sheets()

def add_row_to_sheet(worksheet_name, row_data):
    try:
        ws = sheet.worksheet(worksheet_name)
        ws.append_row(row_data)
        st.success(f"✅ Data saved to {worksheet_name}!")
    except Exception as e:
        st.error(f"❌ Error: Tab '{worksheet_name}' not found. Please create it in your Google Sheet.")

# --- Navigation ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "☠️ Mortality", "💰 Sales", "🌾 Feed", "💸 Expenses"])

with tab1:
    st.header("Batch Status")
    try:
        batch_ws = sheet.worksheet("Batch_Setup")
        batch_data = batch_ws.get_all_records()
        if batch_data:
            df = pd.DataFrame(batch_data)
            latest = df.iloc[-1]
            arrival_date = datetime.strptime(str(latest.get("Arrival_Date")), "%d/%m/%Y").date()
            age = (datetime.now().date() - arrival_date).days
            col1, col2, col3 = st.columns(3)
            col1.metric("Batch ID", latest.get("Batch_Id"))
            col2.metric("Age (Days)", age)
            col3.metric("Initial Chicks", int(latest.get("Chick_Count", 0)))
    except:
        st.info("Fill your 'Batch_Setup' sheet to see dashboard stats.")

with tab2:
    st.header("Log Deaths")
    with st.form("mortality_form", clear_on_submit=True):
        m_date = st.date_input("Date", key="m_date")
        m_batch = st.text_input("Batch ID", value="Batch-01")
        m_deaths = st.number_input("Deaths", min_value=1, step=1)
        if st.form_submit_button("Save Mortality"):
            add_row_to_sheet("Mortality_Log", [m_date.strftime("%d/%m/%Y"), m_batch, m_deaths])

with tab3:
    st.header("Log Sales")
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date", key="s_date")
        s_batch = st.text_input("Batch ID", value="Batch-01")
        s_birds = st.number_input("Birds Sold", min_value=1, step=1)
        s_weight = st.number_input("Weight (kg)", min_value=0.0)
        s_price = st.number_input("Price (₹)", min_value=0.0)
        if st.form_submit_button("Save Sale"):
            add_row_to_sheet("Sales_Log", [s_date.strftime("%d/%m/%Y"), s_batch, s_birds, s_weight, s_price])

with tab4:
    st.header("Log Feed")
    with st.form("feed_form", clear_on_submit=True):
        f_date = st.date_input("Date", key="f_date")
        f_type = st.selectbox("Type", ["Purchased", "Returned"])
        f_bags = st.number_input("Bags", min_value=1, step=1)
        if st.form_submit_button("Save Feed"):
            add_row_to_sheet("Feed_Log", [f_date.strftime("%d/%m/%Y"), f_type, f_bags])

with tab5:
    st.header("Log Expenses")
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("Date", key="e_date")
        e_amount = st.number_input("Amount (₹)", min_value=1.0)
        e_desc = st.text_input("Description")
        if st.form_submit_button("Save Expense"):
            add_row_to_sheet("Expense_Log", [e_date.strftime("%d/%m/%Y"), e_amount, e_desc])
