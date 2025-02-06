import streamlit as st
import pyrebase
from time import sleep
import re

st.set_page_config(page_title="Defect Tracer | Login", page_icon="cfm-holdings-logo.png", layout="centered", initial_sidebar_state="expanded")

if 'email' in st.session_state:
    with st.sidebar:
        if st.button("Logout"):  # Logout functionality
            st.session_state.clear()  # Clears all session state variables
            st.info("Logged out successfully, Goodbye.")
            sleep(1)
            st.switch_page("Login.py")

# Firebase configuration
config = {
    'apiKey': "AIzaSyDPil6-HX-RkZtYp1fAjxyqjTSyJMUOQg8",
    'authDomain': "cfmi-defect-tracer-a2dad.firebaseapp.com",
    'projectId': "cfmi-defect-tracer-a2dad",
    'storageBucket': "cfmi-defect-tracer-a2dad.firebasestorage.app",
    'messagingSenderId': "9745545302",
    'appId': "1:9745545302:web:3d4e32ec1d2afd408c63f7",
    'databaseURL': ""}

# Initialise Firebase
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()


# Handling login
def login(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        st.session_state['email'] = user['email']
        return user
    except:
        return None


# Handle signup (create new user)
def signup(email, password):
    try:
        add_user = auth.create_user_with_email_and_password(email, password)
        placeholder = st.empty()
        placeholder.info("Account created successfully!")
        sleep(3)
        placeholder.empty()
        return add_user
    except Exception as e:
        error_message = str(e)
        if "EMAIL_EXISTS" in error_message:
            st.error("This email is already registered. Please create an account with a different email.")
        elif "INVALID_EMAIL" in error_message:
            st.error("This email is invalid. Please create an account with an existing email.")
        else:
            st.error("An unexpected error occurred. Please try again.")


# Regex for email validation
def is_valid_email(email):
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(email_regex, email) is not None


# Check if the email exists in session state
if 'email' in st.session_state:
    st.subheader("Defect/Reject Tracer")

    tab1, tab2 = st.tabs(["Welcome", "Add a New Account"])
    with tab1:
        st.write("Welcome to the CFM Infratrade defect tracer. Here, you can submit defects and view defects submitted.")

        if st.session_state["email"] == "test@gmail.com":
            st.write("To add new accounts, disable accounts or change passwords, go to https://console.firebase.google.com/u/0/project/cfmi-defect-tracer-a2dad/authentication/users.")

        if st.button("Logout", key="1"):  # Logout functionality
            st.session_state.clear()  # Clears all session state variables
            st.info("Logged out successfully, Goodbye.")
            sleep(1)
            st.switch_page("Login.py")

    with tab2:
        st.markdown("##### Add a New Account")

        add_email = st.text_input("**Email**", placeholder="Enter email")
        add_password = st.text_input("**Password**", key='2', type="password", placeholder="Enter password")
        confirm_add_password = st.text_input("**Confirm Password**", type="password", placeholder="Re-enter password")

        if st.button("Add Account"):
            if not add_email:
                st.error("Email is required.")
            elif not is_valid_email(add_email):
                st.error("Please enter a valid email.")
            elif not add_password:
                st.error("Password is required.")
            elif len(add_password) < 6:
                st.error("Password must be at least 6 characters.")
            elif not confirm_add_password:
                st.error("Confirm Password is required.")
            elif add_password != confirm_add_password:
                st.error("The passwords do not match.")
            else:
                add_user = signup(add_email, add_password)

else:  # If no email is stored, user is not logged in
    st.session_state.clear()

    st.subheader("Defect/Reject Tracer Login")

    email = st.text_input("**Email**", placeholder="Enter email")
    password = st.text_input("**Password**", type="password", placeholder="Enter password")

    if st.button("Login"):
        if not email or not password:
            st.error("Email and password are both required.")
        else:
            user = login(email, password)
            if user:
                st.info("Logged in successfully, Welcome!")
                sleep(1)
                st.switch_page("pages/Submit_Defects.py")
            else:
                st.error("Login failed, incorrect email and/or password.")
