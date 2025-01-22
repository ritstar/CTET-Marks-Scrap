from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
from datetime import datetime
import concurrent.futures
from threading import Lock
from tqdm import tqdm  # For progress bar

class CTETResultScraper:
    def __init__(self, headless=True):
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.driver = None
        self.url = "https://cbseresults.nic.in/CtetDec24/CtetDec24q.htm"
        self.lock = Lock()
        self.all_results = []

    def setup_driver(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.implicitly_wait(5)

    def quit_driver(self):
        if self.driver:
            self.driver.quit()

    def load_page(self):
        try:
            self.driver.get(self.url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "regno"))
            )
            return True
        except Exception as e:
            print(f"Error loading page: {e}")
            return False

    def extract_relevant_info(self):
        try:
            result_data = {
                "personal_info": {},
                "marks_info": {"subjects": []},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            tables = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )

            # Personal information extraction
            personal_table = next((t for t in tables if t.get_attribute("width") == "50%"), None)
            if personal_table:
                for row in personal_table.find_elements(By.TAG_NAME, "tr"):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 2:
                        key = cells[0].text.strip().replace(':', '')
                        value = cells[1].text.strip()
                        if key and value:
                            result_data["personal_info"][key] = value

            # Category extraction
            try:
                category_element = self.driver.find_element(
                    By.XPATH, "//font[contains(text(), 'Category')]"
                )
                result_data["personal_info"]["Category"] = category_element.text.split(":")[1].strip()
            except NoSuchElementException:
                pass

            # Marks extraction
            marks_tables = self.driver.find_elements(By.XPATH, "//table[@width='75%']")
            for table in marks_tables:
                if "SUBJECT NAME" in table.text:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if rows:
                        result_data["marks_info"]["paper_type"] = rows[0].text.strip()
                    
                    for row in rows[2:]:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 2:
                            subject = cells[0].text.strip()
                            marks = cells[1].text.strip()
                            if subject and marks:
                                result_data["marks_info"]["subjects"].append({
                                    "subject": subject,
                                    "marks": marks
                                })

            return result_data if result_data["personal_info"] else None

        except Exception as e:
            print(f"Extraction error: {e}")
            return None

    def fetch_result(self, roll_number):
        for _ in range(3):  # Retry up to 3 times
            try:
                if not self.load_page():
                    continue

                input_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "regno"))
                )
                input_field.clear()
                input_field.send_keys(str(roll_number))

                submit_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.NAME, "B1"))
                )
                submit_button.click()

                time.sleep(1)  # Reduced wait time

                # Check for errors
                try:
                    error_msg = self.driver.find_element(
                        By.XPATH, "//font[contains(text(), 'Invalid')]"
                    )
                    print(f"Invalid roll {roll_number}: {error_msg.text}")
                    return False
                except NoSuchElementException:
                    pass

                # Process results
                result_data = self.extract_relevant_info()
                if result_data:
                    with self.lock:
                        self.all_results.append(result_data)
                    return True

            except Exception as e:
                print(f"Error processing {roll_number}: {e}")
                time.sleep(1)
        
        return False

def process_rolls(rolls, progress_bar=None):
    scraper = CTETResultScraper(headless=True)
    scraper.setup_driver()
    try:
        for roll in rolls:
            scraper.fetch_result(roll)
            if progress_bar:
                progress_bar.update(1)  # Update progress bar
            # Re-use session for next request
            scraper.driver.back()
            time.sleep(0.5)  # Reduced delay between consecutive requests
    finally:
        scraper.quit_driver()
    return scraper.all_results

def main():
    start_roll = 218100001
    end_roll = 218100100
    num_threads = 5  # Adjust based on your system capabilities
    
    rolls = list(range(start_roll, end_roll + 1))
    chunk_size = max(1, len(rolls) // num_threads)

    # Initialize progress bar
    with tqdm(total=len(rolls), desc="Processing Roll Numbers", unit="roll") as progress_bar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(0, len(rolls), chunk_size):
                chunk = rolls[i:i + chunk_size]
                futures.append(executor.submit(process_rolls, chunk, progress_bar))

            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as e:
                    print(f"Error in future: {e}")

    with open("ctet_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Total results collected: {len(results)}")

if __name__ == "__main__":
    main()