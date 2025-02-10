import streamlit as st
import calendar
from datetime import datetime, timedelta
from time import sleep
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter, defaultdict

st.set_page_config(page_title="Defect Tracer | View Submissions", page_icon="cfm-holdings-logo.png", layout="centered", initial_sidebar_state="expanded")

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

if "existing_categories" not in st.session_state:
    st.switch_page("pages/Submit_Defects.py")
    st.stop()

# GET DATA FROM LOCAL CACHE #############################################################
all_records = st.session_state["sheet1_records"]
filter_options = st.session_state["existing_categories"]


# VIEWING SUBMISSIONS ###################################################################
# Check the selected filters and alter display
def filter_display(date_filter, month_filter, year_filter, product_filter):
    text = ""

    if year_filter != "None" and month_filter == "None" and date_filter == "None":
        text = f" in {year_filter}"
    elif year_filter != "None" and month_filter != "None" and date_filter == "None":
        text = f" in {month_filter} {year_filter}"
    elif year_filter != "None" and month_filter != "None" and date_filter != "None":
        text = f" in {date_filter} {month_filter} {year_filter}"

    if product_filter or type_filter != "All" or case_filter != "All":
        text += " that matched your filters"
    else:
        text = "Invalid"

    return text


years = [datetime.strptime(row['Timestamp'], "%d/%m/%Y %H:%M:%S").year for row in all_records if row['Timestamp']]  # Extract the years from the timestamps
years_with_data = [str(year) for year in (sorted(set(years), reverse=True))]  # Only get years with data, arrange in descending order, and convert to string

st.subheader("View Defect Submissions")

tab1, tab2, tab3, tab4 = st.tabs(["All Submissions", "Specific Submission", "Chart Visualization", "Help/Guide"])

with tab1:
    st.markdown("#### All Submissions")

    with st.expander("*Filter Options*", expanded=True):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            product_filter = st.multiselect("**Specific Product(s)**", filter_options, default=None, placeholder="Select product(s)")
        with col2:
            type_filter = st.selectbox("**Defect Type**", ["All", "Rework", "Scrap"])
        with col3:
            case_filter = st.selectbox("**Case Status**", ["All", "Open", "Closed"])

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            year_filter = st.selectbox("**Select Year**", ["None"] + years_with_data)
        with col2:
            month_filter = st.selectbox("**Select Month**", ["None"] + list(calendar.month_name)[1:], disabled=(year_filter == "None"), help="Select a year first" if year_filter == "None" else None)

        # Generate dates based the selected month
        if month_filter != "None":
            current_year = datetime.now().year
            month_number = list(calendar.month_name).index(month_filter)  # Convert month name to number
            days_in_month = calendar.monthrange(current_year, month_number)[1]  # Get total days in the selected month
            dates_in_month = list(range(1, days_in_month + 1))  # Create a list of dates in numbers
        else:
            dates_in_month = [""]  # Empty list if no month is selected

        with col3:
            date_filter = st.selectbox("**Select Date:**", ["None"] + dates_in_month, disabled=(month_filter == "None"), help="Select a month first" if year_filter != "None" else None)

    if product_filter or type_filter != "All" or year_filter != "None":
        button_name = "Filtered"
    else:
        button_name = "All"

    if st.button(f"View {button_name} Submissions"):
        with st.spinner('Searching data...'):
            filtered = []  # Empty list to store filtered data
            for row in all_records:  # For each row in the data
                case_number = row['Case Number']
                customer = row['Customer']
                part_code = row['Product']
                do_number = row['DO Number']
                quantity = row['Quantity']
                cost = row['Cost']
                defect_type = row['Type']
                description = row['Description']
                action = row['Action']
                submitter = row['Submitter']
                timestamp = row['Timestamp']
                status = row['Status']

                try:  # Convert the Timestamp to datetime format
                    timestamp = datetime.strptime(timestamp, "%d/%m/%Y %H:%M:%S")
                except ValueError:
                    continue  # Skip rows where the date format is incorrect

                match_product = not product_filter or part_code in product_filter  # Product filtering
                match_type = type_filter == "All" or row['Type'] == type_filter  # Defect type filtering
                match_case = case_filter == "All" or row['Status'] == case_filter  # Case status filtering

                # Date filtering
                match_date = True
                if year_filter != "None":
                    match_date = match_date and timestamp.year == int(year_filter)
                if month_filter != "None":
                    match_date = match_date and timestamp.month == list(calendar.month_name).index(month_filter)
                if date_filter != "None":
                    match_date = match_date and timestamp.day == int(date_filter)

                if match_product and match_case and match_type and match_date:
                    filtered.append({
                        "Case Number": case_number,
                        "Case Status": status,
                        "Customer": customer,
                        "Part Code": part_code,
                        "DO Number": str(do_number),
                        "Quantity": str(quantity),
                        "Cost ($)": f"{float(cost):.2f}",
                        "Defect Type": defect_type,
                        "Defect Description": description,
                        "Action Taken": action,
                        "Submitter": submitter,
                        "Timestamp": timestamp})

            filtered_sorted = sorted(filtered, key=lambda x: x['Timestamp'], reverse=True)  # Sort data in reverse order based on the datetime

            total_cost = sum(float(entry["Cost ($)"]) for entry in filtered)

            for entry in filtered_sorted:  # Keep only the date when displaying or processing
                entry['Submission Date'] = entry['Timestamp'].strftime("%d/%m/%Y")

            filtered_sorted = [{key: entry[key] for key in entry if key != 'Timestamp'} for entry in filtered_sorted]  # Filter out the timestamp and display the results

            if filtered_sorted:  # Display the filtered data
                st.markdown(f"##### {str(button_name + ' Defect Submissions')}")

                if filter_display(date_filter, month_filter, year_filter, product_filter) != "Invalid":
                    if len(filtered_sorted) == 1:
                        st.write(f"There was 1 submission{filter_display(date_filter, month_filter, year_filter, product_filter)}.")
                    else:
                        st.write(f"There were {len(filtered_sorted)} submissions{filter_display(date_filter, month_filter, year_filter, product_filter)}.")
                else:
                    st.write("Showing the latest records as of today.")

                st.write(f"**Total Cost:** ${total_cost:.2f}")
                st.dataframe(filtered_sorted)  # Display as a table

            else:  # Check the selected filters and display custom messages
                st.markdown("##### No Submissions Found")
                st.write(f"No records found {filter_display(date_filter, month_filter, year_filter, product_filter)}.")

