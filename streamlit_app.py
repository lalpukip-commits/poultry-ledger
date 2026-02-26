import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date

# --- 1. AUTHENTICATION (Using Your Specific Secret Key) ---
try:
    # This matches the [GSP_SERVICE_ACCOUNT] header in your Streamlit Secrets
    creds_dict = st.secrets["GSP_SERVICE_ACCOUNT"]
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # IMPORTANT: Change this to the exact name of your Google Sheet
    SHEET_NAME = "Poultry_Data_Vault" 
    spreadsheet = client.open(SHEET_NAME)
except Exception as e:
    st.error(f"Authentication Error: {e}")
    st.info("Check your Streamlit Secrets and Google Sheet name.")
    st.stop()

# --- 2. HELPER FUNCTIONS ---
def get_df(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_row(sheet_name, row_list):
    spreadsheet.worksheet(sheet_name).append_row(row_list)

# --- 3. NAVIGATION & BATCH SELECTION ---
st.sidebar.title("🐓 Poultry Manager")
nav = st.sidebar.radio("Go to:", ["Dashboard", "Feed Log", "Mortality", "Sales", "Expenses"])

# Fetch Batch List from Dashboard Tab
dash_df = get_df("Dashboard")
if not dash_df.empty:
    batch_list = ["+ Create New Batch"] + dash_df['Batch_ID'].tolist()
else:
    batch_list = ["+ Create New Batch"]

selected_batch = st.sidebar.selectbox("Select Batch:", batch_list)

# Set Session State for the Active Batch
if selected_batch == "+ Create New Batch":
    active_id = None
    status = "New"
else:
    active_id = selected_batch
    status = dash_df[dash_df['Batch_ID'] == active_id]['Status'].values[0]

st.sidebar.divider()
st.sidebar.write(f"**Current Batch:** `{active_id}`")
st.sidebar.write(f"**Status:** `{status}`")

# --- 4. DASHBOARD TAB ---
if nav == "Dashboard":
    st.title("📊 Batch Dashboard")
    
    if status == "New":
        with st.form("create_batch_form"):
            new_id = st.text_input("Enter New Batch ID (e.g., B-01)")
            if st.form_submit_button("Create Pre-Arrival Batch"):
                append_row("Dashboard", [new_id, "", 0, 0, 0, "Pre-Arrival"])
                st.success("Batch created! Expenses are now unlocked.")
                st.rerun()
                
    elif status == "Pre-Arrival":
        st.info("Chicks have not arrived yet. Only the Expenses tab is active.")
        with st.form("activate_batch"):
            arr_date = st.date_input("Actual Arrival Date")
            count = st.number_input("Total Chick Count", min_value=1)
            price = st.number_input("Price per Chick", min_value=0.0)
            if st.form_submit_button("Record Arrival & Unlock All Tabs"):
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(active_id)
                sheet.update_cell(cell.row, 2, str(arr_date))
                sheet.update_cell(cell.row, 3, count)
                sheet.update_cell(cell.row, 4, price)
                sheet.update_cell(cell.row, 5, count * price)
                sheet.update_cell(cell.row, 6, "Active")
                st.rerun()

    elif status == "Active":
        st.success("Batch is Active. All features are enabled.")
        if st.button("🏁 SHOW FINAL AUDIT & FINISH"):
            feed = get_df("Feed_Log").query(f"Batch_ID == '{active_id}'")
            sales = get_df("Sales_Log").query(f"Batch_ID == '{active_id}'")
            mort = get_df("Mortality_Log").query(f"Batch_ID == '{active_id}'")
            exp = get_df("Expenses_Log").query(f"Batch_ID == '{active_id}'")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Feed Bags", feed['Bags'].sum())
                st.metric("Total Mortality", mort['Mortality_Count'].sum())
            with col2:
                total_rev = sales['Total_Revenue'].sum()
                total_feed_cost = feed['Daily_Total'].sum()
                st.metric("Net Total (Revenue - Feed)", f"₹{total_rev - total_feed_cost}")
            
            st.subheader("Other Expenses")
            st.write(f"Medicine: ₹{exp[exp['Category']=='Medicine']['Price'].sum()}")
            st.write(f"Person A: ₹{exp[exp['Category']=='Person A']['Price'].sum()}")
            st.write(f"Person B: ₹{exp[exp['Category']=='Person B']['Price'].sum()}")
            
            if st.button("🔴 LOCK & FINALIZE BATCH"):
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(active_id)
                sheet.update_cell(cell.row, 6, "Finalized")
                st.rerun()

# --- 5. LOGGING TABS (FEED, MORTALITY, EXPENSES) ---
elif nav in ["Feed Log", "Mortality", "Expenses"]:
    st.title(f"📝 {nav}")
    if not active_id:
        st.warning("Please select or create a batch first.")
    else:
        # Feed Logic
        if nav == "Feed Log":
            if status == "Pre-Arrival": st.warning("Locked. Please confirm chick arrival on Dashboard.")
            else:
                if status == "Active":
                    with st.form("feed_form", clear_on_submit=True):
                        f_type = st.text_input("Feed Type")
                        bags = st.number_input("Number of Bags", min_value=1)
                        p_bag = st.number_input("Price per Bag")
                        if st.form_submit_button("Save Feed Entry"):
                            append_row("Feed_Log", [str(date.today()), f_type, bags, p_bag, bags*p_bag, active_id])
                st.dataframe(get_df("Feed_Log").query(f"Batch_ID == '{active_id}'"))

        # Mortality Logic
        elif nav == "Mortality":
            if status == "Pre-Arrival": st.warning("Locked. Please confirm chick arrival on Dashboard.")
            else:
                if status == "Active":
                    with st.form("mort_form", clear_on_submit=True):
                        m_count = st.number_input("Birds Lost Today", min_value=1)
                        if st.form_submit_button("Save Mortality"):
                            append_row("Mortality_Log", [str(date.today()), m_count, active_id])
                st.dataframe(get_df("Mortality_Log").query(f"Batch_ID == '{active_id}'"))

        # Expenses Logic (Always open for Pre-Arrival and Active)
        elif nav == "Expenses":
            if status != "Finalized":
                with st.form("exp_form", clear_on_submit=True):
                    cat = st.selectbox("Category", ["Medicine", "Person A", "Person B"])
                    item = st.text_input("Item/Service Name")
                    amt = st.number_input("Amount Paid", min_value=0.0)
                    if st.form_submit_button("Save Expense"):
                        append_row("Expenses_Log", [str(date.today()), cat, item, "", amt, active_id])
            st.dataframe(get_df("Expenses_Log").query(f"Batch_ID == '{active_id}'"))

# --- 6. SALES TAB (CONTAINER GRID) ---
elif nav == "Sales":
    st.title("💰 Sales Entry")
    if status != "Active" and status != "Finalized":
        st.warning("Sales tab unlocks only after chicks arrive.")
    else:
        if status == "Active":
            with st.expander("Record Today's Sale", expanded=True):
                p_kg = st.number_input("Daily Price per KG")
                trips = st.number_input("How many trips today?", min_value=1, step=1)
                
                all_sales_data = []
                for t in range(int(trips)):
                    st.markdown(f"**Trip {t+1}**")
                    containers = st.number_input(f"Number of Containers (Trip {t+1})", min_value=1, step=1, key=f"t{t}")
                    for c in range(int(containers)):
                        col1, col2 = st.columns(2)
                        weight = col1.number_input(f"Weight KG (C{c+1})", key=f"w{t}{c}")
                        birds = col2.number_input(f"Bird Count (C{c+1})", value=10, key=f"b{t}{c}")
                        all_sales_data.append([str(date.today()), t+1, c+1, birds, weight, p_kg, weight*p_kg, active_id])
                
                if st.button("Upload All Trip Data to Spreadsheet"):
                    for row in all_sales_data:
                        append_row("Sales_Log", row)
                    st.success("Successfully uploaded!"); st.rerun()
        
        st.dataframe(get_df("Sales_Log").query(f"Batch_ID == '{active_id}'"))
