import os
import re
import json
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
    "rongkwang": "ร้องกวาง"
    "phnom": "พนม",
    "takli": "ตาคลี",
    "phimai": "พิมาย"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def parse_filename_to_datetime(filename):
    """แกะปี-เดือน-วัน-เวลา (UTC) จากชื่อไฟล์ แล้วแปลงเป็น datetime เวลาไทย (UTC+7)"""
    match = re.search(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})', filename)
    if match:
        year, month, day, hour, minute = map(int, match.groups())
        utc_dt = datetime.datetime(year, month, day, hour, minute)
        thai_dt = utc_dt + datetime.timedelta(hours=7)
        return thai_dt
    return None

def apply_logo_only(image_path):
    """ประทับภาพโลโก้ไว้ที่มุมซ้ายบนบนภาพขนาดต้นฉบับ"""
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

def cleanup_old_images_24h():
    """ตรวจสอบและลบไฟล์ภาพที่มีอายุเก่าเกิน 24 ชั่วโมง"""
    print("\n--- เริ่มตรวจสอบและลบไฟล์ภาพที่เก่าเกิน 24 ชั่วโมง ---")
    now_thai = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    time_limit = now_thai - datetime.timedelta(hours=24)
    deleted_count = 0

    if not os.path.exists(BASE_SAVE_DIR):
        return

    for root, dirs, files in os.walk(BASE_SAVE_DIR):
        for file in files:
            if file.endswith('.png'):
                file_dt = parse_filename_to_datetime(file)
                if file_dt and file_dt < time_limit:
                    filepath = os.path.join(root, file)
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                        print(f"   [-] ลบไฟล์เก่าเกิน 24 ชม.: {file}")
                    except Exception as e:
                        print(f"   [!] ไม่สามารถลบไฟล์ {file}: {e}")

    for root, dirs, files in os.walk(BASE_SAVE_DIR, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                except Exception:
                    pass

    print(f"--- ทำความสะอาดเสร็จสิ้น: ลบไฟล์เก่าออกทั้งหมด {deleted_count} ภาพ ---\n")

def process_station_check_all_today(station_name, station_label):
    url = f"{BASE_URL}?station={station_name}"
    print(f"--- เริ่มดาวน์โหลดภาพ สถานี: {station_name} ({station_label}) ---")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[{station_name}] เข้าหน้าเว็บไม่สำเร็จ Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. ดึงภาพลำดับแรกสุดจาก div.carousel-item.active
        first_item = soup.find('div', class_=re.compile(r'carousel-item.*active'))
        if not first_item:
            first_item = soup.find('div', class_='carousel-item')
            
        latest_info = {}
        if first_item:
            img_tag = first_item.find('img')
            if img_tag and img_tag.get('src'):
                src = img_tag.get('src')
                full_url = src if src.startswith('http') else f"https://file.royalrain.go.th{src}"
                filename = os.path.basename(full_url.split('?')[0])
                file_dt = parse_filename_to_datetime(filename)
                
                if file_dt:
                    latest_info = {
                        "station": station_name,
                        "filename": filename,
                        "url": full_url,
                        "year": file_dt.strftime("%Y"),
                        "month": file_dt.strftime("%m"),
                        "day": file_dt.strftime("%d"),
                        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

        # 2. แกะ URL ภาพทั้งหมดในหน้าเว็บ
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

        now_thai = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        time_limit = now_thai - datetime.timedelta(hours=24)

        download_count = 0
        skip_count = 0

        for img_url in img_urls:
            filename = os.path.basename(img_url.split('?')[0])
            file_dt = parse_filename_to_datetime(filename)

            if file_dt and file_dt >= time_limit:
                thai_year = file_dt.strftime("%Y")
                thai_month = file_dt.strftime("%m")
                thai_day = file_dt.strftime("%d")

                save_dir = os.path.join(BASE_SAVE_DIR, station_name, thai_year, thai_month, thai_day)
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)

                if os.path.exists(filepath):
                    skip_count += 1
                    continue

                img_res = requests.get(img_url, headers=headers, timeout=15)
                if img_res.status_code == 200 and len(img_res.content) > 3000:
                    with open(filepath, 'wb') as f:
                        f.write(img_res.content)

                    apply_logo_only(filepath)
                    download_count += 1
                    print(f"   [+] โหลดภาพใหม่: {filename}")

        # 3. บันทึกไฟล์ latest.json ไว้ในโฟลเดอร์สถานี
        if latest_info:
            station_dir = os.path.join(BASE_SAVE_DIR, station_name)
            os.makedirs(station_dir, exist_ok=True)
            json_path = os.path.join(station_dir, "latest.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(latest_info, f, ensure_ascii=False, indent=2)
            print(f"   [*] บันทึกข้อมูลภาพล่าสุดลง latest.json เรียบร้อย: {latest_info['filename']}")

        print(f"[{station_name}] สรุป: โหลดเพิ่ม {download_count} ภาพ | มีอยู่แล้ว {skip_count} ภาพ\n")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    cleanup_old_images_24h()
    for station_name, label in STATIONS.items():
        process_station_check_all_today(station_name, label)

if __name__ == "__main__":
    main()