with tab2:
    case_numbers = [row['Case Number'] for row in all_records]
    case_numbers.reverse()

    st.markdown("#### Specific Submission")

    col1, col2 = st.columns(2)
    with col1:
        search_case = st.selectbox("**Search Case Number:**", ["None"] + case_numbers)
        st.write("")


    if search_case != "None":
        case_records = [row for row in all_records if row['Case Number'] == search_case]  # Filter records for the selected case number
        case = case_records[0]  # Assuming only one record per case

        case_status = case['Status']

        # Displaying the details in a neat table format
        case_data = {
            "Customer": case['Customer'],
            "Part Code": case['Product'],
            "DO Number": case['DO Number'],
            "Quantity": case['Quantity'],
            "Cost": case['Cost'],
            "Defect Type": case['Type'],
            "Description": case['Description'],
            "Action": case['Action'],
            "Submitter": case['Submitter'],
            "Submission Date": case['Timestamp'][:10]
        }

        st.markdown(f"##### Viewing Case #{search_case} [Case Status: {case_status}]")
        # Display in a table format
        st.table(case_data)

        if case_status == "Open":
            st.write("##### Mark Case as Closed")
            checkbox = st.checkbox("I understand that closing a case is irreversible.")
            if st.button("Mark as Closed"):
                if not checkbox:
                    st.error("Check the checkbox first.")
                else:
                    # Update status to closed in all_records
                    for row in all_records:
                        if row['Case Number'] == search_case:
                            row['Status'] = "Closed"

                    # Update the status in Google Sheets (sheet1)
                    sheet1 = st.session_state["sheet1"]
                    cell = sheet1.find(search_case)  # Find the cell with the case number
                    if cell:
                        sheet1.update_cell(cell.row, 12, "Closed")  # Update the status in Status (column 12 of sheet)

                        placeholder = st.empty()
                        placeholder.info(f"Case closed successfully.")
                        sleep(3)
                        placeholder.empty()
                        st.switch_page("pages/View_Submissions.py")

