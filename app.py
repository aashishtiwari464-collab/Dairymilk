import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime


# --- Folders & Files ---
if not os.path.exists("data"):
    os.makedirs("data")


USERS_FILE = "data/users.csv"       # Shopkeeper login & admin approval
FARMERS_FILE = "data/farmers.csv"   # Farmers data
MILK_FILE = "data/milk_data.csv"    # Milk collection
RATE_FILE = "data/rate_chart.csv"   # Rate chart


# --- Load or init data ---
def load_data(file, cols):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=cols)


users = load_data(USERS_FILE, ["Username","Password","ShopName","Approved"])
farmers = load_data(FARMERS_FILE, ["ShopName","FarmerID","Name","Village","Phone"])
milk_data = load_data(MILK_FILE, ["ShopName","Date","FarmerID","Session","Litres","Fat","CLR","Rate","Amount"])
rate_chart = load_data(RATE_FILE, ["Fat","CLR","Rate"])


# --- Save ---
def save_data(df, file):
    df.to_csv(file, index=False)


# --- Admin login ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# --- Login ---
st.title("🐄 Dairy Billing System")


menu_option = st.radio("Choose", ["Shopkeeper Login", "Admin Login", "Register Shopkeeper"])


current_shop = None


# --- Shopkeeper Registration ---
if menu_option == "Register Shopkeeper":
    st.subheader("Register Shopkeeper")
    with st.form("reg_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        shop_name = st.text_input("Shop Name")
        submitted = st.form_submit_button("Register")
        if submitted:
            if username and password and shop_name:
                if username in users["Username"].values:
                    st.error("Username already exists!")
                else:
                    users.loc[len(users)] = [username,password,shop_name,"No"]
                    save_data(users, USERS_FILE)
                    st.success("Registered! Waiting for admin approval.")
            else:
                st.warning("Fill all fields.")


# --- Admin Login ---
elif menu_option == "Admin Login":
    st.subheader("Admin Login")
    with st.form("admin_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username==ADMIN_USERNAME and password==ADMIN_PASSWORD:
                st.success("Admin logged in")
                st.subheader("Approve Shopkeepers")
                pending = users[users["Approved"]=="No"]
                for idx,row in pending.iterrows():
                    st.write(f"{row['Username']} ({row['ShopName']})")
                    approve = st.button(f"Approve {row['Username']}", key=idx)
                    if approve:
                        users.at[idx,"Approved"]="Yes"
                        save_data(users, USERS_FILE)
                        st.success(f"{row['Username']} approved")
            else:
                st.error("Invalid admin credentials")


# --- Shopkeeper Login ---
elif menu_option == "Shopkeeper Login":
    st.subheader("Shopkeeper Login")
    with st.form("shop_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            match = users[(users["Username"]==username) & (users["Password"]==password) & (users["Approved"]=="Yes")]
            if not match.empty:
                current_shop = match["ShopName"].values[0]
                st.success(f"Logged in as {current_shop}")
            else:
                st.error("Invalid credentials or not approved")


# --- Shopkeeper App ---
if current_shop:
    menu = st.sidebar.radio("Menu", ["Farmer Management","Milk Entry","Import Data","Rate Chart","Billing"])


    # --- Farmer Management ---
    if menu=="Farmer Management":
        st.header("👨‍🌾 Farmer Management")
        with st.form("add_farmer"):
            fid = st.text_input("Farmer ID")
            name = st.text_input("Farmer Name")
            village = st.text_input("Village")
            phone = st.text_input("Phone")
            submitted = st.form_submit_button("Add Farmer")
            if submitted and fid and name:
                farmers.loc[len(farmers)] = [current_shop,fid,name,village,phone]
                save_data(farmers,FARMERS_FILE)
                st.success("Farmer added!")
        st.write("### Farmer List")
        st.dataframe(farmers[farmers["ShopName"]==current_shop])


    # --- Milk Entry ---
    elif menu=="Milk Entry":
        st.header("🍼 Milk Collection Entry")
        shop_farmers = farmers[farmers["ShopName"]==current_shop]
        if shop_farmers.empty:
            st.warning("Add farmers first")
        else:
            with st.form("milk_entry"):
                date = st.date_input("Date", datetime.today())
                farmer = st.selectbox("Select Farmer", shop_farmers["FarmerID"]+" - "+shop_farmers["Name"])
                session = st.radio("Session", ["Morning","Evening"])
                litres = st.number_input("Litres",0.0)
                fat = st.number_input("Fat",0.0)
                clr = st.number_input("CLR",0.0)
                # Rate lookup
                rate=0; amount=0
                match = rate_chart[(rate_chart["Fat"]==fat)&(rate_chart["CLR"]==clr)]
                if not match.empty:
                    rate=float(match["Rate"].values[0])
                    amount=litres*rate
                submitted = st.form_submit_button("Save Entry")
                if submitted:
                    milk_data.loc[len(milk_data)] = [current_shop,date,farmer.split(" - ")[0],session,litres,fat,clr,rate,amount]
                    save_data(milk_data,MILK_FILE)
                    st.success("Milk entry saved!")
        st.write("### Milk Data")
        st.dataframe(milk_data[milk_data["ShopName"]==current_shop])


    # --- Import Data ---
    elif menu == "Import Data":
         st.header("📥 Import CSV/Excel")
        file = st.file_uploader("Upload CSV/Excel for Farmers or Milk", type=["csv", "xlsx"])
        if file:
            df_import = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)

        if "FarmerID" in df_import.columns:
            global farmers   # 👈 must come first
            df_import["ShopName"] = current_shop  
            farmers = pd.concat([farmers, df_import], ignore_index=True)
            save_data(farmers, FARMERS_FILE)
            st.success("Farmers imported!")

        elif "Litres" in df_import.columns:
            global milk_data   # 👈 must come first
            df_import["ShopName"] = current_shop
            milk_data = pd.concat([milk_data, df_import], ignore_index=True)
            save_data(milk_data, MILK_FILE)
            st.success("Milk data imported!")

        else:
            st.error("Unknown file format")


    # --- Rate Chart ---
    elif menu=="Rate Chart":
        global rate_chart
        st.header("📊 Rate Chart Upload")
        file = st.file_uploader("Upload Rate Chart CSV (Fat, CLR, Rate)", type=["csv"])
        if file:
            rate_chart=pd.read_csv(file)
            save_data(rate_chart,RATE_FILE)
            st.success("Rate chart updated!")
        st.write(rate_chart)


    # --- Billing ---
    elif menu=="Billing":
        st.header("💰 Generate Invoice")
        shop_milk = milk_data[milk_data["ShopName"]==current_shop]
        if shop_milk.empty:
            st.warning("No milk data")
        else:
            pdf=FPDF('L','mm','A4')
            pdf.add_page()
            pdf.set_font("Helvetica","B",16)
            pdf.cell(0,10,f"{current_shop} - Monthly Milk Bill",ln=True,align='C')
            pdf.set_font("Helvetica","",12)
            pdf.cell(0,10,f"Date: {datetime.today().strftime('%Y-%m-%d')}",ln=True)
            pdf.ln(5)
            headers=["Farmer","Session","Litres","Fat","CLR","Rate","Amount"]
            widths=[40,30,25,20,20,20,25]
            for i,h in enumerate(headers): pdf.cell(widths[i],8,h,border=1,align='C')
            pdf.ln()
            for _,row in shop_milk.iterrows():
                pdf.cell(widths[0],8,str(row["FarmerID"]),border=1,align='C')
                pdf.cell(widths[1],8,str(row["Session"]),border=1,align='C')
                pdf.cell(widths[2],8,str(row["Litres"]),border=1,align='C')
                pdf.cell(widths[3],8,str(row["Fat"]),border=1,align='C')
                pdf.cell(widths[4],8,str(row["CLR"]),border=1,align='C')
                pdf.cell(widths[5],8,str(row["Rate"]),border=1,align='C')
                pdf.cell(widths[6],8,str(row["Amount"]),border=1,align='C')
                pdf.ln()
            filename = f"data/{current_shop}_monthly_bill.pdf"
            pdf.output(filename)
            st.success(f"Invoice generated: {filename}")
            st.download_button("Download Invoice", filename)
