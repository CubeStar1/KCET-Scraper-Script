import pandas as pd
import re
from pathlib import Path

BASE_PATH = Path("../cutoff-processing")
CUTOFF_FILE_PATH = BASE_PATH / "cutoff-files/kcet_2024_m1_cutoffs.xlsx"
OUTPTU_FILE_PATH = BASE_PATH / "cutoff-files-output/kcet_2024_m1_cutoffs_output.xlsx"

df = pd.read_excel(CUTOFF_FILE_PATH, "Table 1", engine='openpyxl')
print(df)
df.fillna("", inplace=True)



for index, row in df.iterrows():
    flag = False
    for item in row:
        if item != "":
            flag = True

    if not flag:
        # print(index)
        df.drop(index, inplace=True)

key = ""
college_code = ""
college_name = ""
df['College Code'] = ""
df['College Name'] = ""
i = 0
for index, row in df.iterrows():
    for item in row:
        match = re.search(r'E[0-9]{3}', str(item))
        if match:
            key = match.group()
            college_code = match.group()
            college_name = str(item).split(college_code)[1].strip()
            if " ( GENERAL )" in str(item):
                key = str(item).split(" ( GENERAL )")[1].strip()
            else:
                key = str(item).strip()
            df.drop(index, inplace=True)
            i = index
            break
        elif re.search('1G', str(item)):
            df.drop(index, inplace=True)
            i = index
            break
    if i != index:
        df.at[index, 'College Code'] = college_code
        df.at[index, 'College Name'] = str(college_name).strip()

df.replace("--", "" , inplace = True)
df.replace("\n", " " , inplace = True, regex = True)
df["Round"] = "Mock1"
df.replace("", None, inplace=True)
df.dropna(axis=1, how='all', inplace=True)
df.rename(columns={"Unnamed: 0": "Branch"}, inplace=True)
df["College Name"] = df["College Name"].str.replace(" ", " ")
df.to_excel(OUTPTU_FILE_PATH, index=False)
