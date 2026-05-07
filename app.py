import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import hashlib

# --- 1. CONFIGURATION ---
MASTER_EMAIL = "desinduhansana@gmail.com"
# 👇 PASTE YOUR GOOGLE SHEET LINK HERE 👇
SHEET_URL = "PASTE_YOUR_GOOGLE_SHEET_URL_HERE"
# https://docs.google.com/spreadsheets/d/11JWwxG-HqdYAc_Fwz5QW5AntfEXkMHtmo9Eq6WAnCbI/edit?usp=sharing
st.set_page_config(page_title="Desu's Garage Management", layout="wide")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Helper to read data safely
def get_data(worksheet):
    return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl=0).dropna(how="all")

# --- 2. LOGIN & APPROVAL SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Garage Management Login")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    users_df = get_data("Users")

    with tab1:
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            user_row = users_df[users_df['email'] == email]
            if not user_row.empty:
                stored_pw = user_row.iloc[0]['password']
                status = user_row.iloc[0]['status']
                if check_hashes(pw, stored_pw):
                    if status == "Approved" or email == MASTER_EMAIL:
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.warning("⏳ Access Pending. Desu needs to approve your email.")
                else:
                    st.error("Invalid Password")
            else:
                st.error("User not found")

    with tab2:
        new_email = st.text_input("New Staff Email")
        new_pw = st.text_input("New Password", type="password")
        if st.button("Request Access"):
            if new_email not in users_df['email'].values:
                # Master is auto-approved, others stay "Pending"
                status = "Approved" if new_email == MASTER_EMAIL else "Pending"
                new_user = pd.DataFrame([{"email": new_email, "password": make_hashes(new_pw), "status": status}])
                updated_users = pd.concat([users_df, new_user], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated_users)
                st.success("Request Sent! Wait for Desu to approve you.")
            else:
                st.error("Email already registered.")

# --- 3. THE MAIN APP (Only visible after Login) ---
else:
    st.sidebar.title(f"👤 {st.session_state.user_email}")
    
    # MASTER APPROVAL CENTER
    if st.session_state.user_email == MASTER_EMAIL:
        with st.sidebar.expander("⭐ Approval Center"):
            users_df = get_data("Users")
            pending = users_df[users_df['status'] == "Pending"]
            if not pending.empty:
                to_approve = st.selectbox("Select Staff to Approve:", pending['email'])
                if st.button("Approve Now"):
                    users_df.loc[users_df['email'] == to_approve, 'status'] = 'Approved'
                    conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=users_df)
                    st.success(f"{to_approve} Approved!")
                    st.rerun()
            else:
                st.write("No pending requests.")

    page = st.sidebar.radio("Navigation", ["🛒 Checkout", "📦 Inventory (Stock)", "📈 Profits"])

    # --- CHECKOUT PAGE (Selling) ---
    if page == "🛒 Checkout":
        st.header("🛒 Sales Checkout")
        
        # CAMERA BARCODE SYSTEM
        st.subheader("Scan Barcode")
        st.camera_input("Point phone camera at barcode")
        
        with st.form("sale_form", clear_on_submit=True):
            bc = st.text_input("Enter Scanned Barcode Number")
            qty = st.number_input("Quantity", min_value=1, value=1)
            if st.form_submit_button("Complete Sale"):
                inv_df = get_data("Inventory")
                sales_df = get_data("Sales")
                item = inv_df[inv_df['barcode'].astype(str) == str(bc)]
                
                if not item.empty:
                    idx = item.index[0]
                    stock = inv_df.at[idx, 'quantity']
                    if stock >= qty:
                        # Update Inventory
                        inv_df.at[idx, 'quantity'] = stock - qty
                        conn.update(spreadsheet=SHEET_URL, worksheet="Inventory", data=inv_df)
                        
                        # Add to Sales History
                        new_sale = pd.DataFrame([{
                            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Part_Name": inv_df.at[idx, 'part_name'],
                            "Income": inv_df.at[idx, 'selling_price'] * qty
                        }])
                        updated_sales = pd.concat([sales_df, new_sale], ignore_index=True)
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sales", data=updated_sales)
                        st.success("✅ Sale Successful!")
                        st.rerun()
                else:
                    st.error("Barcode not found in database.")

    # --- INVENTORY PAGE (Stocking) ---
    elif page == "📦 Inventory (Stock)":
        st.header("📦 Stock Management")
        
        st.subheader("Scan to Add New Stock")
        st.camera_input("Scan item to restock")

        with st.form("inv_form", clear_on_submit=True):
            bc = st.text_input("Barcode")
            name = st.text_input("Item Name")
            qty = st.number_input("Qty to Add", min_value=1)
            cost = st.number_input("Cost Price")
            sell = st.number_input("Selling Price")
            
            if st.form_submit_button("Save to Stock"):
                inv_df = get_data("Inventory")
                match = inv_df[inv_df['barcode'].astype(str) == str(bc)]
                
                if not match.empty:
                    idx = match.index[0]
                    inv_df.at[idx, 'quantity'] += qty
                else:
                    new_item = pd.DataFrame([{"barcode": bc, "part_name": name, "quantity": qty, "cost_price": cost, "selling_price": sell}])
                    inv_df = pd.concat([inv_df, new_item], ignore_index=True)
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Inventory", data=inv_df)
                st.success("✅ Stock Successfully Updated!")
                st.rerun()

    # --- PROFITS PAGE (Master Only) ---
    elif page == "📈 Profits":
        if st.session_state.user_email == MASTER_EMAIL:
            st.header("📈 Financial Report")
            sales_df = get_data("Sales")
            st.metric("Total Revenue", f"Rs. {sales_df['Income'].sum():,.2f}")
            st.dataframe(sales_df, use_container_width=True)
        else:
            st.error("🚫 Access Denied. Only Master Admin can see financials.")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()