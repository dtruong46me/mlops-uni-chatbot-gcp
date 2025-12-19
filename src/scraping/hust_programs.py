import os
import json

import requests
from bs4 import BeautifulSoup
import urllib3

__root__ = os.getcwd()

RAW_DATA_PATH = os.path.join(__root__, "data", "raw")
if not os.path.exists(RAW_DATA_PATH):
    os.makedirs(RAW_DATA_PATH)
SAVED_PATH = os.path.join(RAW_DATA_PATH, "hust_programs.json")


# Suppress insecure request warnings (since verify=False is used)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc"

try:
    response = requests.get(url, verify=False)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    accordion_items = soup.find_all('div', class_='accordion-item')

    data_list = []

    for item in accordion_items:
        # 1. Extract Header Information (Title and Code)
        header_tag = item.find('h3', class_='accordion-header') # type: ignore
        full_title = header_tag.get_text(strip=True) if header_tag else ""
        
        # 2. Extract Language and Admission Code
        # We look for the paragraphs in the left-box
        left_box = item.find('div', class_='left-box') # type: ignore
        
        language = ""
        admission_code = ""
        if left_box:
            p_tags = left_box.find_all('p') # type: ignore
            for p in p_tags:
                text = p.get_text(strip=True)
                if "Ngôn ngữ đào tạo" in text:
                    language = text.split(":")[-1].strip()
                if "Mã xét tuyển" in text:
                    admission_code = text.split(":")[-1].strip()

        # 3. Extract Admission Methods (DGTD and THPT)
        meta_div = item.find('div', class_='meta') # type: ignore
        admission_methods = {}
        
        if meta_div:
            rows = meta_div.find_all('div', class_='row') # type: ignore
            for row in rows:
                cols = row.find_all('div') # type: ignore
                if len(cols) >= 2:
                    method_name = cols[0].get_text(strip=True).replace(":", "")
                    
                    # Get combinations (A00, B00, etc.)
                    combinations = [a.get_text(strip=True) for a in row.find_all('a', class_='ds-tooltip')] # type: ignore
                    
                    # Get standard point (Điểm chuẩn)
                    point_span = row.find('span', class_='red-bold') # type: ignore
                    point = point_span.get_text(strip=True) if point_span else "N/A"
                    
                    admission_methods[method_name] = {
                        "combinations": combinations,
                        "cutoff_point": point
                    }

        # 4. Extract Quota (Chỉ tiêu)
        quota_tag = item.find('p', id='quanlity') # type: ignore
        quota = quota_tag.find('strong').get_text(strip=True) if quota_tag and quota_tag.find('strong') else "" # type: ignore

        # 5. Extract School/Faculty
        # It's usually the last <p> in left-box containing the map marker icon
        school = ""
        school_icon = item.find('i', class_='fa-map-marker-alt') # type: ignore
        if school_icon:
            school = school_icon.parent.get_text(strip=True) # type: ignore

        # 6. Extract Detail Link
        link_tag = item.find('a', class_='read-more') # type: ignore
        detail_url = link_tag['href'] if link_tag else "" # type: ignore

        # Construct the object
        program_data = {
            "title": full_title,
            "admission_code": admission_code,
            "language": language,
            "quota": quota,
            "school": school,
            "admission_methods": admission_methods,
            "detail_url": detail_url
        }
        
        data_list.append(program_data)

    # Save to JSON file
    with open(SAVED_PATH, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=4)

    print(f"Successfully scraped {len(data_list)} programs and saved to {SAVED_PATH}")

except Exception as e:
    print(f"An error occurred: {e}")