with tab3:
    years_with_data = sorted(set(datetime.strptime(row['Timestamp'], "%d/%m/%Y %H:%M:%S").year for row in all_records), reverse=True)

    st.markdown("#### Chart Visualization")

    with st.expander("*Filter Options*", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            selected_year = st.selectbox("**Select Year**", years_with_data, key=1)  # Allow users to select the year (only years with data)
        with col2:
            selected_chart = st.selectbox("**Chart Category**", ["Defect Quantity", "Number of Submissions"])

    chart_records = [row for row in all_records if datetime.strptime(row['Timestamp'], "%d/%m/%Y %H:%M:%S").year == selected_year]  # Filter the records by the selected year
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']  # Define all months

    st.write("Showing the latest records as of today.")

    # Get Total Number of Submissions per Month
    month = [datetime.strptime(row['Timestamp'], "%d/%m/%Y %H:%M:%S").strftime("%b") for row in chart_records]  # Extract months and count occurrences for the selected year
    month_counts = Counter(month)
    month_counts = {month: month_counts.get(month, 0) for month in month_order}  # If month has no data, fill it with 0
    month_df = pd.DataFrame(list(month_counts.items()), columns=["Month", "Submissions"])
    month_df['Month'] = pd.Categorical(month_df['Month'], categories=month_order, ordered=True)  # Ensure months are treated as categories (January to December)
    month_df = month_df.sort_values("Month")  # Sort by month order

    # Get Top 3 Products with the Most Submissions
    products = [row['Product'] for row in chart_records]  # Get the list of products from all records
    product_count = Counter(products)  # Count occurrences of each product
    top_product_month = product_count.most_common(3)  # Get the top 3 most common products
    top_product_month_df = pd.DataFrame(top_product_month, columns=['Product', 'Submissions'])

    # Get Total Defect Quantity per Month
    quantity = [int(row['Quantity']) for row in chart_records]  # Get the quantity of defects for each record
    month_quantity = defaultdict(int)  # Aggregate quantities by month
    for m, q in zip(month, quantity):
        month_quantity[m] += q  # Sum the quantities for each month
    month_quantity = {month: month_quantity.get(month, 0) for month in month_order}  # If month has no data, fill it with 0
    quantity_df = pd.DataFrame(list(month_quantity.items()), columns=["Month", "Quantity"])
    quantity_df['Month'] = pd.Categorical(quantity_df['Month'], categories=month_order, ordered=True)  # Ensure months are treated as categories
    quantity_df = quantity_df.sort_values("Month")  # Sort by month order

    # Get Top 3 Products with Most Quantity of Defects
    products = [row['Product'] for row in chart_records]  # Get the list of products from all records
    product_quantity = defaultdict(int)  # Aggregate product quantities
    for m, q in zip(products, quantity):
        product_quantity[m] += q  # Sum the quantities for each product
    product_quantity = Counter(product_quantity)
    top_product_quantity = product_quantity.most_common(3)  # Get the top 3 most common products
    top_product_quantity_df = pd.DataFrame(top_product_quantity, columns=['Product', 'Quantity'])

    if selected_chart == "Number of Submissions":
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))  # 2 rows and 1 column

        # Graph for: Total Number of Submissions per Month
        chart1 = ax1.bar(month_df['Month'], month_df['Submissions'])
        ax1.set_title(f"Total Number of Submissions per Month in {selected_year}", fontsize=18, fontweight='bold', fontname='Calibri', pad=13)
        ax1.yaxis.get_major_locator().set_params(integer=True)  # Ensure y-axis shows whole numbers only

        # Setting x-axis and y-axis fonts and sizes
        ax1.tick_params(axis='x', labelsize=14)
        ax1.tick_params(axis='y', labelsize=14)
        ax1.set_xticks(ax1.get_xticks())
        ax1.set_yticks(ax1.get_yticks())
        ax1.set_xticklabels(ax1.get_xticklabels(), fontname='Calibri')
        ax1.set_yticklabels(ax1.get_yticklabels(), fontname='Calibri')

        # Include the values of each bar if value != 0
        for bar in chart1:
            if bar.get_height() != 0:  # Check if the height of the bar is not 0 and then place the bar value above the bar
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03, str(int(bar.get_height())), ha='center', va='bottom', fontsize=14, fontname='Calibri')

        # Graph for: Top 3 Products with the Most Submissions
        chart2 = ax2.bar(top_product_month_df['Product'], top_product_month_df['Submissions'])
        ax2.set_title(f"Top 3 Products with the Most Submissions in {selected_year}", fontsize=19, fontweight='bold', fontname='Calibri', pad=13)
        ax2.yaxis.get_major_locator().set_params(integer=True)  # Ensure y-axis shows whole numbers only

        # Setting x-axis and y-axis fonts and sizes
        ax2.tick_params(axis='x', labelsize=14)
        ax2.tick_params(axis='y', labelsize=14)
        ax2.set_xticks(ax2.get_xticks())
        ax2.set_yticks(ax2.get_yticks())
        ax2.set_xticklabels(ax2.get_xticklabels(), fontname='Calibri')
        ax2.set_yticklabels(ax2.get_yticklabels(), fontname='Calibri')

        # Include the values of each bar
        ax2.bar_label(chart2, fontsize=14, fontname='Calibri')

        # Plot all the graphs
        plt.subplots_adjust(hspace=0.4)
        st.pyplot(fig)

    else:
        fig, (ax3, ax4) = plt.subplots(2, 1, figsize=(10, 10))  # 2 rows and 1 column
        # Graph for: Total Defect Quantity per Month
        chart3 = ax3.bar(quantity_df['Month'], quantity_df['Quantity'], color='skyblue')
        ax3.set_title(f"Total Defect Quantity per Month in {selected_year}", fontsize=19, fontweight='bold', fontname='Calibri', pad=13)
        ax3.yaxis.get_major_locator().set_params(integer=True)  # Ensure y-axis shows whole numbers only

        # Setting x-axis and y-axis fonts and sizes
        ax3.tick_params(axis='x', labelsize=14)
        ax3.tick_params(axis='y', labelsize=14)
        ax3.set_xticks(ax3.get_xticks())
        ax3.set_yticks(ax3.get_yticks())
        ax3.set_xticklabels(ax3.get_xticklabels(), fontname='Calibri')
        ax3.set_yticklabels(ax3.get_yticklabels(), fontname='Calibri')

        # Include the values of each bar if value != 0
        for bar in chart3:
            if bar.get_height() != 0:  # Check if the height of the bar is not 0 and then place the bar value above the bar
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03, str(int(bar.get_height())), ha='center', va='bottom', fontsize=14, fontname='Calibri')

        # Graph for: Top 3 Products with Most Quantity of Defects
        chart4 = ax4.bar(top_product_quantity_df['Product'], top_product_quantity_df['Quantity'], color='skyblue')
        ax4.set_title(f"Top 3 Products with the Most Quantity of Defects in {selected_year}", fontsize=19, fontweight='bold', fontname='Calibri', pad=13)
        ax4.yaxis.get_major_locator().set_params(integer=True)  # Ensure y-axis shows whole numbers only

        # Setting x-axis and y-axis fonts and sizes
        ax4.tick_params(axis='x', labelsize=14)
        ax4.tick_params(axis='y', labelsize=14)
        ax4.set_xticks(ax4.get_xticks())
        ax4.set_yticks(ax4.get_yticks())
        ax4.set_xticklabels(ax4.get_xticklabels(), fontname='Calibri')
        ax4.set_yticklabels(ax4.get_yticklabels(), fontname='Calibri')

        # Include the values of each bar
        ax4.bar_label(chart4, fontsize=14, fontname='Calibri')

        # Plot all the graphs
        plt.subplots_adjust(hspace=0.4)
        st.pyplot(fig)

