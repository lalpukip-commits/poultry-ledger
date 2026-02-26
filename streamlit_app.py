import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import date

# --- 1. SETUP & AUTHENTICATION ---
# Replace 'your-google-sheet-name' with your actual sheet name
SHEET_NAME = "Your_Poultry_Sheet_Name"
# Replace 'path/to/your/credentials.json' with your file path
SERVICE_ACCOUNT_FILE = 'credentials.json'

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)

# Helper function to get sheet data as DataFrame
def get_df(sheet_name):
    sheet = spreadsheet.worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

# Helper function to append to sheet
def append_row(sheet_name, row):
    spreadsheet.worksheet(sheet_name).append_row(row)

# --- 2. SESSION STATE ---
if 'batch_id' not in st.session_state:
    st.session_state.batch_id = None

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🐓 Poultry Manager")
tab_choice = st.sidebar.radio("Go to:", ["Dashboard", "Feed Log", "Mortality", "Sales", "Expenses"])

# Batch Selector
dash_df = get_df("Dashboard")
all_batches = ["Create New Batch"] + dash_df['Batch_ID'].tolist() if not dash_df.empty else ["Create New Batch"]
selected_batch = st.sidebar.selectbox("Select Batch:", all_batches)

if selected_batch == "Create New Batch":
    st.session_state.batch_id = None
else:
    st.session_state.batch_id = selected_batch

# Get Current Batch Status
batch_status = "New"
current_batch_data = {}
if st.session_state.batch_id:
    row = dash_df[dash_df['Batch_ID'] == st.session_state.batch_id].iloc[0]
    batch_status = row['Status']
    current_batch_data = row.to_dict()

st.sidebar.markdown(f"**Current Status:** `{batch_status}`")

# --- 4. TAB LOGIC ---

# ---------------- DASHBOARD ----------------
if tab_choice == "Dashboard":
    st.title("📊 Batch Dashboard")
    
    if selected_batch == "Create New Batch":
        with st.form("new_batch_form"):
            new_id = st.text_input("Enter New Batch ID (e.g., B-001)")
            submitted = st.form_submit_button("Create Pre-Arrival Batch")
            if submitted and new_id:
                append_row("Dashboard", [new_id, "", 0, 0, 0, "Pre-Arrival"])
                st.success("Batch created! You can now log expenses.")
                st.rerun()

    elif batch_status == "Pre-Arrival":
        st.subheader("Start the Batch")
        st.info("Chicks haven't arrived yet. Expenses are unlocked.")
        with st.form("start_batch"):
            arr_date = st.date_input("Arrival Date")
            count = st.number_input("Chick Count", min_value=1)
            price = st.number_input("Price per Chick", min_value=0.0)
            if st.form_submit_button("Save Arrival Details"):
                # Update Dashboard row
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(st.session_state.batch_id)
                sheet.update_cell(cell.row, 2, str(arr_date))
                sheet.update_cell(cell.row, 3, count)
                sheet.update_cell(cell.row, 4, price)
                sheet.update_cell(cell.row, 5, count * price)
                sheet.update_cell(cell.row, 6, "Active")
                st.success("Batch is now ACTIVE!")
                st.rerun()

    elif batch_status == "Active":
        st.success("Batch is Active. All logs open.")
        if st.button("🏁 FINISH & AUDIT BATCH"):
            # Calculate Audit
            feed_df = get_df("Feed_Log")
            feed_df = feed_df[feed_df['Batch_ID'] == st.session_state.batch_id]
            mort_df = get_df("Mortality_Log")
            mort_df = mort_df[mort_df['Batch_ID'] == st.session_state.batch_id]
            sales_df = get_df("Sales_Log")
            sales_df = sales_df[sales_df['Batch_ID'] == st.session_state.batch_id]
            exp_df = get_df("Expenses_Log")
            exp_df = exp_df[exp_df['Batch_ID'] == st.session_state.batch_id]

            st.divider()
            st.header("Preliminary Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Feed Bags", feed_df['Bags'].sum())
                st.metric("Total Sold", sales_df['Bird_Count'].sum())
                st.metric("Total Mortality", mort_df['Mortality_Count'].sum())
            with col2:
                total_rev = sales_df['Total_Revenue'].sum()
                total_feed = feed_df['Daily_Total'].sum()
                st.metric("Net (Revenue - Feed)", f"₹{total_rev - total_feed}")

            st.subheader("Other Expenses")
            st.write(f"Medicine: ₹{exp_df[exp_df['Category']=='Medicine']['Price'].sum()}")
            st.write(f"Person A: ₹{exp_df[exp_df['Category']=='Person A']['Price'].sum()}")
            st.write(f"Person B: ₹{exp_df[exp_df['Category']=='Person B']['Price'].sum()}")
            
            if st.button("Confirm & Finalize (LOCK DATA)"):
                sheet = spreadsheet.worksheet("Dashboard")
                cell = sheet.find(st.session_state.batch_id)
                sheet.update_cell(cell.row, 6, "Finalized")
                st.rerun()

    if batch_status != "New" and batch_status != "Finalized":
        if st.button("🗑️ Delete Batch"):
            # Logic to clear all logs for this ID...
            st.warning("Delete logic triggered (requires sheet range deletion)")

