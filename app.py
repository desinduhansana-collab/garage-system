import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. Database Setup (SQLite - Local History) ---
conn = sqlite3.connect('garage_inventory.db')
c = conn.cursor()

# Table for Parts
c.execute('''
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT,
        part_name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER NOT NULL,
        price REAL
    )
''')

# Table for Sales History (This is where the history lives!)
c.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_name TEXT NOT NULL,
        quantity_sold INTEGER NOT NULL,
        total_income REAL NOT NULL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# --- 2. The Web Page UI ---
st.set_page_config(page_title="Desu's Garage", page_icon="🏍️")
st.title("🏍️ Desu's Garage Management")

# Sidebar for Navigation
menu = st.sidebar.selectbox("Go to Page", ["🛒 Checkout", "📦 Inventory", "📈 Sales History"])

# ==========================================
# PAGE 1: CHECKOUT (Selling Items)
# ==========================================
if menu == "🛒 Checkout":
    st.header("Sell Parts")
    with st.form("sell_form", clear_on_submit=True):
        scanned_barcode = st.text_input("Scan Barcode")
        sell_qty = st.number_input("Quantity", min_value=1, value=1)
        submit_sale = st.form_submit_button("Complete Sale")

        if submit_sale:
            c.execute("SELECT id, part_name, quantity, price FROM parts WHERE barcode = ?", (scanned_barcode,))
            item = c.fetchone()
            
            if item:
                p_id, p_name, p_qty, p_price = item
                if p_qty >= sell_qty:
                    # 1. Update Inventory
                    new_qty = p_qty - sell_qty
                    c.execute("UPDATE parts SET quantity = ? WHERE id = ?", (new_qty, p_id))
                    
                    # 2. RECORD HISTORY (Save the sale!)
                    income = p_price * sell_qty
                    c.execute("INSERT INTO sales (part_name, quantity_sold, total_income) VALUES (?, ?, ?)", 
                              (p_name, sell_qty, income))
                    conn.commit()
                    st.success(f"Sold {sell_qty}x {p_name} for Rs. {income:,.2f}")
                else:
                    st.error("Not enough stock!")
            else:
                st.error("Item not found in inventory.")

# ==========================================
# PAGE 2: INVENTORY (Adding/Viewing Stock)
# ==========================================
elif menu == "📦 Inventory":
    st.header("Inventory Management")
    
    with st.expander("Add New Part"):
        with st.form("add_form", clear_on_submit=True):
            b = st.text_input("Barcode")
            n = st.text_input("Part Name")
            cat = st.selectbox("Category", ["Oil", "Tires", "Brakes", "Other"])
            q = st.number_input("Quantity", min_value=1)
            p = st.number_input("Price (Rs.)")
            if st.form_submit_button("Save"):
                c.execute("INSERT INTO parts (barcode, part_name, category, quantity, price) VALUES (?,?,?,?,?)", (b, n, cat, q, p))
                conn.commit()
                st.success("Part Added!")

    st.subheader("Current Stock")
    df = pd.read_sql("SELECT * FROM parts", conn)
    st.dataframe(df, use_container_width=True)

# ==========================================
# PAGE 3: SALES HISTORY (The Income Tracker)
# ==========================================
elif menu == "📈 Sales History":
    st.header("Garage Performance")
    
    # Load all sales data from the 'sales' table
    sales_df = pd.read_sql("SELECT * FROM sales ORDER BY sale_date DESC", conn)
    
    if not sales_df.empty:
        # Calculate Total Revenue
        total_rev = sales_df['total_income'].sum()
        st.metric("Total Revenue", f"Rs. {total_rev:,.2f}")
        
        # Show the list of every single sale ever made
        st.subheader("Detailed History")
        st.dataframe(sales_df, use_container_width=True)
        
        # Download button to save history as an Excel file
        st.download_button("Download Report (CSV)", sales_df.to_csv(index=False), "garage_report.csv")
    else:
        st.info("No sales have been recorded yet.")

conn.close()