with tab4:
    guide_date = datetime.now()

    st.markdown(f"""
    #### All Submissions Guide
    ##### How to Interact:
    - Use the dropdown menus in *Filter Options* to filter records based on product(s), defect types, case status, year, month, and date.
    - Click the button to view the records (and apply filters if selected).
    - Records are displayed in descending date order (most recent records are at the top).
    ##### Filtering Guide:
    - **I want to view submissions for certain product(s)**: Select the products you want from the **Select Specific Product(s)**. You can select more than one.
    - **I want to view submissions for reworked/scrapped defects**: Select the option from the **Select Defect Type**. Select all to show all submissions regardless of defect type.
    - **I want to view submissions for a certain year/month/date**: Select a year, month and/or date from the respective dropdowns. These are not mutually exclusive, meaning you can use each dropdown separately.
        - **Examples:**
            - Selecting {guide_date.year-1} from **Select Year** will filter the records to display only those from {guide_date.year-1}.
            
            - Selecting {guide_date.year-1} from **Select Year**, followed by selecting January from **Select Month**, will filter the records to display only those from January of {guide_date.year-1}.
            
    - **I want to view submissions for a certain case number**: Go to "Specific Submission" tab.
    
    ---
    
    #### Specific Submission Guide
    ##### How to Interact:
    - Use the **Search Case Number** to view all the details of a specific submission.
    - If the case status is 'Open', the **Mark as Closed** button will appear. Click on the button to close the case (this action is irreversible).
    
    ---
    
    #### Chart Visualization Guide
    ##### How to Interact:
    - Use the dropdown menus in *Filter Options* to filter records based on year and chart category.
    ##### Graph Explanations:
    - **Total Defect Quantity per Month**: This bar chart displays the sum of all defect quantities submitted each month, regardless of the product.
    
        - **Example:** 
            - There were 5 defects of Product A submitted on 1 February, 3 defects of Product B submitted on 2 February, and 2 defects of Product A submitted on 3 February. 
                
                Total defect quantity in February = 5 + 3 + 2 = 10.
            
    - **Top 3 Products with the Highest Defect Quantities**: This bar chart displays the top 3 products with the highest quantity of defects in the year.
    - **Number of Submissions per Month**: This bar chart displays the sum of all submissions each month, regardless of the product.
    
        - **Example:** 
            - There were 5 defects of Product A submitted on 1 February, 3 defects of Product B submitted on 2 February, and 2 defects of Product A submitted on 3 February.  
            
                Number of submissions in February = 1 + 1 + 1 = 3. 
            
    - **Top 3 Products with the Most Submissions**: This bar chart displays the top 3 products with the most number of submissions in the year.
    """)