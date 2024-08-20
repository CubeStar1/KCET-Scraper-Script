import asyncio
import time
from pathlib import Path
import pandas as pd
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from roll_no_generator import generate_roll_no_list

# Constants
KCET_RESULTS_URL = "https://keaonline.karnataka.gov.in/UGCET_RESULT_2024/main/results.php" # URL to scrape
NUM_BROWSER_TABS = 100 # Number of browser tabs to open
OPEN_BROWSER = True # Set this to false if you want to run it headless without opening browser, by default it is set to False
BASE_PATH = Path("../KCET/2024")
HTML_FILE_PATH = BASE_PATH / "raw_html/final_html_test.xlsx"
RANK_FILE_PATH = BASE_PATH / "raw_results/results_test.xlsx" # Path to save the results
STATUS_FILE_PATH = BASE_PATH / "raw_status/status_test.xlsx"
CUTOFF_RANK = 2000
PROCESSED_RESULTS_FILE_PATH = BASE_PATH / "processed_results/processed_results.xlsx"
PROCESSED_STATUS_FILE_PATH = BASE_PATH / "processed_results/processed_status.xlsx" # Path to save the processed status
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


async def fetch_student_details(context, roll_no, status_dict):
    max_retries = 5
    page = await context.new_page()

    for _ in range(max_retries):
        try:
            await page.goto(KCET_RESULTS_URL, timeout=100000)
            await page.fill("#txtrollno", roll_no)
            await page.get_by_role("button", name="Submit").click()
            await page.wait_for_load_state()
            await page.wait_for_timeout(100)
            break
        except Exception as e:
            print(f"Retry for {roll_no}: {str(e)}")
    else:
        status_dict[roll_no] = "Failed to load page"
        await page.close()
        return None

    try:
        content = await page.locator(
            "body > table:nth-child(10) > tbody > tr:nth-child(5) > td > table:nth-child(1)").text_content()
        if "CONGRATULATIONS" in content:
            status_dict[roll_no] = "Seat allotted"
            result = await page.inner_html(
                "body > table:nth-child(10) > tbody > tr:nth-child(5) > td > table:nth-child(2) > tbody > tr:nth-child(2) > td > table > tbody > tr > td:nth-child(2) > table")
            await page.close()
            return result
        elif "Invalid CET number" in content:
            status_dict[roll_no] = "Invalid CET Number"
        elif "You have not been allotted any seat." in content:
            status_dict[roll_no] = "No seat allotted"
        else:
            status_dict[roll_no] = "Unexpected content"
    except Exception as e:
        status_dict[roll_no] = f"Error: {str(e)}"

    await page.close()
    return None


async def scrape_batch(context, roll_list, status_dict):
    tasks = [asyncio.create_task(fetch_student_details(context, roll_no, status_dict)) for roll_no in roll_list]
    return await asyncio.gather(*tasks)


async def main(roll_list, status_dict):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless= not OPEN_BROWSER)
        context = await browser.new_context()
        data = await scrape_batch(context, roll_list, status_dict)
        await context.close()
        await browser.close()
        return data


def parse_results(results, data, rank_template):
    try:
        for html in results:
            if html is None:
                continue
            soup = BeautifulSoup(html, 'lxml')
            result_rows = soup.find('tbody').find_all('tr')
            rank = rank_template.copy()
            for row in result_rows:
                tds = row.find_all('td')
                if len(tds) < 2:
                    break
                element, value = tds[0].text.strip(), tds[1].text.strip()
                if element in rank:
                    rank[element] = value
            data.loc[len(data.index)] = rank
    except:
        print("Error parsing results")


def process_results(results_df, cutoff_rank):
    try:

        results_df.dropna(inplace=True)
        engineering_df = results_df.loc[results_df['Rank :'].str.contains("Engineering", regex=True, na=False)]
        engineering_df[["Stream", "Rank"]] = engineering_df['Rank :'].str.split('-', expand=True)
        engineering_df['Rank'] = engineering_df['Rank'].str.strip(",").str.strip()
        engineering_df[["ActualRank", "Code"]] = engineering_df['Rank'].str.split('G', expand=True)
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
    except:
        print("Error processing results")

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
        "Category allotted :": "",
        "Course allotted:": "",
        "Serial Number of the Allotted Option:": ""
    }

    df = pd.DataFrame(columns = list(rank_template.keys()))
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
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame().to_excel(file_path, index=False)


    # Uncomment below for testing purposes
    # roll_no_batches = [["BB888", "AA377", "AU860"]]

    # Generates batches of roll numbers, each batch containing 50 roll numbers
    # In this case, its generates roll numbers starting from AA001 to AZ999
    roll_no_batches = generate_roll_no_list("A", "A", NUM_BROWSER_TABS)
    status_dict = {}

    start_time = time.time()


    for batch_number, batch in enumerate(roll_no_batches):
        results = asyncio.run(main(batch, status_dict))

        new_html_df = pd.DataFrame({"HTML": results})
        df_html = pd.concat([df_html, new_html_df], ignore_index=True)
        df_html.to_excel(HTML_FILE_PATH, index=False)

        parse_results(results, df, rank_template)
        df.to_excel(RANK_FILE_PATH, index=False)

        new_status_df = pd.DataFrame({"CET No": status_dict.keys(), "Reason": status_dict.values()})
        df_status = pd.concat([df_status, new_status_df], ignore_index=True)
        df_status.to_excel(STATUS_FILE_PATH, index=False)

        print(f"Batch {batch_number+1} completed. Elapsed time: {time.time() - start_time:.2f} seconds")
        time.sleep(0.1)

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