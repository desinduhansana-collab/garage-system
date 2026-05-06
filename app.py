import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- System Configuration ---
LOW_STOCK_THRESHOLD = 3 
# 👇 PASTE YOUR GOOGLE SHEET LINK INSIDE THESE QUOTES 👇
SHEET_URL = "https://docs.google.com/spreadsheets/d/11JWwxG-HqdYAc_Fwz5QW5AntfEXkMHtmo9Eq6WAnCbI/edit?gid=0#gid=0"

st.title("🏍️ Desu's Garage Management")
st.caption("🟢 Live Cloud Database Connected")

# --- 1. Connect to Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch the live data (Now it knows exactly which sheet to read!)
inventory_df = conn.read(spreadsheet=SHEET_URL, worksheet="Inventory", ttl=0).dropna(how="all")
sales_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sales", ttl=0).dropna(how="all")

# ==========================================
# SECTION: SMART ALERTS
# ==========================================
inventory_df['Quantity'] = pd.to_numeric(inventory_df['Quantity'], errors='coerce').fillna(0)
low_stock_df = inventory_df[inventory_df['Quantity'] <= LOW_STOCK_THRESHOLD]

if not low_stock_df.empty:
    st.error("⚠️ **LOW STOCK ALERT** ⚠️")
    for index, row in low_stock_df.iterrows():
        st.warning(f"Order more: **{row['Part_Name']}** (Only {int(row['Quantity'])} left!)")

st.divider()

# ==========================================
# SECTION: CHECKOUT / SELL PARTS
# ==========================================
st.subheader("🛒 Checkout / Sell Parts")
with st.form("sell_part_form", clear_on_submit=True):
    sell_barcode = st.text_input("Scan Barcode / Enter Part Number")
    sell_qty = st.number_input("Quantity to Sell", min_value=1, value=1, step=1)
    sell_submitted = st.form_submit_button("Complete Sale")

    if sell_submitted and sell_barcode != "":
        match = inventory_df[inventory_df['Barcode'].astype(str) == str(sell_barcode)]
        
        if not match.empty:
            idx = match.index[0] 
            part_name = inventory_df.at[idx, 'Part_Name']
            current_qty = inventory_df.at[idx, 'Quantity']
            price = float(inventory_df.at[idx, 'Price'])

            if current_qty >= sell_qty:
                new_qty = current_qty - sell_qty
                inventory_df.at[idx, 'Quantity'] = new_qty
                # Tell it which sheet to update!
                conn.update(spreadsheet=SHEET_URL, worksheet="Inventory", data=inventory_df)
                
                total_income = price * sell_qty
                new_sale = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Part_Name": part_name,
                    "Qty_Sold": sell_qty,
                    "Income": total_income
                }])
                updated_sales = pd.concat([sales_df, new_sale], ignore_index=True)
                # Tell it which sheet to update!
                conn.update(spreadsheet=SHEET_URL, worksheet="Sales", data=updated_sales)
                
                st.success(f"✅ Sold {sell_qty}x {part_name} for Rs.{total_income:.2f}.")
                st.rerun() 
            else:
                st.error(f"❌ Not enough stock! You only have {int(current_qty)} left.")
        else:
            st.error("❌ Barcode not found.")

# ==========================================
# SECTION: ADD NEW PARTS
# ==========================================
with st.expander("➕ Add New Parts to Inventory"): 
    with st.form("add_part_form", clear_on_submit=True):
        barcode = st.text_input("Barcode / Part Number")
        part_name = st.text_input("Part Name")
        category = st.selectbox("Category", ["Engine Oil", "Brakes", "Tires", "Engine Parts", "Accessories", "Other"])
        quantity = st.number_input("Quantity to Add", min_value=1, value=1, step=1)
        price = st.number_input("Price (Rs.)", min_value=0.0, format="%f")
        add_submitted = st.form_submit_button("Save Part")

        if add_submitted and part_name != "":
            match = inventory_df[inventory_df['Barcode'].astype(str) == str(barcode)]
            
            if not match.empty and barcode != "":
                idx = match.index[0]
                inventory_df.at[idx, 'Quantity'] += quantity
                st.success(f"Added {quantity} more to existing stock!")
            else:
                new_id = len(inventory_df) + 1
                new_item = pd.DataFrame([{
                    "ID": new_id, "Barcode": str(barcode), "Part_Name": part_name, 
                    "Category": category, "Quantity": quantity, "Price": price
                }])
                inventory_df = pd.concat([inventory_df, new_item], ignore_index=True)
                st.success(f"Added {part_name} to inventory!")
            
            # Tell it which sheet to update!
            conn.update(spreadsheet=SHEET_URL, worksheet="Inventory", data=inventory_df)
            st.rerun()

# ==========================================
# SECTION: VIEW DATA
# ==========================================
st.subheader("📦 Current Inventory")
if not inventory_df.empty:
    display_df = inventory_df.copy()
    display_df.insert(0, "Status", ["🔴 Low" if q <= LOW_STOCK_THRESHOLD else "🟢 Good" for q in display_df['Quantity']])
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Inventory is empty.")

st.divider()
st.subheader("📈 Sales History")
if not sales_df.empty:
    sales_df['Income'] = pd.to_numeric(sales_df['Income'], errors='coerce').fillna(0)
    total_rev = sales_df['Income'].sum()
    st.metric(label="Total Garage Revenue", value=f"Rs. {total_rev:,.2f}")
    st.dataframe(sales_df.sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
else:
    st.metric(label="Total Garage Revenue", value="Rs. 0.00")
    st.info("No sales recorded yet.")