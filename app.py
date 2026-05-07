import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import hashlib

MASTER_EMAIL = "desinduhansana@gmail.com"

SHEET_URL = "https://docs.google.com/spreadsheets/d/11JWwxG-HqdYAc_FwZ5QW5AntfEXkMHtmo9Eq6WAnCbl/edit?gid=0#gid=0"

st.set_page_config(
    page_title="Desu's Garage Management",
    layout="wide"
)

# ---------------- CONNECTION ---------------- #
conn = st.connection("gsheets", type=GSheetsConnection)


# ---------------- HELPERS ---------------- #
def make_hashes(password):
    return hashlib.sha256(str(password).encode()).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == str(hashed_text)


def get_data(worksheet):
    """
    Safely load worksheet data.
    Returns empty dataframe if sheet is empty or missing.
    """
    try:
        data = conn.read(
            spreadsheet=SHEET_URL,
            worksheet=worksheet,
            ttl=0
        )

        if data is None:
            return pd.DataFrame()

        return data.dropna(how="all")

    except Exception as e:
        st.error(f"Error loading '{worksheet}' sheet: {e}")
        return pd.DataFrame()


def update_sheet(worksheet, dataframe):
    """
    Safely update worksheet.
    """
    try:
        conn.update(
            spreadsheet=SHEET_URL,
            worksheet=worksheet,
            data=dataframe
        )
        return True
    except Exception as e:
        st.error(f"Error updating '{worksheet}' sheet: {e}")
        return False


# ---------------- SESSION ---------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""


# ---------------- LOGIN PAGE ---------------- #
if not st.session_state.logged_in:

    st.title("🔐 Garage Management Login")

    tab1, tab2 = st.tabs(["Login", "Register"])

    users_df = get_data("Users")

    # Ensure required columns exist
    required_user_columns = ["email", "password", "status"]

    for col in required_user_columns:
        if col not in users_df.columns:
            users_df[col] = []

    # ---------- LOGIN ---------- #
    with tab1:

        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")

        if st.button("Login"):

            if not email or not pw:
                st.warning("Please enter email and password.")
            else:
                user_row = users_df[
                    users_df["email"].astype(str).str.lower() == email.lower()
                ]

                if not user_row.empty:

                    stored_pw = user_row.iloc[0]["password"]
                    status = user_row.iloc[0]["status"]

                    if check_hashes(pw, stored_pw):

                        if status == "Approved" or email.lower() == MASTER_EMAIL.lower():

                            st.session_state.logged_in = True
                            st.session_state.user_email = email

                            st.success("Login successful!")
                            st.rerun()

                        else:
                            st.warning(
                                "⏳ Access Pending. Desu needs to approve your email."
                            )

                    else:
                        st.error("Invalid Password")

                else:
                    st.error("User not found")

    # ---------- REGISTER ---------- #
    with tab2:

        new_email = st.text_input("New Staff Email")
        new_pw = st.text_input("New Password", type="password")

        if st.button("Request Access"):

            if not new_email or not new_pw:
                st.warning("Please fill all fields.")

            elif new_email.lower() in users_df["email"].astype(str).str.lower().values:
                st.error("Email already registered.")

            else:
                status = (
                    "Approved"
                    if new_email.lower() == MASTER_EMAIL.lower()
                    else "Pending"
                )

                new_user = pd.DataFrame(
                    [
                        {
                            "email": new_email,
                            "password": make_hashes(new_pw),
                            "status": status,
                        }
                    ]
                )

                updated_users = pd.concat(
                    [users_df, new_user],
                    ignore_index=True
                )

                if update_sheet("Users", updated_users):
                    st.success("Request Sent! Wait for approval.")


