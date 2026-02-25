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
        # Define the required Google permissions
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Pull the secret JSON from Streamlit's secure vault
        secret_data = st.secrets["GCP_SERVICE_ACCOUNT"]
        
        # Ensure it reads the JSON format properly
        if isinstance(secret_data, str):
            secret_data = json.loads(secret_data)
            
        creds = Credentials.from_service_account_info(secret_data, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open your specific sheet
        return client.open("Poultry_Data_Vault")
        
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        st.stop()

# Initialize connection
sheet = connect_to_sheets()

# --- Helper Function to Save Data ---
def add_row_to_sheet(worksheet_name, row_data):
    try:
        ws = sheet.worksheet(worksheet_name)
        ws.append_row(row_data)
        st.success(f"✅ Data successfully saved to {worksheet_name}!")
    except Exception as e:
        st.error(f"❌ Failed to save data. Make sure the tab name is exactly '{worksheet_name}'. Error: {e}")

# --- Navigation Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "☠️ Mortality", "💰 Sales", "🌾 Feed", "💸 Expenses"])

# --- TAB 1: Dashboard (Live Inventory & Age) ---
with tab1:
    st.header("Current Batch Status")
    try:
        batch_ws = sheet.worksheet("Batch_Setup")
        batch_data = batch_ws.get_all_records()
        
        if batch_data:
            df_batch = pd.DataFrame(batch_data)
            latest_batch = df_batch.iloc[-1] # Gets the most recent batch
            
            batch_id = latest_batch.get("Batch_Id", "Unknown")
            arrival_str = str(latest_batch.get("Arrival_Date", ""))
            initial_count = int(latest_batch.get("Chick_Count", 0))
            
            # Calculate Age automatically
            try:
                arrival_date = datetime.strptime(arrival_str, "%d/%m/%Y").date()
                age_days = (datetime.now().date() - arrival_date).days
            except:
                age_days = "Date Format Error"
            
            # Show Metrics cleanly on screen
            col1, col2, col3 = st.columns(3)
            col1.metric("Batch ID", batch_id)
            col2.metric("Age (Days)", age_days)
            col3.metric("Initial Chicks", initial_count)
            
            st.info("💡 Additional Live Inventory features (deaths & sales math) will populate here as you add more data!")
        else:
            st.warning("No batch data found. Please add your first row to the 'Batch_Setup' tab in your Google Sheet.")
    except Exception as e:
        st.warning(f"Could not load Dashboard data. Check your 'Batch_Setup' tab headers. Error: {e}")

# --- TAB 2: Mortality Log ---
with tab2:
    st.header("Log Deaths")
    with st.form("mortality_form", clear_on_submit=True):
        m_date = st.date_input("Date")
        m_batch = st.text_input("Batch ID", value="Batch-01")
        m_deaths = st.number_input("Number of Deaths", min_value=1, step=1)
        m_reason = st.text_input("Reason / Notes")
        
        if st.form_submit_button("Save Mortality"):
            formatted_date = m_date.strftime("%d/%m/%Y")
            add_row_to_sheet("Mortality_Log", [formatted_date, m_batch, m_deaths, m_reason])

# --- TAB 3: Sales Log ---
with tab3:
    st.header("Log Sales (Trips)")
    with st.form("sales_form", clear_on_submit=True):
        s_date = st.date_input("Date of Sale")
        s_batch = st.text_input("Batch ID", value="Batch-01")
        s_birds = st.number_input("Number of Birds Sold", min_value=1, step=1)
        s_weight = st.number_input("Total Weight (kg)", min_value=0.0, step=0.1)
        s_price = st.number_input("Total Price (₹)", min_value=0.0, step=10.0)
        s_trip = st.text_input("Trip / Container Info")
        
        if st.form_submit_button("Save Sale"):
            formatted_date = s_date.strftime("%d/%m/%Y")
            # Assumes your Google Sheet tab is named 'Sales_Log'
            add_row_to_sheet("Sales
