import pandas as pd
file_path = "outputs/batch_sections_7.xlsx"
df = pd.read_excel(file_path)
column_name = "Experience"
column_data = df[column_name].dropna().astype(str).reset_index(drop=True)
data_len = len(column_data)
print(f"📄 Total records: {data_len}")

processed = {}
for i, text in enumerate(column_data):
    if processed.get(text):
        continue
    processed[text] = True

print("Unique: ",len(processed.keys()))
