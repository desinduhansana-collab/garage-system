import streamlit as st
import sqlite3
from datetime import datetime

# --- System Configuration ---
# You can change this number! If stock hits this number, the alarm sounds.
LOW_STOCK_THRESHOLD = 3 

# --- 1. Database Setup ---
conn = sqlite3.connect('garage_inventory.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER NOT NULL,
        price REAL
    )
''')
try:
    c.execute('ALTER TABLE parts ADD COLUMN barcode TEXT')
except sqlite3.OperationalError:
    pass 

c.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_name TEXT NOT NULL,
        quantity_sold INTEGER NOT NULL,
        total_price REAL NOT NULL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# --- 2. The Web Page ---
st.title("🏍️ Desu's Garage Management")

# ==========================================
# NEW SECTION: SMART ALERTS
# ==========================================
# We check the database specifically for items running out
c.execute("SELECT part_name, quantity FROM parts WHERE quantity <= ?", (LOW_STOCK_THRESHOLD,))
low_stock_items = c.fetchall()

# If the list is not empty, trigger the red warning boxes!
if len(low_stock_items) > 0:
    st.error("⚠️ **LOW STOCK ALERT** ⚠️")
    for item in low_stock_items:
        st.warning(f"Order more: **{item[0]}** (Only {item[1]} left in stock!)")

st.divider()

# ==========================================
# SECTION: CHECKOUT / SELL PARTS
# ==========================================
st.subheader("🛒 Checkout / Sell Parts")
with st.form("sell_part_form", clear_on_submit=True):
    sell_barcode = st.text_input("Scan Barcode / Enter Part Number")
    sell_qty = st.number_input("Quantity to Sell", min_value=1, value=1, step=1)
    sell_submitted = st.form_submit_button("Complete Sale")

    if sell_submitted:
        if sell_barcode != "":
            c.execute("SELECT id, part_name, quantity, price FROM parts WHERE barcode = ?", (sell_barcode,))
            part = c.fetchone() 

            if part:
                part_id = part[0]
                part_name = part[1]
                current_qty = part[2]
                part_price = part[3] 

                if current_qty >= sell_qty:
                    new_qty = current_qty - sell_qty
                    c.execute("UPDATE parts SET quantity = ? WHERE id = ?", (new_qty, part_id))
                    
                    total_sale_value = part_price * sell_qty
                    c.execute("INSERT INTO sales (part_name, quantity_sold, total_price, sale_date) VALUES (?, ?, ?, datetime('now', 'localtime'))", 
                              (part_name, sell_qty, total_sale_value))
                    conn.commit()
                    
                    # Check if this sale just triggered a low stock warning!
                    if new_qty <= LOW_STOCK_THRESHOLD:
                        st.success(f"✅ Sale Successful! Sold {sell_qty}x {part_name}.")
                        st.error(f"🚨 Heads up! {part_name} is now low on stock ({new_qty} left).")
                    else:
                        st.success(f"✅ Sale Successful! Sold {sell_qty}x {part_name} for Rs.{total_sale_value:.2f}.")
                else:
                    st.error(f"❌ Not enough stock! You only have {current_qty} of {part_name} left.")
            else:
                st.error("❌ Barcode not found in the system.")
        else:
            st.warning("Please enter or scan a barcode to sell.")

# ==========================================
# SECTION: ADD NEW PARTS
# ==========================================
with st.expander("➕ Add New Parts to Inventory"): 
    with st.form("add_part_form", clear_on_submit=True):
        barcode = st.text_input("Barcode / Part Number")
        part_name = st.text_input("Part Name (e.g., Honda Brake Pads)")
        category = st.selectbox("Category", ["Engine Oil", "Brakes", "Tires", "Engine Parts", "Accessories", "Other"])
        quantity = st.number_input("Quantity to Add", min_value=1, value=1, step=1)
        price = st.number_input("Price (Rs.)", min_value=0.0, format="%f")
        add_submitted = st.form_submit_button("Save Part to Inventory")

        if add_submitted and part_name != "":
            c.execute("SELECT id, quantity FROM parts WHERE barcode = ? AND barcode != ''", (barcode,))
            existing_part = c.fetchone()
            if existing_part:
                new_total = existing_part[1] + quantity
                c.execute("UPDATE parts SET quantity = ? WHERE id = ?", (new_total, existing_part[0]))
                st.success(f"Updated existing part! Added {quantity} more to stock.")
            else:
                c.execute("INSERT INTO parts (barcode, part_name, category, quantity, price) VALUES (?, ?, ?, ?, ?)", 
                          (barcode, part_name, category, quantity, price))
                st.success(f"Successfully added {quantity}x {part_name} to the system!")
            conn.commit()

# ==========================================
# SECTION: VIEW INVENTORY
# ==========================================
st.subheader("📦 Current Inventory")
c.execute("SELECT * FROM parts")
rows = c.fetchall()

if len(rows) > 0:
    inventory_data = []
    for row in rows:
        qty = row[3]
        # Assign a visual status based on the threshold
        if qty <= LOW_STOCK_THRESHOLD:
            status = "🔴 Low Stock"
        else:
            status = "🟢 Good"
            
        inventory_data.append({
            "Status": status,
            "Barcode": row[5] if len(row) > 5 else "N/A", 
            "Part Name": row[1], 
            "Category": row[2], 
            "Qty": qty, 
            "Price (Rs.)": row[4]
        })
    st.dataframe(inventory_data, use_container_width=True)
else:
    st.info("Your inventory is empty.")

# ==========================================
# SECTION: SALES HISTORY & INCOME
# ==========================================
st.subheader("📈 Sales History")

c.execute("SELECT SUM(total_price) FROM sales")
total_income = c.fetchone()[0]
if total_income:
    st.metric(label="Total Garage Revenue", value=f"Rs. {total_income:,.2f}")
else:
    st.metric(label="Total Garage Revenue", value="Rs. 0.00")

c.execute("SELECT part_name, quantity_sold, total_price, sale_date FROM sales ORDER BY sale_date DESC")
sales_rows = c.fetchall()

if len(sales_rows) > 0:
    sales_data = []
    for row in sales_rows:
        sales_data.append({"Date & Time": row[3], "Part Sold": row[0], "Qty": row[1], "Income (Rs.)": row[2]})
    st.dataframe(sales_data, use_container_width=True)
else:
    st.info("No sales recorded yet.")

conn.close()