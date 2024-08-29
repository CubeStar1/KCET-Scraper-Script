import asyncio
import time
from pathlib import Path
import pandas as pd
import re
from bs4 import BeautifulSoup
import aiohttp
from roll_no_generator import get_roll_no_list_from_file

# Constants
KCET_RESULTS_URL = "https://keaonline.karnataka.gov.in/ugcet_result_2024/main/resultscheck.php"
NUM_CONCURRENT_REQUESTS = 50
BASE_PATH = Path("../KCET/2024/test")
INPUT_FILE_PATH = BASE_PATH / "kcet_A_Z_valid.xlsx"
HTML_FILE_PATH = BASE_PATH / "raw_html/final_html_test.xlsx"
RANK_FILE_PATH = BASE_PATH / "raw_results/results_test.xlsx"
STATUS_FILE_PATH = BASE_PATH / "raw_status/status_test.xlsx"
CUTOFF_RANK = 2000
PROCESSED_RESULTS_FILE_PATH = BASE_PATH / "processed_results/processed_results.xlsx"
PROCESSED_STATUS_FILE_PATH = BASE_PATH / "processed_results/processed_status.xlsx"
PROCESSED_RESULTS_CUTOFF_FILE_PATH = BASE_PATH / "processed_results/processed_results_cutoff.xlsx"


def extract_course_info(course_string):
    pattern = r'(.*?)\s+([A-Z]\d+[A-Z]+)\s*(\(\s*Rs\.[^)]*\))?'
    match = re.match(pattern, course_string, re.DOTALL)

    if match:
        course_name = match.group(1).strip()
        course_code = match.group(2)
        course_fee = match.group(3) if match.group(3) else ""
        course_fee = course_fee.strip('( )') if course_fee else ""
        return pd.Series([course_name, course_code, course_fee])
    else:
        return pd.Series([course_string, "", ""])


async def fetch_student_details(session, roll_no, status_dict):
    max_retries = 5
    form_data = {
        'txtrollno': roll_no,
        'Submit': 'Submit'
    }

    for _ in range(max_retries):
        try:
            async with session.post(KCET_RESULTS_URL, data=form_data) as response:
                content = await response.text()
                soup = BeautifulSoup(content, 'lxml')

                # Check for the congratulations message
                congrats_table = soup.find('table', {'width': '70%', 'border': '1', 'align': 'center'})
                print(congrats_table)
                if congrats_table and "CONGRATULATIONS" in congrats_table.text:
                    status_dict[roll_no] = "Seat allotted"
                    # Find the table with the student details
                    result_table = soup.find_all('table', {'width': '70%', 'border': '1', 'align': 'center'})[1]
                    if result_table:
                        return str(result_table)
                elif "Invalid CET number" in content:
                    status_dict[roll_no] = "Invalid CET Number"
                elif "You have not been allotted any seat." in content:
                    status_dict[roll_no] = "No seat allotted"
                else:
                    status_dict[roll_no] = "Unexpected content"
                return None
        except Exception as e:
            print(f"Retry for {roll_no}: {str(e)}")

    status_dict[roll_no] = "Failed to load page"
    return None


async def scrape_batch(roll_list, status_dict):
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(fetch_student_details(session, roll_no, status_dict)) for roll_no in roll_list]
        return await asyncio.gather(*tasks)


def parse_results(results, data, rank_template):
    try:
        for html in results:
            if html is None:
                continue
            soup = BeautifulSoup(html, 'lxml')
            result_rows = soup.find_all('tr')
            rank = rank_template.copy()
            for row in result_rows:
                tds = row.find_all('td')
                if len(tds) < 2:
                    continue
                element = ' '.join(tds[0].text.replace("\n", "").strip().split())
                value = ' '.join(tds[1].text.replace("\n", "").strip().split())
                if element in rank:
                    rank[element] = value
            data.loc[len(data.index)] = rank
    except Exception as e:
        print("Error parsing results: ", e)



