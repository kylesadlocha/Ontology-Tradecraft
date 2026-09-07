import pandas as pd

df = pd.read_excel(r"C:\Users\kygal\repos\Ontology-Tradecraft\projects\project-2\assignment\src\aircraft_data.xlsx")

print(df.head())
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
