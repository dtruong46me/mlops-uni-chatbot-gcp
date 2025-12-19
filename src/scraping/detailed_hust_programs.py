import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

__root__ = os.getcwd()
# Create an output directory for the individual JSON files
OUTPUT_DIR = os.path.join(__root__, "data", "detailed_programs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HUST_PROGRAMS_PATH = os.path.join(__root__, "data", "raw", "hust_programs.json")

# Load the initial list of programs
if not os.path.exists(HUST_PROGRAMS_PATH):
    print(f"Error: {HUST_PROGRAMS_PATH} not found.")
    sys.exit(1)

with open(HUST_PROGRAMS_PATH, 'r', encoding='utf-8') as f:
    programs_data = json.load(f)

def clean_text(text):
    return " ".join(text.split()) if text else ""

# programs_data = programs_data[:10]  # Limit to first 10 programs for testing

for program in programs_data:
    admission_code = program.get("admission_code", "unknown").replace("/", "-")
    title = program.get("title", "")
    url = program.get("detail_url", "")

    if not url:
        continue

    print(f"Processing program: {title} ({admission_code})")

    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        contrain = soup.find('div', class_='contrain')

        if not contrain:
            print(f"   [!] Could not find 'contrain' div for {admission_code}")
            continue

        # --- 1. Extract Overview Details (tab_1) ---
        overview_data = {}
        wrap_view = contrain.find('div', class_='wrap_view') # type: ignore
        if wrap_view:
            li_items = wrap_view.find_all('li') # type: ignore
            for li in li_items:
                text = li.get_text(strip=True)
                if "Tốt nghiệp" in text: overview_data["degree"] = text.split(":")[-1].strip()
                elif "Thời gian tuyển sinh" in text: overview_data["enrollment_time"] = text.split(":")[-1].strip()
                elif "Thời gian đào tạo" in text: overview_data["duration"] = text.split(":")[-1].strip()
                elif "Học phí" in text: overview_data["tuition"] = text.split(":")[-1].strip()
            
            # Extract the introductory paragraph
            intro_p = wrap_view.find('p') # type: ignore
            if intro_p:
                overview_data["description"] = clean_text(intro_p.get_text()) # type: ignore

        # --- 2. Extract Training Program (tab_2) ---
        training_section = contrain.find('section', id='tab_2') # type: ignore
        training_info = ""
        if training_section:
            training_info = clean_text(training_section.find('div', class_='sec-con').get_text()) # type: ignore

        # --- 3. Extract Job Opportunities & Contact (tab_4) ---
        job_section = contrain.find('section', id='tab_4') # type: ignore
        jobs_data = []
        contact_info = {}
        if job_section:
            job_list = job_section.find('ul') # type: ignore
            if job_list:
                jobs_data = [clean_text(li.get_text()) for li in job_list.find_all('li')] # type: ignore
            
            # Extract contact inside job section
            sec_con = job_section.find('div', class_='sec-con') # type: ignore
            if sec_con:
                contact_text = sec_con.get_text()
                for line in contact_text.split('\n'):
                    if "Điện thoại" in line: contact_info["phone"] = line.split(":")[-1].strip()
                    if "Email" in line: contact_info["email"] = line.split(":")[-1].strip()
                    if "Địa chỉ" in line: contact_info["address"] = line.split(":")[-1].strip()

        # --- 4. Extract Management Unit (tab_5) ---
        mgmt_section = contrain.find('section', id='tab_5') # type: ignore
        management_unit = {}
        if mgmt_section:
            unit_name = mgmt_section.find('h4') # type: ignore
            management_unit["name"] = unit_name.get_text(strip=True) if unit_name else "" # type: ignore
            
            li_items = mgmt_section.find_all('li') # type: ignore
            for li in li_items:
                text = li.get_text(strip=True)
                if "Địa chỉ" in text: management_unit["address"] = text.replace("Địa chỉ:", "").strip()
                if "Hotline" in text: management_unit["hotline"] = text.replace("Hotline:", "").strip()
                if "Email" in text: management_unit["email"] = text.replace("Email:", "").strip()
                if "Website" in text: management_unit["website"] = text.replace("Website:", "").strip()

        # --- Compile final data object ---
        detailed_info = {
            "program_name": title,
            "admission_code": admission_code,
            "overview": overview_data,
            "training_program_summary": training_info,
            "job_opportunities": jobs_data,
            "contact": contact_info,
            "management_unit": management_unit,
            "source_url": url
        }

        # --- Save to individual JSON file ---
        file_path = os.path.join(OUTPUT_DIR, f"{admission_code}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_info, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"   [!] Failed to process {admission_code}: {e}")

print("\nDone! All files saved in 'data/detailed_programs/'.")