
import pandas as pd

try:
    df = pd.read_excel("Sem 6 attendace.xlsx")
    print("Columns found:", df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.head())
except Exception as e:
    print(f"Error reading file: {e}")
