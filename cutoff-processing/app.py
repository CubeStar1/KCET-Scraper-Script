import streamlit as st
import pandas as pd
import re
import io


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.fillna("", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Remove empty rows
    df = df[df.astype(str).apply(lambda x: x.str.strip().ne("").any(), axis=1)]

    df['College Code'] = ""
    df['College Name'] = ""

    college_code = ""
    college_name = ""
    rows_to_drop = []

    for index, row in df.iterrows():
        for item in row:
            match = re.search(r'E[0-9]{3}', str(item))
            if match:
                college_code = match.group()
                college_name = str(item).split(college_code)[1].strip()
                rows_to_drop.append(index)
                break
            elif " ( GENERAL )" in str(item):
                college_name = str(item).split(" ( GENERAL )")[1].strip()
                rows_to_drop.append(index)
                break
            elif re.search('1G', str(item)):
                rows_to_drop.append(index)
                break
        else:
            df.at[index, 'College Code'] = college_code
            df.at[index, 'College Name'] = college_name.strip()

    df.drop(rows_to_drop, inplace=True)

    df.replace("--", "", inplace=True)
    df.replace("\n", " ", inplace=True, regex=True)
    df["Round"] = "Mock2"
    df["College Name"].replace("", "University of Visvesvaraya College of Engineering Bangalore", inplace=True)
    df["College Code"].replace("", "E001", inplace=True)
    df.replace("", None, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    df.rename(columns={"Unnamed: 0": "Branch"}, inplace=True)
    df["College Name"] = df["College Name"].str.replace(" ", " ")
    df["College Name"] = df["College Name"].str.replace(" ", " ")



    return df


def main():
    st.title("Cutoff File Processor")

    uploaded_file = st.file_uploader("Choose an XLSX file", type="xlsx")

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file, "Table 1", engine='openpyxl', skiprows=1)

        st.subheader("Original Data")
        st.dataframe(df)

        processed_df = process_dataframe(df)

        st.subheader("Processed Data")
        st.dataframe(processed_df)

        csv = processed_df.to_csv(index=False)
        st.download_button(
            label="Download processed data as CSV",
            data=csv,
            file_name="processed_cutoffs.csv",
            mime="text/csv",
        )

if __name__ == '__main__':
    main()