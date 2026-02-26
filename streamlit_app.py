import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date

# --- 1. AUTHENTICATION (Using Streamlit Secrets) ---
# Make sure you have your secrets set up in the Streamlit Cloud Dashboard
try:
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # CHANGE THIS to your exact Google Sheet name
    SHEET_NAME = "Your_Poultry_Sheet_Name" 
    spreadsheet = client.open(SHEET_NAME)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# Helper Functions
def get_df(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def append_row(sheet_name, row_list):
    spreadsheet.worksheet(sheet_name).append_row(row_list)

# --- 2. NAVIGATION & BATCH SELECTION ---
st.sidebar.title("🐓 Poultry Manager")
nav = st.sidebar.radio("Menu", ["Dashboard", "Feed Log", "Mortality", "Sales", "Expenses"])

dash_df = get_df("Dashboard")
batch_list = ["+ Create New Batch"] + dash_df['Batch_ID'].tolist() if not dash_df.empty else ["+ Create New Batch"]
selected_batch = st.sidebar.selectbox("Select Batch", batch_list)

# Global State for Batch ID
if selected_batch == "+ Create New Batch":
    active_id = None
    status = "New"
else:
    active_id = selected_batch
    status = dash_df[dash_df['Batch_ID'] == active_id]['Status'].values[0]

st.sidebar.divider()
st.sidebar.info(f"Current Batch: **{active_id}**\n\nStatus: **{status}**")

# --- 3. DASHBOARD (Setup & Finalization) ---
if nav == "Dashboard":
    st.title("📊 Batch Dashboard")
    
    if status == "New":
        with st.form("new_batch"):
            new_id = st.text_input("New Batch ID")
            if st.form_submit_button("Create Pre-Arrival Batch"):
                append_row("Dashboard", [new_id, "", 0, 0, 0, "Pre-Arrival"])
                st.rerun()
                
    elif status == "Pre-Arrival":
        st.warning("Status: Pre-Arrival (Only Expenses Unlocked)")
        with st.form("activate_batch"):
            arr_date = st.date_input("Arrival Date")
            count = st.number_input("Chick Count", min_value=1)
            price = st.number_input("Price per Chick", min_value=0.0)
            if st.form_submit_button("Confirm Chick Arrival"):
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(active_id)
                sheet.update_cell(cell.row, 2, str(arr_date))
                sheet.update_cell(cell.row, 3, count)
                sheet.update_cell(cell.row, 4, price)
                sheet.update_cell(cell.row, 5, count * price)
                sheet.update_cell(cell.row, 6, "Active")
                st.rerun()

    elif status == "Active":
        st.success("Batch is Active. Logging fully enabled.")
        if st.button("🏁 FINISH & VIEW SUMMARY"):
            # Math Logic
            feed = get_df("Feed_Log")
            feed = feed[feed['Batch_ID'] == active_id]
            sales = get_df("Sales_Log")
            sales = sales[sales['Batch_ID'] == active_id]
            mort = get_df("Mortality_Log")
            mort = mort[mort['Batch_ID'] == active_id]
            exp = get_df("Expenses_Log")
            exp = exp[exp['Batch_ID'] == active_id]
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Bags", feed['Bags'].sum())
            c2.metric("Total Mortality", mort['Mortality_Count'].sum())
            c3.metric("Remaining/Rejects", int(dash_df[dash_df['Batch_ID']==active_id]['Chick_Count'].values[0] - mort['Mortality_Count'].sum() - sales['Bird_Count'].sum()))
            
            rev = sales['Total_Revenue'].sum()
            f_cost = feed['Daily_Total'].sum()
            st.metric("NET TOTAL (Revenue - Feed Only)", f"₹{rev - f_cost}")
            
            st.subheader("Other Expenses (Separate)")
            st.write(f"Medicine Total: ₹{exp[exp['Category']=='Medicine']['Price'].sum()}")
            st.write(f"Person A Total: ₹{exp[exp['Category']=='Person A']['Price'].sum()}")
            st.write(f"Person B Total: ₹{exp[exp['Category']=='Person B']['Price'].sum()}")
            
            if st.button("🔴 FINALISE (NO MORE EDITS)"):
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(active_id)
                sheet.update_cell(cell.row, 6, "Finalized")
                st.rerun()

# --- 4. LOGGING TABS (FEED, MORTALITY, EXPENSES) ---
elif nav in ["Feed Log", "Mortality", "Expenses"]:
    st.title(f"📝 {nav}")
    if status == "Finalized": st.error("READ ONLY MODE - Batch Finalized")
    
    if nav == "Feed Log":
        if status == "Pre-Arrival": st.warning("Locked until chicks arrive.")
        else:
            if status == "Active":
                with st.form("feed_form", clear_on_submit=True):
                    f_type = st.text_input("Feed Type")
                    bags = st.number_input("Bags", min_value=1)
                    p_bag = st.number_input("Price per Bag")
                    if st.form_submit_button("Save"):
                        append_row("Feed_Log", [str(date.today()), f_type, bags, p_bag, bags*p_bag, active_id])
            st.dataframe(get_df("Feed_Log").query(f"Batch_ID == '{active_id}'"))

    elif nav == "Mortality":
        if status == "Pre-Arrival": st.warning("Locked until chicks arrive.")
        else:
            if status == "Active":
                with st.form("mort_form", clear_on_submit=True):
                    m_count = st.number_input("Birds Dead", min_value=1)
                    if st.form_submit_button("Save"):
                        append_row("Mortality_Log", [str(date.today()), m_count, active_id])
            st.dataframe(get_df("Mortality_Log").query(f"Batch_ID == '{active_id}'"))

    elif nav == "Expenses":
        if status != "Finalized":
            with st.form("exp_form", clear_on_submit=True):
                cat = st.selectbox("Category", ["Medicine", "Person A", "Person B"])
                item = st.text_input("Item Name")
                amt = st.number_input("Price", min_value=0.0)
                if st.form_submit_button("Add Expense"):
                    append_row("Expenses_Log", [str(date.today()), cat, item, "", amt, active_id])
        st.dataframe(get_df("Expenses_Log").query(f"Batch_ID == '{active_id}'"))

# --- 5. SALES TAB (THE CONTAINER GRID) ---
elif nav == "Sales":
    st.title("💰 Sales Grid")
    if status != "Active" and status != "Finalized":
        st.warning("Sales only available when Batch is Active.")
    else:
        if status == "Active":
            with st.expander("New Sales Entry", expanded=True):
                p_kg = st.number_input("Price per KG")
                trips = st.number_input("Number of Trips", min_value=1, step=1)
                all_rows = []
                for t in range(int(trips)):
                    st.subheader(f"Trip {t+1}")
                    conts = st.number_input(f"Containers for Trip {t+1}", min_value=1, step=1, key=f"t{t}")
                    for c in range(int(conts)):
                        col1, col2 = st.columns(2)
                        w = col1.number_input(f"Weight (KG) C{c+1}", key=f"w{t}{c}")
                        b = col2.number_input(f"Birds C{c+1}", value=10, key=f"b{t}{c}")
                        all_rows.append([str(date.today()), t+1, c+1, b, w, p_kg, w*p_kg, active_id])
                if st.button("Save All Sales"):
                    for r in all_rows: append_row("Sales_Log", r)
                    st.success("Saved!"); st.rerun()
        st.dataframe(get_df("Sales_Log").query(f"Batch_ID == '{active_id}'"))
