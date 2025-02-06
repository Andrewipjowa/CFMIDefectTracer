import streamlit as st
from datetime import datetime
from time import sleep
import gspread
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
import re
from dotenv import load_dotenv
import os

# Set up Google Credentials path
load_dotenv()
google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

st.set_page_config(page_title="Defect Tracer | Submit Defects", page_icon="cfm-holdings-logo.png", layout="centered", initial_sidebar_state="expanded")

if 'email' not in st.session_state:
    st.switch_page("./Login.py")  # Switch to login page if user is not logged in
    st.stop()  # Stop further execution
else:
    with st.sidebar:
        if st.button("Logout"):  # Logout functionality
            st.session_state.clear()  # Clears all session state variables
            st.info("Logged out successfully, Goodbye.")
            sleep(1)
            st.switch_page("Login.py")

# OPEN THE GOOGLE SPREADSHEET & SET UP LOCAL CACHE ######################################
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]  # Define the scope of the app (access to Sheets and Drive)
creds = Credentials.from_service_account_file(google_credentials_path, scopes=scope)  # Authenticate using the credentials file
client = gspread.authorize(creds)  # Authorize the client

# Open the spreadsheets once and store them in session state
if "sheet1" not in st.session_state:
    st.session_state["sheet1"] = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1jIOFgZWKG2mX7x27z2yVi76mPZy8xvBWSNvN5AglRiE/edit?usp=sharing").sheet1
if "sheet2" not in st.session_state:
    st.session_state["sheet2"] = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1jIOFgZWKG2mX7x27z2yVi76mPZy8xvBWSNvN5AglRiE/edit?usp=sharing").get_worksheet(1)

# Fetch records into local cache
if "sheet1_records" not in st.session_state:
    st.session_state["sheet1_records"] = st.session_state["sheet1"].get_all_records()

# Cache existing categories
if "existing_categories" not in st.session_state:
    st.session_state["existing_categories"] = st.session_state["sheet2"].col_values(1)


# Helper to generate a case number based on the current date and the number of submissions today.
def generate_case_number():
    today = datetime.now().strftime("%d/%m/%Y")  # Get today's date in DD/MM/YYYY format

    # Count how many rows have today's date in the Timestamp
    case_count = sum(1 for row in st.session_state["sheet1_records"] if row["Timestamp"][:10] == today)

    case_number = f"{today[:2]}{today[3:5]}{today[6:10]}-{case_count + 1:02d}"  # Generate case number in the format DDMMYYYY-XX
    return case_number


# Helper to append a new row to Sheet1 and update the local cache.
def submit_defect(data_to_append):
    case_number = generate_case_number()
    data_to_append.insert(0, case_number)  # Insert case number at the start of the data
    st.session_state["sheet1"].append_row(data_to_append)
    # Update local cache
    st.session_state["sheet1_records"].append(dict(zip(["Case Number", "Product", "DO Number", "Quantity", "Cost", "Type", "Description", "Action", "Submitter", "Timestamp"], data_to_append)))


# SUBMIT DEFECTS ########################################################################
def validate_inputs(option, new_category, do_number, quantity, cost, description, action, submitter, checkbox):
    errors = []
    existing_categories = st.session_state["existing_categories"]

    if option == "No Product":
        errors.append("Select a product is required.")
    if option == "Add New Product":
        if not new_category:
            errors.append("Either select a product or enter a new product name.")
        elif new_category.lower() in [category.lower() for category in existing_categories]:
            errors.append("New product name entered already exists.")
        elif new_category.lower() in ["none"]:
            errors.append("New product name is invalid.")
        elif not re.search(r"[A-Za-z0-9]", new_category):  # Ensures at least one letter or number
            errors.append("New product name cannot have no letters or numbers.")
    elif option == "No Product" and new_category:
        errors.append("Either select a product or enter a new product name.")
    if not do_number.strip():
        errors.append("DO number is required.")
    elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", do_number):
        errors.append("DO Number cannot have no letters or numbers.")
    if quantity == 0 and cost == 0:
        errors.append("Invalid quantity of defective products and unit cost.")
    elif quantity == 0:
        errors.append("Invalid quantity of defective products.")
    elif cost == 0:
        errors.append("Invalid unit cost.")
    if not description.strip() and not action.strip():
        errors.append("Descriptions of defect(s) and action(s) taken are required.")
    elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", description) and not re.match(r"^(?=.*[A-Za-z0-9]).*$", action):
        errors.append("Descriptions of defect(s) and action(s) taken cannot have no letters or numbers.")
    else:
        if not description.strip():
            errors.append("Description of defect(s) is required.")
        elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", description):
            errors.append("Description of defect(s) cannot have no letters or numbers.")
        if not action.strip():
            errors.append("Description of action(s) taken is required.")
        elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", action):
            errors.append("Description of action(s) taken cannot have no letters or numbers.")
    if not submitter.strip():
        errors.append("Submitter is required.")
    elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", submitter):
        errors.append("Submitter cannot have no letters or numbers.")
    if not checkbox:
        errors.append("Check the checkbox before submitting.")
    return errors