def process_results(results_df, cutoff_rank):
    try:

        results_df.dropna(inplace=True)
        engineering_df = results_df.loc[results_df['Rank :'].str.contains("Engineering", regex=True, na=False)]
        # engineering_df = results_df.loc[results_df['Rank :'].str.contains("Medical", regex=True, na=False)]

        engineering_df[["Stream", "Rank"]] = engineering_df['Rank :'].str.split('-', expand=True)
        engineering_df['Rank'] = engineering_df['Rank'].str.strip(",").str.strip()
        if engineering_df['Rank'].str.contains('G', na=False).any():
            engineering_df[["ActualRank", "Code"]] = engineering_df['Rank'].str.split('G', expand=True)
        else:
            engineering_df['ActualRank'] = engineering_df['Rank']
            engineering_df['Code'] = ""
        engineering_df[["Course Name", "Course Code", "Course Fee"]] = engineering_df['Course allotted:'].apply(
            extract_course_info)
        engineering_df['ActualRank'] = pd.to_numeric(engineering_df['ActualRank'])
        engineering_df["Course Fee"] = engineering_df["Course Fee"].str.replace('Rs.', '',
                                                                                regex=False).str.strip().str.replace(',',
                                                                                                                     '')
        engineering_df["Course Fee"] = pd.to_numeric(engineering_df["Course Fee"], errors='coerce')

        required_df = engineering_df.loc[engineering_df["ActualRank"] <= cutoff_rank]
        required_df.drop(['Code', 'Rank :', 'Course allotted:'], axis=1, inplace=True)
        engineering_df.drop(['Code', 'Rank :', 'Course allotted:'], axis=1, inplace=True)

        engineering_df.to_excel(PROCESSED_RESULTS_FILE_PATH, index=False)
        required_df.to_excel(PROCESSED_RESULTS_CUTOFF_FILE_PATH, index=False)
        return engineering_df, required_df
    except Exception as e:
        print("Error processing results: ", e)

def process_status(stat_df):
    required_stat_df = stat_df.loc[
        (stat_df["Reason"] == "Unexpected Error") | (stat_df["Reason"] == "Pre-Submit failure")]
    required_stat_df.to_excel(PROCESSED_STATUS_FILE_PATH, index=False)
    return required_stat_df

def main_script():
    rank_template = {
        "CET No:": "",
        "Name of the Candidate:": "",
        "Verified Category :": "",
        "Rank :": "",
        "Discipline :": "",
        "College allotted :": "",
        "Category allotted :": "",
        "Course allotted:": "",
        "Serial Number of the Allotted Option:": ""
    }

    df = pd.DataFrame(columns=list(rank_template.keys()))
    df_status = pd.DataFrame(columns=["CET No", "Reason"])
    df_html = pd.DataFrame(columns=["HTML"])

    for file_path in [HTML_FILE_PATH, RANK_FILE_PATH, STATUS_FILE_PATH]:
        if file_path.is_file():
            if file_path == HTML_FILE_PATH:
                df_html = pd.read_excel(file_path, engine='openpyxl')
            elif file_path == RANK_FILE_PATH:
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                df_status = pd.read_excel(file_path, engine='openpyxl')
                df_status = df_status.drop_duplicates(subset=["CET No"])
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame().to_excel(file_path, index=False)

    # Generates batches of roll numbers from a file
    # roll_no_batches = [["BB888", "AA377", "AU860"]]

    roll_no_batches = get_roll_no_list_from_file(INPUT_FILE_PATH, "CET No", NUM_CONCURRENT_REQUESTS)
    status_dict = {}

    start_time = time.time()

    for batch_number, batch in enumerate(roll_no_batches):
        results = asyncio.run(scrape_batch(batch, status_dict))

        new_html_df = pd.DataFrame({"HTML": results})
        df_html = pd.concat([df_html, new_html_df], ignore_index=True)
        df_html.to_excel(HTML_FILE_PATH, index=False)

        parse_results(results, df, rank_template)
        df.to_excel(RANK_FILE_PATH, index=False)

        new_status_df = pd.DataFrame({"CET No": status_dict.keys(), "Reason": status_dict.values()})
        df_status = pd.concat([df_status, new_status_df], ignore_index=True)
        df_status.drop_duplicates(subset=["CET No"], inplace=True)
        df_status.to_excel(STATUS_FILE_PATH, index=False)

        print(f"Batch {batch_number + 1} completed. Elapsed time: {time.time() - start_time:.2f} seconds")
        time.sleep(1)

    print(f"Scraping completed. Elapsed time: {time.time() - start_time:.2f} seconds")

    # Process the results
    engineering_df, required_df = process_results(df, CUTOFF_RANK)
    print("Results processed and saved.")

    # Process the status
    required_stat_df = process_status(df_status)
    print("Status processed and saved.")

    return engineering_df, required_df, required_stat_df


if __name__ == '__main__':
    engineering_results, required_results, required_status = main_script()
    print("Engineering Results Sample:")
    print(engineering_results.head())
    print("\nRequired Results Sample:")
    print(required_results.head())
    print("\nRequired Status Sample:")
    print(required_status.head())