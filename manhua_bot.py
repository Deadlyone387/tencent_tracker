import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def load_series():
    with open("series.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_series(series):
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

def get_latest_chapter_tencent(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    chapter = soup.select_one("a.comic-chapter__item")
    if chapter:
        href = chapter.get("href")
        title = chapter.text.strip()
        return {
            "url": "https://ac.qq.com" + href,
            "title": title
        }
    else:
        print("⚠️ No chapter found in HTML!")
        return None

def translate_text(text):
    try:
        return GoogleTranslator(source='zh-CN', target='en').translate(text)
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")
        return text

def send_discord_notification(series_title, chapter_title_cn, chapter_url, thumbnail):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK is not set in environment variables.")
        return

    translated_title = translate_text(chapter_title_cn)
    release_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    embed = {
        "title": f"📢 New Chapter for {series_title}!",
        "description": (
            f"**[{translated_title}]({chapter_url})**\n"
            f"🕒 Released: `{release_time}`"
        ),
        "color": 0x1abc9c,
        "thumbnail": {"url": thumbnail},
        "footer": {"text": "Auto-translated from Chinese"}
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    if response.status_code != 204:
        print(f"⚠️ Discord request failed: {response.status_code} {response.text}")
    else:
        print(f"✅ Notification sent for {series_title}")

def main():
    series = load_series()
    updated = False

    for item in series:
        if item["site"] != "tencent":
            continue

        title = item["title"]
        url = item["url"]
        last_chapter = item["last_chapter"]
        thumbnail = item.get("thumbnail", "")

        print(f"🔍 Checking {title}...")
        result = get_latest_chapter_tencent(url)

        if not result:
            print(f"⚠️ Skipped {title} due to missing chapter info.")
            continue

        if result["url"] != last_chapter:
            print(f"📢 New chapter for {title}: {result['title']}")
            send_discord_notification(title, result['title'], result['url'], thumbnail)
            item["last_chapter"] = result["url"]
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
