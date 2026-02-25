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
    st.header("Batch Setup & Status")
    
    # Form matching your specific Google Sheet headers
    with st.expander("➕ Start New Batch", expanded=True):
        with st.form("batch_setup_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                b_id = st.text_input("Batch ID (e.g., B-01)")
                b_date = st.date_input("Arrival Date")
                b_count = st.number_input("Chick Count", min_value=1, step=1)
            with col_b:
                b_cost = st.number_input("Chick Cost (₹)", min_value=0.0)
                f_qty = st.number_input("Initial Feed Qty (Bags)", min_value=0.0)
                f_price = st.number_input("Initial Feed Price (₹/Bag)", min_value=0.0)
            
            if st.form_submit_button("Record Batch Details"):
                # Data must stay in this exact order to match your columns A through F
                new_row = [b_id, b_date.strftime("%d/%m/%Y"), b_count, b_cost, f_qty, f_price]
                add_row_to_sheet("Batch_Setup", new_row)
    
    st.divider()

    # --- Display Status Metrics ---
    try:
        batch_ws = sheet.worksheet("Batch_Setup")
        batch_data = batch_ws.get_all_records()
        if batch_data:
            df = pd.DataFrame(batch_data)
            latest = df.iloc[-1]
            arr_date = datetime.strptime(str(latest.get("Arrival_Date")), "%d/%m/%Y").date()
            age = (datetime.now().date() - arr_date).days
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Active Batch", latest.get("Batch_Id"))
            m2.metric("Age (Days)", age)
            total_cost = (float(latest.get("Chick_Count", 0)) * float(latest.get("Chick_Cost", 0))) + \
                         (float(latest.get("Init_Feed_Qty", 0)) * float(latest.get("Init_Feed_Price", 0)))
            m3.metric("Initial Investment", f"₹{total_cost:,.2f}")
    except:
        st.info("Record a batch to see the dashboard stats.")

with tab2:
    st.header("Log Deaths")
    with st.form("mortality_form", clear_on_submit=True):
        m_date = st.date_input("Date")
        m_batch = st.text_input("Batch ID", placeholder="Match the Batch ID used above")
        m_deaths = st.number_input("Number of Deaths", min_value=1, step=1)
        if st.form_submit_button("Save Mortality"):
            add_row_to_sheet("Mortality_Log", [m_date.strftime("%d/%m/%Y"), m_batch, m_deaths])

with tab3:
    st.header("Log Sales")
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date")
        s_batch = st.text_input("Batch ID")
        s_birds = st.number_input("Birds Sold", min_value=1, step=1)
        s_weight = st.number_input("Total Weight (kg)", min_value=0.0)
        s_price = st.number_input("Total Sale Price (₹)", min_value=0.0)
        if st.form_submit_button("Save Sale"):
            add_row_to_sheet("Sales_Log", [s_date.strftime("%d/%m/%Y"), s_batch, s_birds, s_weight, s_price])

with tab4:
    st.header("Log Feed")
    with st.form("feed_form", clear_on_submit=True):
        f_date = st.date_input("Date")
        f_type = st.selectbox("Action", ["Purchased", "Returned"])
        f_bags = st.number_input("Number of Bags", min_value=1, step=1)
        if st.form_submit_button("Save Feed Log"):
            add_row_to_sheet("Feed_Log", [f_date.strftime("%d/%m/%Y"), f_type, f_bags])

with tab5:
    st.header("Log Expenses")
    with st.form("expense_form", clear_on_submit=True):
        e_date = st.date_input("Date")
        e_amount = st.number_input("Amount (₹)", min_value=0.0)
        e_desc = st.text_input("Expense Details")
        if st.form_submit_button("Save Expense"):
            add_row_to_sheet("Expense_Log", [e_date.strftime("%d/%m/%Y"), e_amount, e_desc])
