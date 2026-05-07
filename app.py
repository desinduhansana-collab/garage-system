import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- 1. DATABASE & SECURITY SETUP ---
conn = sqlite3.connect('garage_management.db', check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('CREATE TABLE IF NOT EXISTS parts (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE, part_name TEXT, category TEXT, quantity INTEGER, cost_price REAL, selling_price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, part_name TEXT, qty_sold INTEGER, sale_total REAL, profit REAL, sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
# NEW: Users Table with Approval Status
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (email TEXT PRIMARY KEY, password TEXT, role TEXT, status TEXT)''')
conn.commit()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Master Admin Email
MASTER_EMAIL = "desinduhansana@gmail.com"

# --- 2. LOGIN & REGISTRATION SYSTEM ---
def login_page():
    st.title("🔐 Garage Management Login")
    
    tab1, tab2 = st.tabs(["Login", "Register New Staff"])
    
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type='password')
        if st.button("Login"):
            c.execute('SELECT password, role, status FROM users WHERE email = ?', (email,))
            data = f = c.fetchone()
            if data:
                if check_hashes(password, data[0]):
                    if data[2] == "Approved" or email == MASTER_EMAIL:
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.user_role = data[1]
                        st.success(f"Welcome {email}")
                        st.rerun()
                    else:
                        st.warning("⏳ Your account is pending approval from Desu.")
                else:
                    st.error("Incorrect Password")
            else:
                st.error("Email not found")

    with tab2:
        new_email = st.text_input("Staff Email")
        new_pw = st.text_input("Staff Password", type='password')
        if st.button("Request Access"):
            try:
                # Master email is automatically approved, others are pending
                status = "Approved" if new_email == MASTER_EMAIL else "Pending"
                role = "Admin" if new_email == MASTER_EMAIL else "Staff"
                c.execute('INSERT INTO users(email,password,role,status) VALUES (?,?,?,?)',
                          (new_email, make_hashes(new_pw), role, status))
                conn.commit()
                st.success("Registration Sent! Please wait for Desu to approve you.")
            except:
                st.error("User already exists.")

# --- 3. MAIN APP LOGIC ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    # Sidebar Navigation
    st.sidebar.title("🛠️ Menu")
    st.sidebar.write(f"User: {st.session_state.user_email}")
    
    # MASTER ONLY: Approval Center
    if st.session_state.user_email == MASTER_EMAIL:
        if st.sidebar.checkbox("⭐ Admin Approval Center"):
            st.header("Admin Approval Center")
            users_df = pd.read_sql("SELECT email, role, status FROM users WHERE email != ?", conn, params=(MASTER_EMAIL,))
            st.dataframe(users_df)
            
            email_to_approve = st.selectbox("Select Email to Approve", users_df['email'])
            if st.button("Approve User"):
                c.execute("UPDATE users SET status = 'Approved' WHERE email = ?", (email_to_approve,))
                conn.commit()
                st.success(f"{email_to_approve} can now access the app!")
                st.rerun()

    page = st.sidebar.radio("Navigate to:", ["🛒 Checkout", "📦 Inventory", "📈 Profits"])

    # --- CHECKOUT PAGE ---
    if page == "🛒 Checkout":
        st.header("🛒 Sales")
        # 
        with st.form("sale"):
            bc = st.text_input("Barcode")
            qty = st.number_input("Qty", min_value=1)
            if st.form_submit_button("Complete Sale"):
                c.execute("SELECT id, part_name, quantity, cost_price, selling_price FROM parts WHERE barcode = ?", (bc,))
                item = c.fetchone()
                if item and item[2] >= qty:
                    revenue = item[4] * qty
                    profit = (item[4] - item[3]) * qty
                    c.execute("UPDATE parts SET quantity = ? WHERE id = ?", (item[2]-qty, item[0]))
                    c.execute("INSERT INTO sales (part_name, qty_sold, sale_total, profit) VALUES (?,?,?,?)", (item[1], qty, revenue, profit))
                    conn.commit()
                    st.success("Sale Successful!")
                else:
                    st.error("Stock Error or Item Not Found")

    # --- INVENTORY PAGE ---
    elif page == "📦 Inventory":
        st.header("📦 Stock")
        # Only Master/Approved Management can add/edit
        with st.expander("Add/Update Stock"):
            with st.form("inv"):
                b = st.text_input("Barcode")
                n = st.text_input("Name")
                q = st.number_input("Qty", min_value=1)
                cp = st.number_input("Cost")
                sp = st.number_input("Sell")
                if st.form_submit_button("Save"):
                    c.execute("INSERT OR REPLACE INTO parts (barcode, part_name, quantity, cost_price, selling_price) VALUES (?,?,?,?,?)", (b,n,q,cp,sp))
                    conn.commit()
                    st.success("Inventory Updated")
        
        st.dataframe(pd.read_sql("SELECT * FROM parts", conn), use_container_width=True)

    # --- PROFITS PAGE ---
    elif page == "📈 Profits":
        if st.session_state.user_email == MASTER_EMAIL:
            st.header("📈 Master Financials")
            sales = pd.read_sql("SELECT * FROM sales", conn)
            st.metric("Total Revenue", f"Rs. {sales['sale_total'].sum():,.2f}")
            st.metric("Total Profit", f"Rs. {sales['profit'].sum():,.2f}")
            st.dataframe(sales)
        else:
            st.warning("🚫 Only the Master Admin can see financial reports.")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()