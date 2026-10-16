import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE_URL = "https://file.royalrain.go.th/opendata/radar_data/cappi/"
BASE_SAVE_DIR = "radar-images"
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
    """แกะ ปี/เดือน/วัน จากชื่อไฟล์ เช่น 2026101708480000dBZ -> 2026, 10, 17"""
    match = re.search(r'(\d{4})(\d{2})(\d{2})\d+', filename)
    if match:
        return match.groups()
    now = datetime.datetime.now()
    return str(now.year), f"{now.month:02d}", f"{now.day:02d}"

def apply_logo_only(image_path):
    """ประทับภาพโลโก้ไว้ที่มุมซ้ายบน"""
    try:
        if os.path.exists(LOGO_PATH):
            with Image.open(image_path).convert("RGBA") as base_img:
                with Image.open(LOGO_PATH).convert("RGBA") as logo:
                    logo_width = 80
                    aspect_ratio = logo.height / logo.width
                    logo_height = int(logo_width * aspect_ratio)
                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                    
                    base_img.paste(logo, (15, 15), logo)

                base_img.convert("RGB").save(image_path)
    except Exception as e:
        print(f"   [!] เกิดข้อผิดพลาดในการใส่โลโก้: {e}")

def process_station_check_all_today(station_name, station_label):
    url = f"{BASE_URL}?station={station_name}"
    print(f"\n--- เริ่มตรวจสอบภาพย้อนหลังประจำวัน สถานี: {station_name} ({station_label}) ---")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[{station_name}] เข้าหน้าเว็บไม่สำเร็จ Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. กวาดหา URL ภาพเรดาร์ทั้งหมดที่มีบนหน้าเว็บ
        img_urls = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if ('dBZ' in src or 'cappi' in src) and 'logo' not in src:
                full_url = src if src.startswith('http') else f"https://file.royalrain.go.th{src}"
                if full_url not in img_urls:
                    img_urls.append(full_url)

        if not img_urls:
            print(f"[{station_name}] ไม่พบภาพเรดาร์ในหน้าเว็บ")
            return

        # คำนวณวันที่ปัจจุบัน (ปี, เดือน, วัน)
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=7) # เวลาไทย UTC+7
        today_year = now.strftime("%Y")
        today_month = now.strftime("%m")
        today_day = now.strftime("%d")

        download_count = 0
        skip_count = 0

        # 2. วนลูปเช็คภาพทั้งหมดในหน้าเว็บ
        for img_url in img_urls:
            filename = os.path.basename(img_url.split('?')[0])
            year, month, day = extract_date_from_filename(filename)

            # กรองเอาเฉพาะภาพที่เป็นของ "วันนี้" เท่านั้น
            if year == today_year and month == today_month and day == today_day:
                save_dir = os.path.join(BASE_SAVE_DIR, station_name, year, month, day)
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)

                # เช็คว่ามีไฟล์นี้อยู่ในโฟลเดอร์แล้วหรือยัง
                if os.path.exists(filepath):
                    skip_count += 1
                    continue

                # ถ้ายังไม่มี ให้ดาวน์โหลดและประทับโลโก้
                img_res = requests.get(img_url, headers=headers, timeout=15)
                if img_res.status_code == 200 and len(img_res.content) > 3000:
                    with open(filepath, 'wb') as f:
                        f.write(img_res.content)

                    apply_logo_only(filepath)
                    download_count += 1
                    print(f"   [+] โหลดภาพย้อนหลังเพิ่ม: {filename}")

        print(f"[{station_name}] สรุปวันนี้: โหลดเพิ่ม {download_count} ภาพ | มีอยู่แล้ว {skip_count} ภาพ (ครบสมบูรณ์)")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    for station_name, label in STATIONS.items():
        process_station_check_all_today(station_name, label)

if __name__ == "__main__":
    main()
