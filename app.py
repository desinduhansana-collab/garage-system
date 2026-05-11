import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
import io

# ---------------- CONFIGURATION ---------------- #
MASTER_EMAIL = "desinduhansana@gmail.com"
MASTER_PASSWORD = "admin"
STAFF_EMAIL = "staff@garage.com"
STAFF_PASSWORD = "staff"
SHEET_URL = "https://docs.google.com/spreadsheets/d/11JWwxG-HqdYAc_Fwz5QW5AntfEXkMHtmo9Eq6WAnCbI/edit?gid=0#gid=0"

st.set_page_config(page_title="Desu's Garage", layout="wide", page_icon="🔧")

# ---------------- CUSTOM CSS ---------------- #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #0f1117; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #16192a 100%);
        border-right: 1px solid #2d3154;
    }
    [data-testid="stSidebar"] * { color: #e0e6ff !important; }
    [data-testid="stSidebar"] .stRadio label {
        background: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 10px;
        padding: 10px 16px !important;
        margin: 4px 0 !important;
        cursor: pointer;
        transition: all 0.2s;
        display: block;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(99,102,241,0.2);
        border-color: rgba(99,102,241,0.4);
    }

    .card {
        background: #1e2130;
        border: 1px solid #2d3154;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 20px;
    }
    .page-title { font-size: 28px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }
    .page-subtitle { font-size: 14px; color: #6b7280; margin-bottom: 28px; }

    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #252840 100%);
        border: 1px solid #2d3154;
        border-radius: 14px;
        padding: 22px 24px;
        text-align: center;
    }
    .metric-label { font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #ffffff; }
    .metric-revenue { border-top: 3px solid #6366f1; }
    .metric-cost    { border-top: 3px solid #f59e0b; }
    .metric-profit  { border-top: 3px solid #10b981; }

    .stTextInput input, .stNumberInput input {
        background: #12141f !important;
        border: 1px solid #2d3154 !important;
        border-radius: 10px !important;
        color: #e0e6ff !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }
    .stTextInput label, .stNumberInput label { color: #9ca3af !important; font-size: 13px !important; font-weight: 500 !important; }

    .stFormSubmitButton button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 28px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        width: 100% !important;
        margin-top: 8px !important;
    }
    .stFormSubmitButton button:hover { opacity: 0.9 !important; }

    [data-testid="stSidebar"] .stButton button {
        background: rgba(99,102,241,0.12) !important;
        color: #a5b4fc !important;
        border: 1px solid rgba(99,102,241,0.25) !important;
        border-radius: 10px !important;
        width: 100% !important;
        padding: 10px !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] .stButton button:hover { background: rgba(99,102,241,0.25) !important; }
    [data-testid="stSidebar"] .stButton:last-child button {
        background: rgba(239,68,68,0.1) !important;
        color: #f87171 !important;
        border-color: rgba(239,68,68,0.25) !important;
    }

    .sidebar-brand { display: flex; align-items: center; gap: 10px; padding: 8px 0 24px 0; border-bottom: 1px solid #2d3154; margin-bottom: 20px; }
    .sidebar-brand-icon { font-size: 28px; }
    .sidebar-brand-text { font-size: 16px; font-weight: 700; color: #ffffff; }
    .sidebar-brand-sub  { font-size: 11px; color: #6b7280; }
    .sidebar-user { background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 10px 14px; margin-bottom: 20px; }
    .sidebar-user-role  { font-size: 11px; color: #6366f1; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .sidebar-user-email { font-size: 13px; color: #e0e6ff; margin-top: 2px; }
    .section-label { font-size: 11px; font-weight: 600; color: #4b5563; text-transform: uppercase; letter-spacing: 0.8px; margin: 16px 0 8px 0; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONNECTION ---------------- #
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------- HELPERS ---------------- #
def get_data(worksheet):
    try:
        data = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl=0)
        if data is None:
            return pd.DataFrame()
        return data.dropna(how="all")
    except Exception as e:
        st.error(f"Error loading '{worksheet}' sheet: {e}")
        return pd.DataFrame()

def update_sheet(worksheet, dataframe):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=worksheet, data=dataframe)
        return True
    except Exception as e:
        st.error(f"Error updating '{worksheet}' sheet: {e}")
        return False

def normalize_bc(s):
    return str(s).strip().replace('.0', '')

def decode_barcode(image_bytes):
    """Decode a barcode from image bytes. Returns the barcode string or None."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        results = decode(img)
        if results:
            return results[0].data.decode("utf-8")
        # Retry with grayscale for better detection
        gray = img.convert("L")
        results = decode(gray)
        if results:
            return results[0].data.decode("utf-8")
        return None
    except Exception:
        return None

# ---------------- SESSION ---------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "is_master" not in st.session_state:
    st.session_state.is_master = False

# Persist login across refreshes using query params
if not st.session_state.logged_in:
    params = st.query_params
    if params.get("user") and params.get("role"):
        st.session_state.logged_in = True
        st.session_state.user_email = params["user"]
        st.session_state.is_master = params["role"] == "admin"

# Save login state to query params when logged in
if st.session_state.logged_in:
    st.query_params["user"] = st.session_state.user_email
    st.query_params["role"] = "admin" if st.session_state.is_master else "staff" 

# ================================================================
# LOGIN PAGE
# ================================================================
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center; padding: 60px 0 30px 0;">
            <div style="font-size:56px">🔧</div>
            <div style="font-size:26px; font-weight:700; color:#ffffff; margin-top:8px">Desu's Garage</div>
            <div style="font-size:14px; color:#6b7280; margin-top:4px">Management System</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email  = st.text_input("Email Address")
            pw     = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In →")

            if submit:
                email_clean = email.lower().strip()
                if email_clean == MASTER_EMAIL.lower() and pw == MASTER_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email_clean
                    st.session_state.is_master = True
                    st.rerun()
                elif email_clean == STAFF_EMAIL.lower() and pw == STAFF_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email_clean
                    st.session_state.is_master = False
                    st.rerun()
                else:
                    st.error("❌ Invalid email or password.")

# ================================================================
# MAIN APP
# ================================================================
else:
    role_label = "Admin" if st.session_state.is_master else "Staff"
    role_icon  = "⭐" if st.session_state.is_master else "🛠️"

    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🔧</div>
            <div>
                <div class="sidebar-brand-text">Desu's Garage</div>
                <div class="sidebar-brand-sub">Management System</div>
            </div>
        </div>
        <div class="sidebar-user">
            <div class="sidebar-user-role">{role_icon} {role_label}</div>
            <div class="sidebar-user-email">{st.session_state.user_email}</div>
        </div>
        <div class="section-label">Navigation</div>
        """, unsafe_allow_html=True)

        nav_options = ["🛒  Checkout", "📦  Inventory"]
        if st.session_state.is_master:
            nav_options.append("📈  Profits")

        page = st.radio("", nav_options, label_visibility="collapsed")

        st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
        if st.button("🔄  Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        if st.button("🚪  Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.session_state.is_master = False
            st.query_params.clear()
            st.rerun()

    # ================================================================
    # CHECKOUT PAGE
    # ================================================================
    if page == "🛒  Checkout":
        st.markdown('<div class="page-title">🛒 Sales Checkout</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Scan or enter a barcode to complete a sale</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            use_cam = st.toggle("📷  Enable Camera Scanner")

            scanned_bc = ""
            if use_cam:
                cam_img = st.camera_input("Point camera at barcode")
                if cam_img is not None:
                    decoded = decode_barcode(cam_img.getvalue())
                    if decoded:
                        scanned_bc = decoded
                        st.success(f"✅ Barcode detected: **{decoded}**")
                    else:
                        st.warning("⚠️ No barcode detected — try better lighting or move closer.")

            with st.form("sale_form", clear_on_submit=True):
                bc  = st.text_input("Barcode", value=scanned_bc, placeholder="Scan or type barcode...")
                qty = st.number_input("Quantity", min_value=1, value=1)
                st.markdown("<br>", unsafe_allow_html=True)

                if st.form_submit_button("✅  Complete Sale"):
                    inv_df   = get_data("Inventory")
                    sales_df = get_data("Sales")

                    if sales_df.empty:
                        sales_df = pd.DataFrame(columns=["Date","Part_Name","Quantity","Income","Cost","Profit"])
                    else:
                        for c in ["Date","Part_Name","Quantity","Income","Cost","Profit"]:
                            if c not in sales_df.columns:
                                sales_df[c] = []

                    if not bc:
                        st.warning("⚠️ Please enter a barcode.")
                    else:
                        item = inv_df[inv_df["barcode"].apply(normalize_bc) == normalize_bc(bc)]
                        if item.empty:
                            st.error("❌ Barcode not found in inventory.")
                        else:
                            idx   = item.index[0]
                            stock = int(inv_df.at[idx, "quantity"])
                            if stock < qty:
                                st.error(f"❌ Only {stock} units in stock.")
                            else:
                                inv_df.at[idx, "quantity"] = stock - qty
                                sale_income = float(str(inv_df.at[idx, "selling_price"]).replace(',','') or 0) * qty
                                cost_price  = float(str(inv_df.at[idx, "cost_price"]).replace(',','') or 0) * qty
                                profit      = sale_income - cost_price

                                new_sale = pd.DataFrame([{
                                    "Date":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Part_Name": inv_df.at[idx, "part_name"],
                                    "Quantity":  qty,
                                    "Income":    sale_income,
                                    "Cost":      cost_price,
                                    "Profit":    profit,
                                }])
                                updated_sales = pd.concat([sales_df, new_sale], ignore_index=True)

                                if update_sheet("Inventory", inv_df) and update_sheet("Sales", updated_sales):
                                    st.success(f"✅ Sale recorded! Collected **Rs. {sale_income:,.2f}** | Profit **Rs. {profit:,.2f}**")
                                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**📋 Recent Sales**")
            sales_df = get_data("Sales")
            if not sales_df.empty and "Part_Name" in sales_df.columns:
                recent = sales_df.tail(5)[["Date","Part_Name","Income"]].iloc[::-1]
                st.dataframe(recent, use_container_width=True, hide_index=True)
            else:
                st.markdown('<p style="color:#4b5563;font-size:13px">No sales yet.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ================================================================
    # INVENTORY PAGE
    # ================================================================
    elif page == "📦  Inventory":
        st.markdown('<div class="page-title">📦 Stock Management</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Add new items or restock existing ones</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1.4])

        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**➕ Add / Restock Item**")
            use_cam = st.toggle("📷  Enable Camera Scanner")

            scanned_bc = ""
            if use_cam:
                cam_img = st.camera_input("Scan item to restock")
                if cam_img is not None:
                    decoded = decode_barcode(cam_img.getvalue())
                    if decoded:
                        scanned_bc = decoded
                        st.success(f"✅ Barcode detected: **{decoded}**")
                    else:
                        st.warning("⚠️ No barcode detected — try better lighting or move closer.")

            with st.form("inv_form", clear_on_submit=True):
                bc   = st.text_input("Barcode", value=scanned_bc, placeholder="Scan or type barcode...")
                name = st.text_input("Item Name", placeholder="e.g. Brake Pad")
                c1, c2 = st.columns(2)
                qty  = c1.number_input("Qty to Add", min_value=1, value=1)
                cost = c2.number_input("Cost Price (Rs.)", min_value=0.0, value=0.0)
                sell = st.number_input("Selling Price (Rs.)", min_value=0.0, value=0.0)
                st.markdown("<br>", unsafe_allow_html=True)

                if st.form_submit_button("💾  Save to Stock"):
                    if not bc or not name:
                        st.warning("⚠️ Please enter barcode and item name.")
                    elif sell <= 0:
                        st.warning("⚠️ Selling Price must be greater than 0.")
                    else:
                        inv_df = get_data("Inventory")
                        if inv_df.empty:
                            inv_df = pd.DataFrame(columns=["barcode","part_name","quantity","cost_price","selling_price"])
                        else:
                            for c in ["barcode","part_name","quantity","cost_price","selling_price"]:
                                if c not in inv_df.columns:
                                    inv_df[c] = []

                        match = inv_df[inv_df["barcode"].apply(normalize_bc) == normalize_bc(bc)]
                        if not match.empty:
                            idx = match.index[0]
                            inv_df.at[idx, "quantity"]      = int(inv_df.at[idx, "quantity"]) + qty
                            inv_df.at[idx, "cost_price"]    = cost
                            inv_df.at[idx, "selling_price"] = sell
                            msg = f"✅ Restocked — now {int(inv_df.at[idx, 'quantity'])} units"
                        else:
                            new_item = pd.DataFrame([{"barcode":bc,"part_name":name,"quantity":qty,"cost_price":cost,"selling_price":sell}])
                            inv_df   = pd.concat([inv_df, new_item], ignore_index=True)
                            msg      = f"✅ **{name}** added to inventory"

                        if update_sheet("Inventory", inv_df):
                            st.success(msg)
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**📋 Current Stock**")
            inv_df = get_data("Inventory")
            if not inv_df.empty:
                display = inv_df[["barcode","part_name","quantity","cost_price","selling_price"]].copy()
                display.columns = ["Barcode","Part Name","Qty","Cost (Rs.)","Sell (Rs.)"]
                st.dataframe(display, use_container_width=True, hide_index=True)
            else:
                st.markdown('<p style="color:#4b5563;font-size:13px">No items in stock yet.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ================================================================
    # PROFITS PAGE (Master Only)
    # ================================================================
    elif page == "📈  Profits" and st.session_state.is_master:
        st.markdown('<div class="page-title">📈 Financial Report</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Overview of revenue, costs, and net profit</div>', unsafe_allow_html=True)

        sales_df = get_data("Sales")

        if sales_df.empty or "Income" not in sales_df.columns:
            st.info("💡 No sales recorded yet.")
        else:
            sales_df["Income"] = pd.to_numeric(sales_df["Income"], errors="coerce").fillna(0)
            sales_df["Cost"]   = pd.to_numeric(sales_df["Cost"],   errors="coerce").fillna(0) if "Cost"   in sales_df.columns else 0
            sales_df["Profit"] = pd.to_numeric(sales_df["Profit"], errors="coerce").fillna(0) if "Profit" in sales_df.columns else sales_df["Income"]

            total_revenue = sales_df["Income"].sum()
            total_cost    = sales_df["Cost"].sum()   if "Cost"   in sales_df.columns else 0
            total_profit  = sales_df["Profit"].sum()

            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card metric-revenue"><div class="metric-label">💰 Total Revenue</div><div class="metric-value">Rs. {total_revenue:,.0f}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card metric-cost"><div class="metric-label">📦 Total Cost</div><div class="metric-value">Rs. {total_cost:,.0f}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card metric-profit"><div class="metric-label">📈 Net Profit</div><div class="metric-value">Rs. {total_profit:,.0f}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("**📋 Sales History**")
            st.dataframe(sales_df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)