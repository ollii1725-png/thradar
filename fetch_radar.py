import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "https://file.royalrain.go.th/opendata/radar_data/cappi/"
BASE_SAVE_DIR = "radar-images"

# พาธไฟล์โลโก้ที่คุณอัปโหลดไว้ในโปรเจกต์ (เช่น logo.png)
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

def extract_time_from_filename(filename):
    """แกะ YYYYMMDDHHMMSS จากชื่อไฟล์ แปลงเป็นเวลาไทย UTC+7"""
    match = re.search(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})', filename)
    if match:
        year, month, day, hour, minute = match.groups()
        # แปลงเป็นวัตถุ datetime (เวลา UTC)
        utc_dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
        # บวกเพิ่ม 7 ชั่วโมงสำหรับเวลาไทย (UTC+7)
        thai_dt = utc_dt + datetime.timedelta(hours=7)
        
        date_folder = (thai_dt.strftime("%Y"), thai_dt.strftime("%m"), thai_dt.strftime("%d"))
        time_text = thai_dt.strftime("%Y-%m-%d %H:%M (UTC+7)")
        return date_folder, time_text
    
    # กรณีแกะชื่อไม่ได้ ให้ใช้เวลาปัจจุบัน UTC+7
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    return (now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")), now.strftime("%Y-%m-%d %H:%M (UTC+7)")

def apply_logo_and_timestamp(image_path, station_label, thai_time_str):
    """วาดโลโก้ที่มุมซ้ายบน และใส่ข้อความเวลา UTC+7 ที่มุมซ้ายล่าง"""
    try:
        with Image.open(image_path).convert("RGBA") as base_img:
            
            # 1. แปะภาพโลโก้ที่มุมซ้ายบน (ถ้ามีไฟล์ LOGO_PATH)
            if os.path.exists(LOGO_PATH):
                with Image.open(LOGO_PATH).convert("RGBA") as logo:
                    # ย่อขนาดโลโก้ให้เหมาะสม (เช่น กว้าง 80px)
                    logo_width = 80
                    aspect_ratio = logo.height / logo.width
                    logo_height = int(logo_width * aspect_ratio)
                    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                    
                    # วางโลโก้ที่มุมซ้ายบน (ตำแหน่ง x=15, y=15)
                    base_img.paste(logo, (15, 15), logo)

            # 2. วาดข้อความเวลา UTC+7 ที่มุมซ้ายล่าง
            draw = ImageDraw.Draw(base_img)
            
            try:
                # โหลดฟอนต์ (ปรับขนาดตามความเหมาะสม)
                font = ImageFont.truetype("arial.ttf", 18)
            except IOError:
                font = ImageFont.load_default()

            text_content = f"สถานี: {station_label} | เวลา: {thai_time_str}"

            # วาดกล่องพื้นหลังสีดำโปร่งแสงที่มุมซ้ายล่าง
            box_x1, box_y1 = 10, base_img.height - 45
            box_x2, box_y2 = 420, base_img.height - 10
            draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill=(0, 0, 0, 180))

            # เขียนข้อความสีขาวลงในกล่อง
            draw.text((box_x1 + 10, box_y1 + 8), text_content, fill=(255, 255, 255, 255), font=font)

            # บันทึกภาพทับไฟล์เดิมเป็น RGB
            base_img.convert("RGB").save(image_path)
            print(f"-> ประทับโลโก้และเวลา UTC+7 สำเร็จ")

    except Exception as e:
        print(f"-> เกิดข้อผิดพลาดในการแต่งภาพ: {e}")

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
        (year, month, day), thai_time_str = extract_time_from_filename(filename)

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

            # แต่งภาพ: แปะโลโก้มุมซ้ายบน + เวลา UTC+7 มุมซ้ายล่าง
            apply_logo_and_timestamp(filepath, station_label, thai_time_str)
            print(f"[{station_name}] บันทึกสำเร็จ!")

    except Exception as e:
        print(f"[{station_name}] เกิดข้อผิดพลาด: {e}")

def main():
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    for station_name, label in STATIONS.items():
        process_station(station_name, label)

if __name__ == "__main__":
    main()