# ---------------- SALES TAB (THE GRID) ----------------
elif tab_choice == "Sales":
    st.title("💰 Sales & Revenue")
    if not st.session_state.batch_id or batch_status == "Pre-Arrival":
        st.warning("Chicks must arrive before sales can be logged.")
    else:
        # Inventory Calculation
        mort_df = get_df("Mortality_Log")
        sold_df = get_df("Sales_Log")
        total_mort = mort_df[mort_df['Batch_ID']==st.session_state.batch_id]['Mortality_Count'].sum()
        total_sold = sold_df[sold_df['Batch_ID']==st.session_state.batch_id]['Bird_Count'].sum()
        remaining = current_batch_data['Chick_Count'] - total_mort - total_sold
        
        st.subheader(f"Inventory: {remaining} Birds Remaining")
        
        if batch_status == "Active":
            with st.expander("Log New Sale", expanded=True):
                s_date = st.date_input("Sale Date")
                price_kg = st.number_input("Price per KG", min_value=0.0)
                num_trips = st.number_input("Number of Trips today", min_value=1, step=1)
                
                all_trip_data = []
                for t in range(int(num_trips)):
                    st.markdown(f"--- **Trip {t+1}** ---")
                    num_containers = st.number_input(f"Containers for Trip {t+1}", min_value=1, key=f"t_{t}")
                    for c in range(int(num_containers)):
                        cols = st.columns(2)
                        weight = cols[0].number_input(f"T{t+1}-C{c+1} Weight (KG)", key=f"w_{t}_{c}")
                        birds = cols[1].number_input(f"T{t+1}-C{c+1} Bird Count", value=10, key=f"b_{t}_{c}")
                        all_trip_data.append([str(s_date), t+1, c+1, birds, weight, price_kg, weight*price_kg, st.session_state.batch_id])
                
                if st.button("Save All Trips"):
                    for row in all_trip_data:
                        append_row("Sales_Log", row)
                    st.success("Sales Recorded!")
                    st.rerun()
        
        # Display History
        st.dataframe(sold_df[sold_df['Batch_ID'] == st.session_state.batch_id])

# ---------------- EXPENSES TAB (N ENTRIES) ----------------
elif tab_choice == "Expenses":
    st.title("💊 Expenses & Medicine")
    if not st.session_state.batch_id:
        st.warning("Please create or select a batch first.")
    else:
        exp_df = get_df("Expenses_Log")
        batch_exp = exp_df[exp_df['Batch_ID'] == st.session_state.batch_id]
        
        st.metric("Total Spent So Far", f"₹{batch_exp['Price'].sum()}")
        
        if batch_status != "Finalized":
            cat = st.selectbox("Category", ["Medicine", "Person A", "Person B"])
            with st.form("exp_form", clear_on_submit=True):
                e_date = st.date_input("Date")
                name = st.text_input("Item Name")
                desc = st.text_area("Description")
                amt = st.number_input("Price", min_value=0.0)
                if st.form_submit_button("Add Expense"):
                    append_row("Expenses_Log", [str(e_date), cat, name, desc, amt, st.session_state.batch_id])
                    st.rerun()
        
        st.subheader("Expense History")
        st.table(batch_exp)

# Note: Similar logic applies to Feed and Mortality tabs (forms + DF display)
