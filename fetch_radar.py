import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://file.royalrain.go.th/opendata/radar_data/cappi/"
BASE_SAVE_DIR = "radar-images"

STATIONS = {
    "sattahip": "sattahip",
    "omkoi": "omkoi",
    "phnom": "phnom",
    "takli": "takli",
    "phimai": "phimai"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def extract_date_from_filename(filename):
    match = re.search(r'(\d{4})(\d{2})(\d{2})\d+', filename)
    if match:
        return match.groups()
    now = datetime.datetime.now()
    return str(now.year), f"{now.month:02d}", f"{now.day:02d}"

def process_station(station_name, station_param):
    url = f"{BASE_URL}?station={station_param}"
    print(f"\n--- เริ่มประมวลผลสถานี: {station_name} ---")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[{station_name}] เข้าหน้าเว็บไม่สำเร็จ Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        latest_img_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if ('dBZ' in src or 'cappi' in src) and 'logo' not in src:
                latest_img_url = src if src.startswith('http') else f"https://file.royalrain.go.th{src}"
                break

        if not latest_img_url:
            print(f"[{station_name}] ไม่พบ URL ภาพเรดาร์ในหน้าเว็บ")
            return

        filename = os.path.basename(latest_img_url.split('?')[0])
        year, month, day = extract_date_from_filename(filename)

        save_dir = os.path.join(BASE_SAVE_DIR, station_name, year, month, day)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            print(f"[{station_name}] มีภาพนี้ในระบบแล้ว ข้าม: {filename}")
            return

        img_res = requests.get(latest_img_url, headers=headers, timeout=15)
        if img_res.status_code == 200 and len(img_res.content) > 3000:
            with open(filepath, 'wb') as f:
                f.write(img_res.content)
            file_size_kb = len(img_res.content) / 1024
            print(f"[{station_name}] บันทึกภาพสำเร็จ! -> {year}/{month}/{day}/{filename} ({file_size_kb:.2f} KB)")
        else:
            print(f"[{station_name}] ดาวน์โหลดล้มเหลว หรือไฟล์ขนาดผิดปกติ")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    for station_name, param in STATIONS.items():
        process_station(station_name, param)

if __name__ == "__main__":
    main()
