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

# --- Helper Functions ---
def add_row_to_sheet(worksheet_name, row_data):
    try:
        ws = sheet.worksheet(worksheet_name)
        ws.append_row(row_data)
        st.success(f"✅ Saved to {worksheet_name}!")
    except:
        st.error(f"❌ Tab '{worksheet_name}' not found!")

def get_total_from_col(worksheet_name, col_name='Cost'):
    try:
        df = pd.DataFrame(sheet.worksheet(worksheet_name).get_all_records())
        return df[col_name].sum() if not df.empty else 0
    except:
        return 0

# --- Get Active Batch ---
active_batch_id = "No Active Batch"
batch_data = []
try:
    batch_ws = sheet.worksheet("Batch_Setup")
    batch_data = batch_ws.get_all_records()
    if batch_data:
        active_batch_id = batch_data[-1].get("Batch_Id", "No Active Batch")
except:
    pass

# --- Navigation (Reordered Tabs) ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "☠️ Mortality", "🌾 Feed", "💰 Sales", "💸 Expenses & Medicine"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header(f"Active Batch: {active_batch_id}")
    
    col_setup, col_delete = st.columns([2, 1])
    with col_setup:
        with st.expander("➕ Start New Batch"):
            with st.form("batch_setup_form", clear_on_submit=True):
                b_id = st.text_input("Batch ID")
                b_date = st.date_input("Arrival Date")
                b_count = st.number_input("Chick Count", min_value=1)
                b_cost = st.number_input("Chick Cost (₹)")
                f_qty = st.number_input("Initial Feed (Bags)")
                f_price = st.number_input("Feed Price (₹/Bag)")
                if st.form_submit_button("Initialize"):
                    add_row_to_sheet("Batch_Setup", [b_id, b_date.strftime("%d/%m/%Y"), b_count, b_cost, f_qty, f_price])
                    st.rerun()

    with col_delete:
        if active_batch_id != "No Active Batch":
            if st.button(f"🗑️ Delete Batch {active_batch_id}"):
                ws = sheet.worksheet("Batch_Setup")
                rows = ws.get_all_values()
                for i, row in enumerate(rows):
                    if row[0] == active_batch_id:
                        ws.delete_rows(i + 1)
                        st.rerun()
    
    st.divider()
    
    if active_batch_id != "No Active Batch":
        t_med = get_total_from_col("Medicine_Log")
        t_a = get_total_from_col("Expenses_A")
        t_b = get_total_from_col("Expenses_B")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Medicine Total", f"₹{t_med:,.2f}")
        m2.metric("Person A Expenses", f"₹{t_a:,.2f}")
        m3.metric("Person B Expenses", f"₹{t_b:,.2f}")

# --- TAB 2: MORTALITY ---
with tab2:
    st.header("Log Mortality")
    with st.form("mort_form", clear_on_submit=True):
        m_date = st.date_input("Date")
        m_batch = st.text_input("Batch ID", value=active_batch_id)
        m_qty = st.number_input("Deaths", min_value=1)
        if st.form_submit_button("Save Mortality"):
            add_row_to_sheet("Mortality_Log", [m_date.strftime("%d/%m/%Y"), m_batch, m_qty])

# --- TAB 3: FEED (Now Before Sales) ---
with tab4:
    st.header("Log Feed")
    with st.form("feed_form", clear_on_submit=True):
        f_date = st.date_input("Date")
        f_batch = st.text_input("Batch ID", value=active_batch_id)
        f_bags = st.number_input("Bags Purchased", min_value=1)
        if st.form_submit_button("Save Feed"):
            add_row_to_sheet("Feed_Log", [f_date.strftime("%d/%m/%Y"), f_batch, f_bags])

# --- TAB 4: SALES (Now After Feed) ---
with tab3:
    st.header("Log Sales")
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date")
        s_batch = st.text_input("Batch ID", value=active_batch_id)
        s_birds = st.number_input("Birds Sold", min_value=1)
        s_weight = st.number_input("Total Weight (kg)")
        s_price = st.number_input("Total Sale Price (₹)")
        if st.form_submit_button("Save Sale"):
            add_row_to_sheet("Sales_Log", [s_date.strftime("%d/%m/%Y"), s_batch, s_birds, s_weight, s_price])

# --- TAB 5: MEDICINE & EXPENSES ---
with tab5:
    st.header("Additional Costs")
    col_med, col_a, col_b = st.columns(3)
    
    with col_med:
        st.subheader("💊 Medicine")
        with st.form("med_form", clear_on_submit=True):
            med_date = st.date_input("Date")
            med_item = st.text_input("Item")
            med_cost = st.number_input("Cost (₹)", key="med_c")
            if st.form_submit_button("Log Medicine"):
                add_row_to_sheet("Medicine_Log", [med_date.strftime("%d/%m/%Y"), active_batch_id, med_item, med_cost])

    with col_a:
        st.subheader("👤 Person A")
        with st.form("a_form", clear_on_submit=True):
            a_date = st.date_input("Date")
            a_item = st.text_input("Item")
            a_cost = st.number_input("Cost (₹)", key="a_c")
            if st.form_submit_button("Log Person A"):
                add_row_to_sheet("Expenses_A", [a_date.strftime("%d/%m/%Y"), active_batch_id, a_item, a_cost])

    with col_b:
        st.subheader("👤 Person B")
        with st.form("b_form", clear_on_submit=True):
            b_date = st.date_input("Date")
            b_item = st.text_input("Item")
            b_cost = st.number_input("Cost (₹)", key="b_c")
            if st.form_submit_button("Log Person B"):
                add_row_to_sheet("Expenses_B", [b_date.strftime("%d/%m/%Y"), active_batch_id, b_item, b_cost])
