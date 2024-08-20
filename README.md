# KCET Scraper

This project is a web scraper designed to extract and process KCET (Karnataka Common Entrance Test) counselling results from the official KEA (Karnataka Examinations Authority) website. The scraper uses Playwright for browser automation and BeautifulSoup for HTML parsing.

## Features

- Scrapes KCET results for a list of roll numbers.
- Extracts and processes course information.
- Saves raw HTML, results, and status to Excel files.
- Processes and filters results based on a cutoff rank.

## Requirements

- Python 3.7+
- Playwright
- BeautifulSoup4
- Pandas
- openpyxl

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/CubeStar1/KCET-Scraper-Script.git
    cd KCET-Scraper-Script
    ```

2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Install Playwright browsers:
    ```sh
    playwright install
    ```

## Usage

1. Update the constants in `async/kcet_rank_extraction.py` as needed:
    - `KCET_RESULTS_URL`: URL to scrape.
    - `NUM_BROWSER_TABS`: Number of browser tabs to open.
    - `OPEN_BROWSER`: Set to `False` to run headless.
    - `BASE_PATH`: Base path for saving files.
    - `CUTOFF_RANK`: Rank cutoff for filtering results.

2. Run the script:
    ```sh
    python async/kcet_rank_extraction.py
    ```

## File Structure

- `async/kcet_rank_extraction.py`: Main script for scraping and processing KCET results.
- `requirements.txt`: List of required Python packages.
- `KCET/2024/`: Folder containing the processed results.

## Output Files

- `raw_html/final_html_test.xlsx`: Raw HTML content of the scraped results.
- `raw_results/results_test.xlsx`: Extracted results.
- `raw_status/status_test.xlsx`: Status of each roll number.
- `processed_results/processed_results.xlsx`: Processed results.
- `processed_results/processed_results_cutoff.xlsx`: Processed results filtered by cutoff rank.
- `processed_results/processed_status.xlsx`: Processed status.
