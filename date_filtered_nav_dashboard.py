import streamlit as st
import pandas as pd
import os
from datetime import timedelta
from datetime import datetime
import openpyxl

# Define the directory where the workbooks are stored (this is in the same repo)
WORKBOOK_DIR = "NAV"  # Folder where the Excel workbooks are stored

# Function to list available Excel files in the specified directory
def list_workbooks(directory):
    try:
        # List only .xlsx files in the directory
        files = [f for f in os.listdir(directory) if f.endswith('.xlsx')]
        return files
    except FileNotFoundError:
        st.error("Directory not found. Please ensure the specified directory exists.")
        return []

# Function to load NAV data from the selected workbook and handle date parsing
def load_nav_data(file_path):
    try:
        data = pd.read_excel(file_path, sheet_name=0)  # Load full sheet data without headers
        # Ensure 'Date' column is datetime; coerce errors to handle non-date values
        data.columns = data.iloc[0]  # Use the first row as headers
        data = data.drop(0)  # Drop the first row after making it the header
        if 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        else:
            st.error("Date column not found in the dataset.")
        return data.reset_index(drop=True)  # Reset the index after modifications
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return pd.DataFrame()

# Function to filter data based on the selected date range
def filter_data_by_date(data, date_range):
    if 'Date' not in data.columns:
        st.error("Date column not found in the data for filtering.")
        return data

    # Ensure all 'Date' values are valid datetime objects
    data = data.dropna(subset=['Date'])

    if date_range == "1 Day":
        return data.tail(1)
    elif date_range == "5 Days":
        return data.tail(5)
    elif date_range == "1 Month":
        one_month_ago = data['Date'].max() - timedelta(days=30)
        return data[data['Date'] >= one_month_ago]
    elif date_range == "6 Months":
        six_months_ago = data['Date'].max() - timedelta(days=180)
        return data[data['Date'] >= six_months_ago]
    elif date_range == "1 Year":
        one_year_ago = data['Date'].max() - timedelta(days=365)
        return data[data['Date'] >= one_year_ago]
    else:  # Max
        return data

# Function to process the Excel data and identify stock name changes dynamically
def process_excel_data(data):
    stock_blocks = []
    current_block = None

    # Dynamically find the column that contains 'Stocks'
    stock_column = None
    for col in data.columns:
        if data[col].astype(str).str.contains('Stocks').any():
            stock_column = col
            break

    if not stock_column:
        st.error("No 'Stocks' column found in the workbook.")
        return []

    # Iterate through the rows of the DataFrame
    for idx, row in data.iterrows():
        if isinstance(row[stock_column], str) and row[stock_column] == 'Stocks':  # Detect when stock names change
            if current_block:
                current_block['end_idx'] = idx - 1  # End the current block before the next 'Stocks' row
                stock_blocks.append(current_block)  # Save the completed block

            # Create a new block
            stock_names = row[2:7].tolist()  # Get stock names from columns C to G
            current_block = {'stock_names': stock_names, 'start_idx': idx + 2, 'end_idx': None}

    if current_block:
        current_block['end_idx'] = len(data) - 1  # Handle the last block until the end of the dataset
        stock_blocks.append(current_block)

    return stock_blocks

# Function to insert stock names before the dates in the filtered data
def insert_stock_names(data, stock_blocks):
    final_data = pd.DataFrame()

    for block in stock_blocks:
        # Get the block's data
        block_data = data.iloc[block['start_idx']:block['end_idx'] + 1].copy()
        block_data = block_data.reset_index(drop=True)

        # Get the date range for the block
        start_date = block_data['Date'].min()
        end_date = block_data['Date'].max()

        # Find the dates that match the block date range in the filtered data
        matching_dates = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]

        if not matching_dates.empty:
            # Create a row for the stock names with None for other columns
            stock_names_row = pd.DataFrame([[None] * len(data.columns)], columns=data.columns)
            for i, stock_name in enumerate(block['stock_names']):
                stock_names_row[f'Stock{i + 1}'] = stock_name

            # Append the stock names row to the final data
            final_data = pd.concat([final_data, stock_names_row], ignore_index=True)

        # Append the actual data (dates) for the block
        final_data = pd.concat([final_data, matching_dates], ignore_index=True)

    return final_data

# Main Streamlit app function
def main():
    st.title("NAV Data Dashboard")

    # List available workbooks in the directory
    workbooks = list_workbooks(WORKBOOK_DIR)

    if not workbooks:
        st.error("No Excel workbooks found in the specified directory.")
        return

    # Display the data for a specific workbook (example: the first one)
    selected_workbook = st.selectbox("Select a workbook", workbooks)
    
    file_path = os.path.join(WORKBOOK_DIR, selected_workbook)

    nav_data = load_nav_data(file_path)

    if not nav_data.empty:
        # Process the Excel data and detect stock name changes (identify stock blocks)
        stock_blocks = process_excel_data(nav_data)

        if not stock_blocks:
            st.error("No valid stock data found in the workbook.")
            return

        # Allow the user to select a date range
        date_ranges = ["1 Day", "5 Days", "1 Month", "6 Months", "1 Year", "Max"]
        selected_range = st.selectbox("Select Date Range", date_ranges)

        # Filter the combined data by the selected date range
        filtered_data = filter_data_by_date(nav_data, selected_range)

        # Insert stock names above the matching date ranges
        final_data = insert_stock_names(filtered_data, stock_blocks)

        # Display the final data in a single table
        st.write("### Combined Stock Data Table")
        st.dataframe(final_data.reset_index(drop=True))

    else:
        st.error("Failed to load data. Please check the workbook format.")

if __name__ == "__main__":
    main()
