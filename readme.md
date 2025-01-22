# CTET Result Scraper and JSON to Excel Converter

## Features
- **ctet_python.py**: Scrape CTET results to JSON.
- **JSONtoExcel.py**: Convert JSON to Excel with color-coded Roll No cells.

---

## Prerequisites

1. **Python 3.x**  
   Download from [python.org](https://www.python.org/).

2. **Install Libraries**  
   ```bash
   pip install selenium openpyxl tqdm
   ```

3. **ChromeDriver**  
   ```bash
   # Download from https://sites.google.com/chromium.org/driver/
   # Add ChromeDriver to your system PATH
   ```

---

## Usage

1. **Scrape Results**  
   ```bash
   python ctet_python.py
   ```
   - Edit `start_roll` and `end_roll` in the script.
   - Output: `ctet_results.json`.

2. **Convert to Excel**  
   ```bash
   python JSONtoExcel.py
   ```
   - Input: `ctet_results.json`.
   - Output: `ctet_results.xlsx` (Roll No cells: 🔴 <60%, 🟢 >=60%).

---

## Example JSON Output
```json
[
  {
    "personal_info": {
      "Roll No": "218100041",
      "Name": "KM DIMPAL",
      "Mother's Name": "MEENA DEVI"
    },
    "marks_info": {
      "subjects": [
        {"subject": "Mathematics & Science", "marks": "33 out of 60 (Mathematics - 19 Science - 14)"}
      ]
    }
  }
]
```

---

## Notes
- Match ChromeDriver version to your Chrome browser.
- Avoid excessive requests to the CTET website.

---

## License
MIT License.