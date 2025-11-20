import pandas as pd
import os

file_path = '/Users/TKM-h.almughrabi-c/Downloads/qa-trainings/QA Training Plan.xlsx'

try:
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")
    
    for sheet_name in xls.sheet_names:
        print(f"\n--- Sheet: {sheet_name} ---")
        df = pd.read_excel(xls, sheet_name=sheet_name, nrows=5)
        print(f"Columns: {list(df.columns)}")
        print("First 5 rows:")
        print(df.head().to_string())
        
except Exception as e:
    print(f"Error reading Excel file: {e}")