# Checking for duplicates
def is_duplicate_submission(data_to_check):
    today = datetime.now().strftime("%d/%m/%Y")
    for row in st.session_state["sheet1_records"]:
        row_date = datetime.strptime(row["Timestamp"], "%d/%m/%Y %H:%M:%S").strftime("%d/%m/%Y")

        if (row_date == today
                and row["Product"] == data_to_check[0]
                and row["DO Number"] == data_to_check[1]
                and row["Quantity"] == data_to_check[2]
                and row["Cost"] == data_to_check[3]
                and row["Type"] == data_to_check[4]
                and row["Description"] == data_to_check[5]
                and row["Action"] == data_to_check[6]
                and row["Submitter"] == data_to_check[7]
                and row_date == data_to_check[8][:10]):
            return True  # Duplicate found
    return False  # Duplicate not found


st.subheader("Submit A Defect")

tab1, tab2 = st.tabs(["Submit A Defect", "Help/Guide"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        option = st.selectbox("**Select a Product:**", ["No Product", "Add New Product"] + st.session_state["existing_categories"], help="To add a new product not in the list, select the 'Add New Product' option.")
        new_category = ""
        if option == "Add New Product":
            new_category = st.text_input("**Add New Product:**", max_chars=50, placeholder="Enter new product name", help="Make sure not to enter the name of an existing product.")
            new_category = new_category.title()

    with col2:
        do_number = st.text_input("**DO Number**", max_chars=50, placeholder="Enter DO number", help="Delivery order reference number")

    col1, col2 = st.columns(2)
    with col1:
        quantity = st.number_input("**Quantity of Defective Products:**", min_value=0, max_value=1000, step=1, format="%d", placeholder="Enter the number defective products")
    with col2:
        cost = st.number_input("**Unit Cost ($):**", min_value=0.0, max_value=5000.0, step=0.01, format="%.2f", placeholder="Enter unit price")

    total_price = quantity * cost
    if cost:
        st.markdown(f'<p style="font-size:14px;"><strong>Total Cost:</strong> <span style="font-size:16px;">${total_price:.2f}</span></p>', unsafe_allow_html=True)

    defect_type = st.radio("**Select Defect Type:**", ["Rework", "Scrap"], captions=["Parts can be replaced", "Totally unusable"], horizontal=True)
    description = st.text_area("**Description of Defect(s):** (max. 300 characters)", max_chars=300, placeholder="Go into detail on the defect")
    action = st.text_area("**Description of Action(s) Taken:** (max. 300 characters)", max_chars=300, placeholder="Go into detail on the action(s) taken")
    submitter = st.text_input("**Submitter:**", max_chars=50, placeholder="Enter name of submitter")
    checkbox = st.checkbox("I understand that this submission is final and cannot be edited or deleted.")

    st.write("New Category is" + new_category)

    # Handle Submission
    if st.button("Submit"):
        errors = validate_inputs(option, new_category, do_number, quantity, cost, description, action, submitter, checkbox)
        if errors:
            if len(errors) > 1:
                error_message = "\n".join(f"{i+1}. {error}" for i, error in enumerate(errors))  # Numbering errors
            else:
                error_message = errors[0]  # Single error, no numbering
            st.error(error_message)
        else:
            if option == "Add New Product":  # If user adds a new product, add to existing_categories cache and Sheet 2
                data_to_append = [new_category, do_number, quantity, f"{total_price:.2f}", defect_type, description, action, submitter, datetime.now().strftime("%d/%m/%Y %H:%M:%S")]
                st.session_state["sheet2"].append_row([new_category])  # Add new product to the categories
                st.session_state["existing_categories"].append(new_category)  # Update local cache
            else:  # User selects a product from dropdown
                data_to_append = [option, do_number, quantity, total_price, defect_type, description, action, submitter, datetime.now().strftime("%d/%m/%Y %H:%M:%S")]

            if is_duplicate_submission(data_to_append):  # If user submits the exact same submission on the same day
                st.error("This submission already exists. Please do not submit a duplicate.")

            else:
                submit_defect(data_to_append)
                placeholder = st.empty()
                placeholder.info(f"Submitted successfully on {datetime.now().strftime('%d/%m/%Y at %I:%M %p')}.")
                sleep(3)
                placeholder.empty()

with tab2:
    st.markdown(f"""
    #### Defect Submission Guide
    - **Step 1 - Enter Product Name:** Choose a product from the list in **Select a Product**. To add a new product to the list, choose the 'Add New Product' option and enter its name in **Add New Product**. The maximum number of characters allowed is 50. You cannot enter a product name that already exists.
    
    - **Step 2 - Enter DO Number:** Enter the delivery order reference number in **DO Number**. The maximum number of characters allowed is 50. This is required.
    
    - **Step 3 - Enter Quantity and Unit Cost:** Using the number inputs, enter the quantity in **Quantity of Defect Products** and unit cost in **Unit Cost ($)**. If both entered, the total cost (quantity x unit cost) will be displayed. Both the quantity and unit cost cannot be zero.
    
    - **Step 4 - Classify the Defect:** Choose either "Rework" or "Scrap" from **Select Defect Type**. 
    
    - **Step 5 - Describe the Defect(s) and Action(s) Taken:** Go into detail on the defects and actions taken in **Description of Defect(s)** and **Description of Action(s) Taken**. The maximum number of characters allowed is 300. Both descriptions are required.
    
    - **Step 6 - Enter Submitter:** Enter the submitter's name in **Submitter**. The maximum number of characters allowed is 50. This is required.
    
    - **Step 7 - Check the Checkbox:** By checking the checkbox, you are sure that your submission is correct and cannot be altered after submission. This is required.
    
    - **Step 8 - Submit Defect:** Finally, click on **Submit** to add your entry. The time of submission will be recorded. Do not submit the same entry twice.
    """)