# ---------------- MAIN APP ---------------- #
else:

    st.sidebar.title(f"👤 {st.session_state.user_email}")

    # ---------- APPROVAL CENTER ---------- #
    if st.session_state.user_email.lower() == MASTER_EMAIL.lower():

        with st.sidebar.expander("⭐ Approval Center"):

            users_df = get_data("Users")

            if "status" not in users_df.columns:
                users_df["status"] = []

            pending = users_df[users_df["status"] == "Pending"]

            if not pending.empty:

                to_approve = st.selectbox(
                    "Select Staff to Approve:",
                    pending["email"]
                )

                if st.button("Approve Now"):

                    users_df.loc[
                        users_df["email"] == to_approve,
                        "status"
                    ] = "Approved"

                    if update_sheet("Users", users_df):
                        st.success(f"{to_approve} Approved!")
                        st.rerun()

            else:
                st.write("No pending requests.")

    # ---------- NAVIGATION ---------- #
    page = st.sidebar.radio(
        "Navigation",
        ["🛒 Checkout", "📦 Inventory (Stock)", "📈 Profits"]
    )

    # =========================================================
    # CHECKOUT PAGE
    # =========================================================
    if page == "🛒 Checkout":

        st.header("🛒 Sales Checkout")

        st.subheader("Scan Barcode")
        st.camera_input("Point phone camera at barcode")

        with st.form("sale_form", clear_on_submit=True):

            bc = st.text_input("Enter Barcode")
            qty = st.number_input("Quantity", min_value=1, value=1)

            if st.form_submit_button("Complete Sale"):

                inv_df = get_data("Inventory")
                sales_df = get_data("Sales")

                required_inventory_cols = [
                    "barcode",
                    "part_name",
                    "quantity",
                    "cost_price",
                    "selling_price"
                ]

                for col in required_inventory_cols:
                    if col not in inv_df.columns:
                        inv_df[col] = []

                if "Income" not in sales_df.columns:
                    sales_df["Income"] = []

                item = inv_df[
                    inv_df["barcode"].astype(str) == str(bc)
                ]

                if item.empty:
                    st.error("Barcode not found in database.")

                else:

                    idx = item.index[0]
                    stock = int(inv_df.at[idx, "quantity"])

                    if stock < qty:
                        st.error("Not enough stock available.")

                    else:

                        inv_df.at[idx, "quantity"] = stock - qty

                        sale_income = (
                            float(inv_df.at[idx, "selling_price"]) * qty
                        )

                        new_sale = pd.DataFrame(
                            [
                                {
                                    "Date": datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                    "Part_Name": inv_df.at[idx, "part_name"],
                                    "Income": sale_income,
                                }
                            ]
                        )

                        updated_sales = pd.concat(
                            [sales_df, new_sale],
                            ignore_index=True
                        )

                        inventory_updated = update_sheet(
                            "Inventory",
                            inv_df
                        )

                        sales_updated = update_sheet(
                            "Sales",
                            updated_sales
                        )

                        if inventory_updated and sales_updated:
                            st.success("✅ Sale Successful!")
                            st.rerun()

    # =========================================================
    # INVENTORY PAGE
    # =========================================================
    elif page == "📦 Inventory (Stock)":

        st.header("📦 Stock Management")

        st.subheader("Scan to Add New Stock")
        st.camera_input("Scan item to restock")

        with st.form("inv_form", clear_on_submit=True):

            bc = st.text_input("Barcode")
            name = st.text_input("Item Name")

            qty = st.number_input(
                "Qty to Add",
                min_value=1,
                value=1
            )

            cost = st.number_input(
                "Cost Price",
                min_value=0.0,
                value=0.0
            )

            sell = st.number_input(
                "Selling Price",
                min_value=0.0,
                value=0.0
            )

            if st.form_submit_button("Save to Stock"):

                if not bc or not name:
                    st.warning("Please enter barcode and item name.")

                else:

                    inv_df = get_data("Inventory")

                    required_inventory_cols = [
                        "barcode",
                        "part_name",
                        "quantity",
                        "cost_price",
                        "selling_price"
                    ]

                    for col in required_inventory_cols:
                        if col not in inv_df.columns:
                            inv_df[col] = []

                    match = inv_df[
                        inv_df["barcode"].astype(str) == str(bc)
                    ]

                    if not match.empty:

                        idx = match.index[0]

                        current_qty = int(inv_df.at[idx, "quantity"])

                        inv_df.at[idx, "quantity"] = current_qty + qty

                        inv_df.at[idx, "cost_price"] = cost
                        inv_df.at[idx, "selling_price"] = sell

                    else:

                        new_item = pd.DataFrame(
                            [
                                {
                                    "barcode": bc,
                                    "part_name": name,
                                    "quantity": qty,
                                    "cost_price": cost,
                                    "selling_price": sell,
                                }
                            ]
                        )

                        inv_df = pd.concat(
                            [inv_df, new_item],
                            ignore_index=True
                        )

                    if update_sheet("Inventory", inv_df):
                        st.success("✅ Stock Successfully Updated!")
                        st.rerun()

    # =========================================================
    # PROFITS PAGE
    # =========================================================
    elif page == "📈 Profits":

        if st.session_state.user_email.lower() == MASTER_EMAIL.lower():

            st.header("📈 Financial Report")

            sales_df = get_data("Sales")

            if sales_df.empty or "Income" not in sales_df.columns:
                total_revenue = 0
            else:
                sales_df["Income"] = pd.to_numeric(
                    sales_df["Income"],
                    errors="coerce"
                ).fillna(0)

                total_revenue = sales_df["Income"].sum()

            st.metric(
                "Total Revenue",
                f"Rs. {total_revenue:,.2f}"
            )

            st.dataframe(
                sales_df,
                use_container_width=True
            )

        else:
            st.error(
                "🚫 Access Denied. Only Master Admin can see financials."
            )

    # ---------- LOGOUT ---------- #
    if st.sidebar.button("Logout"):

        st.session_state.logged_in = False
        st.session_state.user_email = ""

        st.rerun()
