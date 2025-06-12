import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from googletrans import Translator

# Load Discord Webhook URL from environment
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

translator = Translator()

def load_series():
    with open("series.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_series(series):
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

def get_latest_chapter_tencent(url):
    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"  # Use Chromium instead of Chrome
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    chapter = soup.select_one("a.comic-chapter__item")
    if chapter:
       href = chapter.get("href", "")
       title = chapter.get_text(strip=True)
       print(f"➡️ Found chapter: {title}, URL: https://ac.qq.com{href}")  # Add this
       return "https://ac.qq.com" + href, title
    else:
       print("⚠️ No chapter found in HTML!")  # Add this


def send_discord_notification(title, chapter_url, chapter_title_cn):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL not set.")
        return

    # Translate chapter title
    try:
        translated_title = translator.translate(chapter_title_cn, src='zh-cn', dest='en').text
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")
        translated_title = chapter_title_cn

    # Add release timestamp
    release_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    embed = {
        "title": "📢 Tencent Tracking Bot",
        "description": (
            f"**New chapter released for _{title}_!**\n\n"
            f"📖 **[{translated_title}]({chapter_url})**\n"
            f"🕒 Released: `{release_time}`"
        ),
        "color": 0x1abc9c,
        "thumbnail": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/5/55/Tencent_Logo.png"
        },
        "footer": {
            "text": "Powered by Tencent Tracking Bot • Auto-translated"
        }
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    if response.status_code != 204:
        print(f"⚠️ Discord message failed: {response.status_code} {response.text}")
    else:
        print(f"✅ Notification sent for {title}")

def main():
    series = load_series()
    updated = False

    for entry in series:
        if entry.get("site") != "tencent":
            continue

        title = entry["name"]
        url = entry["url"]
        print(f"🔍 Checking {title}...")

        latest_url, chapter_title = get_latest_chapter_tencent(url)

        if latest_url and latest_url != entry.get("latest", ""):
            print(f"🆕 New chapter found: {chapter_title}")
            send_discord_notification(title, latest_url, chapter_title)
            entry["latest"] = latest_url
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
