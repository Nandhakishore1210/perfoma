"""
Inspect Excel file structure to understand the layout
"""
import pandas as pd

file_path = "C:/Users/Lenovo/Desktop/perfoma/Sem 6 attendace.xlsx"

print("=" * 100)
print("EXCEL FILE STRUCTURE INSPECTION")
print("=" * 100)

# Try reading with different parameters
for skip in range(0, 12):
    print(f"\n{'='*100}")
    print(f"READING WITH SKIPROWS={skip}")
    print("=" * 100)
    
    try:
        df = pd.read_excel(file_path, skiprows=skip, nrows=5)
        print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
        print(f"\nColumn Names:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1:2d}. '{col}'")
        
        print(f"\nFirst 3 Data Rows:")
        print(df.head(3).to_string())
        
        # Check if we found meaningful data
        non_null_cols = df.columns[~df.columns.str.contains('Unnamed', case=False, na=False)]
        if len(non_null_cols) >= 4:
            print(f"\n✅ POTENTIAL DATA FOUND! {len(non_null_cols)} meaningful columns")
            
    except Exception as e:
        print(f"Error: {e}")
