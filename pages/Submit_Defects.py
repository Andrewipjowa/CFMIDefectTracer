import streamlit as st
from datetime import datetime
from time import sleep
import gspread
from google.oauth2.service_account import Credentials
import re
import json

st.set_page_config(page_title="Defect Tracer | Submit Defects", page_icon="cfm-holdings-logo.png", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stToolbar"] {display: none !important;} /* Hides the top right menu */
    </style>
""", unsafe_allow_html=True)

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


# Set up Google Credentials using Streamlit secrets
google_credentials_json = st.secrets["google_sheets"]["credentials_json"]

clean_credentials = re.sub(r'[^\x00-\x7F]+', '', google_credentials_json)  # Clean the credentials

credentials_dict = json.loads(clean_credentials, strict=False)  # Convert the credentials JSON string back into a dictionary


# OPEN THE GOOGLE SPREADSHEET & SET UP LOCAL CACHE ######################################

# Define the scope of the app (access to Sheets and Drive)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Authenticate using the credentials
creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
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
    st.session_state["sheet1_records"].append(dict(zip(["Case Number", "Customer", "Product", "DO Number", "Quantity", "Cost", "Type", "Description", "Action", "Submitter", "Timestamp", "Status", "Comments", "Closed By", "Date Closed", "Account"], data_to_append)))


# SUBMIT DEFECTS ########################################################################
def validate_inputs(customer, option, new_category, do_number, quantity, cost, description, action, submitter, checkbox):
    errors = []
    existing_categories = st.session_state["existing_categories"]

    if not customer.strip():
        errors.append("Customer is required.")
    elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", customer):
        errors.append("Customer cannot have no letters or numbers.")
    if option == "No Part Code":
        errors.append("Part code is required.")
    if option == "Add New Part Code":
        if not new_category:
            errors.append("Either select a part code or enter a new part code name.")
        elif new_category.lower() in [category.lower() for category in existing_categories]:
            errors.append("Part code entered already exists.")
        elif not re.search(r"[A-Za-z0-9]", new_category):  # Ensures at least one letter or number
            errors.append("Part code cannot have no letters or numbers.")
    elif option == "No Part Code" and new_category:
        errors.append("Either select a part code or enter a new part code name.")
    if not do_number.strip():
        errors.append("DO number is required.")
    elif not re.match(r"^(?=.*[A-Za-z0-9]).*$", do_number):
        errors.append("DO Number cannot have no letters or numbers.")
    if quantity == 0 and cost == 0:
        errors.append("Invalid quantity and unit cost.")
    elif quantity == 0:
        errors.append("Invalid quantity.")
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
                and row["Customer"] == data_to_check[0]
                and row["Product"] == data_to_check[1]
                and row["DO Number"] == data_to_check[2]
                and row["Quantity"] == data_to_check[3]
                and row["Cost"] == data_to_check[4]
                and row["Type"] == data_to_check[5]
                and row["Description"] == data_to_check[6]
                and row["Action"] == data_to_check[7]
                and row["Submitter"] == data_to_check[8]
                and row_date == data_to_check[9][:10]):
            return True  # Duplicate found
    return False  # Duplicate not found


st.subheader("Submit A Defect")

tab1, tab2 = st.tabs(["Submit A Defect", "Help/Guide"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        customer = st.text_input("**Customer**", max_chars=50, placeholder="Enter customer")
    with col2:
        do_number = st.text_input("**DO Number**", max_chars=50, placeholder="Enter DO number", help="Delivery order reference number")

    col1, col2 = st.columns(2)
    with col1:
        option = st.selectbox("**Part Code:**", ["No Part Code", "Add New Part Code"] + st.session_state["existing_categories"], help="To add a new part code not in the list, select the 'Add New Part Code' option.")
        new_category = ""
    with col2:
        if option == "Add New Part Code":
            new_category = st.text_input("**Add New Part Code:**", max_chars=50, placeholder="Enter new part code", help="Make sure not to enter an existing part code.")

    col1, col2 = st.columns(2)
    with col1:
        quantity = st.number_input("**Quantity:**", min_value=0, max_value=1000, step=1, format="%d", placeholder="Enter the quantity")
    with col2:
        cost = st.number_input("**Unit Cost ($):**", min_value=0.0, max_value=5000.0, step=0.01, format="%.2f", placeholder="Enter unit price")

    total_price = quantity * cost
    if cost:
        st.markdown(f'<p style="font-size:14px;"><strong>Total Cost:</strong> <span style="font-size:16px;">${total_price:.2f}</span></p>', unsafe_allow_html=True)

    defect_type = st.radio("**Select Defect Type:**", ["Rework", "Scrap"], captions=["Parts can be replaced", "Totally unusable"], horizontal=True)
    description = st.text_area("**Description of Defect(s):** (max. 300 characters)", max_chars=300, placeholder="Go into detail on the defect")
    action = st.text_area("**Description of Action(s) Taken:** (max. 300 characters)", max_chars=300, placeholder="Go into detail on the action(s) taken")
    submitter = st.text_input("**Submitter:**", max_chars=50, placeholder="Enter name here")
    checkbox = st.checkbox("I understand that this submission is final and cannot be edited or deleted.")

    # Handle Submission
    if st.button("Submit"):
        errors = validate_inputs(customer, option, new_category, do_number, quantity, cost, description, action, submitter, checkbox)
        if errors:
            if len(errors) > 1:
                error_message = "\n".join(f"{i+1}. {error}" for i, error in enumerate(errors))  # Numbering errors
            else:
                error_message = errors[0]  # Single error, no numbering
            st.error(error_message)
        else:
            if option == "Add New Part Code":  # If user adds a new product, add to existing_categories cache and Sheet 2
                data_to_append = [customer, new_category, do_number, quantity, total_price, defect_type, description, action, submitter, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Open", "N/A", "N/A", "N/A", st.session_state["email"]]
                st.session_state["sheet2"].append_row([new_category])  # Add new product to the categories
                st.session_state["existing_categories"].append(new_category)  # Update local cache
            else:  # User selects a product from dropdown
                data_to_append = [customer, option, do_number, quantity, total_price, defect_type, description, action, submitter, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Open", "N/A", "N/A", "N/A", st.session_state["email"]]

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
    - **Step 1 - Enter Customer:** Enter the customer in **Customer**. The maximum number of characters allowed is 50. This is required.
    
    - **Step 2 - Enter DO Number:** Enter the delivery order reference number in **DO Number**. The maximum number of characters allowed is 50. This is required.
    
    - **Step 3 - Enter Part Code:** Choose a part code from the list in **Part Code**. To add a new part code to the list, choose the 'Add New Part Code' option and enter it in **Add New Part Code**. The maximum number of characters allowed is 50. You cannot enter a part code that already exists.
    
    - **Step 4 - Enter Quantity and Unit Cost:** Using the number inputs, enter the quantity in **Quantity** and unit cost in **Unit Cost ($)**. If both entered, the total cost (quantity x unit cost) will be displayed. Both the quantity and unit cost cannot be zero.
    
    - **Step 5 - Classify the Defect:** Choose either "Rework" or "Scrap" from **Select Defect Type**. 
    
    - **Step 6 - Describe the Defect(s) and Action(s) Taken:** Go into detail on the defects and actions taken in **Description of Defect(s)** and **Description of Action(s) Taken**. The maximum number of characters allowed is 300. Both descriptions are required.
    
    - **Step 7 - Enter Submitter:** Enter the submitter's name in **Submitter**. The maximum number of characters allowed is 50. This is required.
    
    - **Step 8 - Check the Checkbox:** By checking the checkbox, you are sure that your submission is correct and cannot be altered after submission. This is required.
    
    - **Step 9 - Submit Defect:** Finally, click on **Submit** to add your entry. The time of submission will be recorded. Do not submit the same entry twice.
    """)
