import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE_URL = "https://file.royalrain.go.th/opendata/radar_data/cappi/"
BASE_SAVE_DIR = "radar-images"

# พาธไฟล์โลโก้ที่วางไว้ใน Repository (เช่น logo.png)
LOGO_PATH = "logo.png" 

STATIONS = {
    "sattahip": "สัตหีบ",
    "omkoi": "อมก๋อย",
    "phnom": "พนม",
    "takli": "ตาคลี",
    "phimai": "พิมาย"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def extract_date_from_filename(filename):
    """แกะ ปี/เดือน/วัน จากชื่อไฟล์สำหรับสร้างโฟลเดอร์จัดเก็บ"""
    match = re.search(r'(\d{4})(\d{2})(\d{2})\d+', filename)
    if match:
        return match.groups()
    now = datetime.datetime.now()
    return str(now.year), f"{now.month:02d}", f"{now.day:02d}"

def apply_logo_only(image_path):
    """ประทับเฉพาะภาพโลโก้ไว้ที่มุมซ้ายบน"""
    try:
        if os.path.exists(LOGO_PATH):
            with Image.open(image_path).convert("RGBA") as base_img:
                with Image.open(LOGO_PATH).convert("RGBA") as logo:
                    # ปรับขนาดโลโก้ให้เหมาะสม (ความกว้าง 80px)
                    logo_width = 80
                    aspect_ratio = logo.height / logo.width
                    logo_height = int(logo_width * aspect_ratio)
                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                    
                    # แปะโลโก้ที่มุมซ้ายบน (ตำแหน่ง x=15, y=15)
                    base_img.paste(logo, (15, 15), logo)

                # บันทึกภาพทับไฟล์เดิมเป็น RGB
                base_img.convert("RGB").save(image_path)
                print(f"-> ประทับโลโก้มุมซ้ายบนสำเร็จ")
        else:
            print(f"-> ไม่พบไฟล์โลโก้ {LOGO_PATH} ข้ามการประทับภาพ")

    except Exception as e:
        print(f"-> เกิดข้อผิดพลาดในการใส่โลโก้: {e}")

def process_station(station_name, station_label):
    url = f"{BASE_URL}?station={station_name}"
    print(f"\n--- เริ่มประมวลผลสถานี: {station_name} ---")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        latest_img_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if ('dBZ' in src or 'cappi' in src) and 'logo' not in src:
                latest_img_url = src if src.startswith('http') else f"https://file.royalrain.go.th{src}"
                break

        if not latest_img_url:
            return

        filename = os.path.basename(latest_img_url.split('?')[0])
        year, month, day = extract_date_from_filename(filename)

        save_dir = os.path.join(BASE_SAVE_DIR, station_name, year, month, day)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            print(f"[{station_name}] มีภาพนี้แล้ว ข้ามการดาวน์โหลด")
            return

        img_res = requests.get(latest_img_url, headers=headers, timeout=15)
        if img_res.status_code == 200 and len(img_res.content) > 3000:
            with open(filepath, 'wb') as f:
                f.write(img_res.content)

            # ใส่เฉพาะโลโก้ที่มุมซ้ายบน
            apply_logo_only(filepath)
            print(f"[{station_name}] บันทึกสำเร็จ!")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    for station_name, label in STATIONS.items():
        process_station(station_name, label)

if __name__ == "__main__":
    main()
