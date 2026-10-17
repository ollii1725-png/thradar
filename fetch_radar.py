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

def parse_filename_to_thai_date(filename):
    """
    แกะเวลา UTC จากชื่อไฟล์ (เช่น 2026101617290000dBZ -> YYYY=2026, MM=10, DD=16, HH=17, MM=29)
    แล้วบวกเพิ่ม 7 ชั่วโมง ให้เป็นเวลาไทย (UTC+7)
    """
    match = re.search(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})', filename)
    if match:
        year, month, day, hour, minute = match.groups()
        # สร้างวัตถุ datetime เป็นเวลา UTC
        utc_dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        # แปลงเป็นเวลาไทย (UTC + 7 Hours)
        thai_dt = utc_dt + datetime.timedelta(hours=7)
        
        # คืนค่า (ปีไทย, เดือนไทย, วันไทย)
        return thai_dt.strftime("%Y"), thai_dt.strftime("%m"), thai_dt.strftime("%d")
    
    # กรณีชื่อไฟล์ไม่มีรูปแบบเวลามาตรฐาน ให้ใช้เวลาปัจจุบัน (UTC+7)
    now_thai = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    return now_thai.strftime("%Y"), now_thai.strftime("%m"), now_thai.strftime("%d")

def apply_logo_only(image_path, target_width=800):
    """ย่อขนาดภาพเพื่อประหยัดพื้นที่ + ประทับภาพโลโก้ไว้ที่มุมซ้ายบน"""
    try:
        with Image.open(image_path).convert("RGBA") as base_img:
            
            # 1. ย่อขนาดภาพเรดาร์ (Resize) รักษาอัตราส่วนเดิม
            if base_img.width > target_width:
                aspect_ratio = base_img.height / base_img.width
                target_height = int(target_width * aspect_ratio)
                base_img = base_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # 2. แปะภาพโลโก้ที่มุมซ้ายบน (ถ้ามีไฟล์ LOGO_PATH)
            if os.path.exists(LOGO_PATH):
                with Image.open(LOGO_PATH).convert("RGBA") as logo:
                    logo_width = 60 # ปรับขนาดโลโก้ให้พอดีกับภาพที่ย่อแล้ว
                    aspect_ratio = logo.height / logo.width
                    logo_height = int(logo_width * aspect_ratio)
                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                    
                    base_img.paste(logo, (10, 10), logo)

            # 3. บันทึกภาพทับไฟล์เดิมในรูปแบบ RGB พร้อมบีบอัดความจุ
            base_img.convert("RGB").save(image_path, "PNG", optimize=True)
            print(f"   [+] ย่อขนาดภาพเหลือความกว้าง {target_width}px เรียบร้อย")

    except Exception as e:
        print(f"   [!] เกิดข้อผิดพลาดในการปรับขนาดภาพ: {e}")
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

        # คำนวณวันที่ปัจจุบันของไทย (UTC+7)
        now_thai = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        today_year = now_thai.strftime("%Y")
        today_month = now_thai.strftime("%m")
        today_day = now_thai.strftime("%d")

        download_count = 0
        skip_count = 0

        # 2. วนลูปเช็คภาพทั้งหมด
        for img_url in img_urls:
            filename = os.path.basename(img_url.split('?')[0])
            
            # แปลงเวลาในชื่อไฟล์จาก UTC เป็นเวลาไทย
            thai_year, thai_month, thai_day = parse_filename_to_thai_date(filename)

            # เช็คว่าหลังจากแปลงเป็นเวลาไทยแล้ว ภาพนั้นตรงกับ "วันนี้ของไทย" หรือไม่
            if thai_year == today_year and thai_month == today_month and thai_day == today_day:
                
                # จัดเก็บในโฟลเดอร์ตามวันที่เวลาไทย
                save_dir = os.path.join(BASE_SAVE_DIR, station_name, thai_year, thai_month, thai_day)
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)

                # เช็คว่ามีไฟล์นี้อยู่ในโฟลเดอร์แล้วหรือยัง
                if os.path.exists(filepath):
                    skip_count += 1
                    continue

                # ดาวน์โหลดและใส่โลโก้
                img_res = requests.get(img_url, headers=headers, timeout=15)
                if img_res.status_code == 200 and len(img_res.content) > 3000:
                    with open(filepath, 'wb') as f:
                        f.write(img_res.content)

                    apply_logo_only(filepath)
                    download_count += 1
                    print(f"   [+] โหลดภาพย้อนหลังเพิ่ม: {filename} (เวลาไทย: {thai_year}-{thai_month}-{thai_day})")

        print(f"[{station_name}] สรุปวันนี้ ({today_year}-{today_month}-{today_day}): โหลดเพิ่ม {download_count} ภาพ | มีอยู่แล้ว {skip_count} ภาพ")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    for station_name, label in STATIONS.items():
        process_station_check_all_today(station_name, label)

if __name__ == "__main__":
    main()
