from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import json
from datetime import datetime

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
        self.results = []

    def setup_driver(self):
        if self.driver is None:
            self.driver = webdriver.Chrome(options=self.options)
            self.driver.implicitly_wait(5)  # Add implicit wait

    def quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def load_page(self):
        try:
            self.driver.get(self.url)
            # Wait for input field as indicator of page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "regno"))
            )
            return True
        except Exception as e:
            print(f"Error loading page: {e}")
            return False

    def extract_relevant_info(self):
        """Extract information with better error handling"""
        try:
            result_data = {
                "personal_info": {},
                "marks_info": {"subjects": []},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Wait for tables to be present
            tables = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
            )

            # Extract personal information
            personal_table = None
            for table in tables:
                if table.get_attribute("width") == "50%":
                    personal_table = table
                    break

            if personal_table:
                rows = personal_table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 2:
                        key = cells[0].text.strip().replace(':', '').strip()
                        value = cells[1].text.strip()
                        if key and value:  # Only add if both key and value exist
                            result_data["personal_info"][key] = value

            # Extract Category
            try:
                category_element = self.driver.find_element(
                    By.XPATH, "//font[contains(text(), 'Category')]"
                )
                category_text = category_element.text.strip()
                if ":" in category_text:
                    result_data["personal_info"]["Category"] = category_text.split(":")[1].strip()
            except NoSuchElementException:
                result_data["personal_info"]["Category"] = "Not Found"

            # Extract Marks Information
            marks_tables = self.driver.find_elements(
                By.XPATH, "//table[@width='75%']"
            )
            
            for table in marks_tables:
                if "SUBJECT NAME" in table.text:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    # Extract paper type
                    if len(rows) > 0:
                        paper_text = rows[0].text.strip()
                        if paper_text:
                            result_data["marks_info"]["paper_type"] = paper_text

                    # Extract subject marks
                    for row in rows[2:]:  # Skip header rows
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 2:
                            subject = cells[0].text.strip()
                            marks = cells[1].text.strip()
                            if subject and marks and "out of" in marks.lower():
                                subject_data = {
                                    "subject": subject,
                                    "marks": marks
                                }
                                result_data["marks_info"]["subjects"].append(subject_data)
                                
                                if subject.lower() == "total":
                                    result_data["marks_info"]["total_marks"] = marks
                                    # Try to get percentage
                                    try:
                                        next_row = rows[rows.index(row) + 1]
                                        percentage_text = next_row.find_element(By.TAG_NAME, "td").text
                                        if "%" in percentage_text:
                                            result_data["marks_info"]["percentage"] = percentage_text.strip()
                                    except (IndexError, NoSuchElementException):
                                        pass

            # Validate that we have essential data
            if not result_data["personal_info"] or not result_data["marks_info"]["subjects"]:
                print("Missing essential data in the response")
                return None

            return result_data

        except Exception as e:
            print(f"Error in extract_relevant_info: {str(e)}")
            return None

    def fetch_result(self, roll_number):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Load page and check success
                if not self.load_page():
                    retry_count += 1
                    time.sleep(2)
                    continue

                # Find and fill input field
                input_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "regno"))
                )
                input_field.clear()
                input_field.send_keys(str(roll_number))

                # Find and click submit button
                submit_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.NAME, "B1"))
                )
                submit_button.click()

                # Wait for result content or error message
                time.sleep(2)  # Give page time to load
                
                # Check for error message
                try:
                    error_msg = self.driver.find_element(
                        By.XPATH, "//font[contains(text(), 'Invalid') or contains(text(), 'Error')]"
                    )
                    print(f"Roll number {roll_number}: {error_msg.text}")
                    return False
                except NoSuchElementException:
                    pass

                # Extract information
                result_data = self.extract_relevant_info()
                if result_data:
                    self.results.append(result_data)
                    return True

                retry_count += 1
                time.sleep(2)

            except Exception as e:
                print(f"Error processing roll number {roll_number}: {str(e)}")
                retry_count += 1
                time.sleep(2)

        return False

    def save_results(self, filename="ctet_results.json"):
        if self.results:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=4, ensure_ascii=False)
                print(f"Results saved to {filename}")
            except Exception as e:
                print(f"Error saving results: {e}")
        else:
            print("No results to save")

    def process_roll_numbers(self, start_roll, end_roll, delay=2):
        try:
            self.setup_driver()
            
            for roll in range(start_roll, end_roll + 1):
                print(f"\nProcessing roll number: {roll}")
                success = self.fetch_result(roll)
                
                if success:
                    print(f"Successfully processed roll number: {roll}")
                else:
                    print(f"Failed to process roll number: {roll}")
                
                time.sleep(delay)

        except KeyboardInterrupt:
            print("\nScraping interrupted by user")
        except Exception as e:
            print(f"\nError in main processing loop: {e}")
        finally:
            self.save_results()
            self.quit_driver()

def main():
    scraper = CTETResultScraper(headless=True)
    start_roll = 218100001
    end_roll = 218100005
    scraper.process_roll_numbers(start_roll, end_roll)

if __name__ == "__main__":
    main()