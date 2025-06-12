import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator

TRANSLATE = True

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

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
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/ComicView/index/"]'))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        chapter_links = soup.select('a[href^="/ComicView/index/"]')
        filtered = [a for a in chapter_links if a.text.strip().startswith("第")]

        if not filtered:
            print("⚠️ No chapter found in HTML!")
            return None

        latest = filtered[0]
        chapter_url = "https://ac.qq.com" + latest["href"]
        chapter_title = latest.text.strip()
        return chapter_url, chapter_title

    except Exception as e:
        print("⚠️ Error during Tencent scrape:", e)
        return None
    finally:
        driver.quit()

def send_discord_notification(title, chapter_url, chapter_title, thumbnail_url):
    embed = {
        "title": title,
        "url": chapter_url,
        "description": f"**New Chapter Released!**\n{chapter_title}",
        "color": 0x00ff00,
        "thumbnail": {"url": thumbnail_url},
        "timestamp": datetime.utcnow().isoformat()
    }

    if TRANSLATE:
        try:
            translated = GoogleTranslator(source='zh-CN', target='en').translate(chapter_title)
            embed["fields"] = [{
                "name": "Translated Title",
                "value": translated,
                "inline": False
            }]
        except Exception as e:
            print("⚠️ Translation failed:", e)

    data = {"embeds": [embed]}
    try:
        response = requests.post(DISCORD_WEBHOOK, json=data)
        if response.status_code != 204:
            print("⚠️ Discord webhook failed:", response.text)
    except Exception as e:
        print("⚠️ Discord request failed:", e)

def main():
    series = load_series()
    updated = False

    for item in series:
        title = item["title"]
        url = item["url"]
        site = item["site"]
        last_chapter = item.get("last_chapter", "")
        thumbnail_url = item.get("thumbnail", "")

        print(f"🔍 Checking {title}...")

        if site == "tencent":
            result = get_latest_chapter_tencent(url)
        else:
            print(f"⚠️ Unknown site for {title}: {site}")
            continue

        if result is None:
            print(f"⚠️ Skipped {title} due to missing chapter info.")
            continue

        latest_url, chapter_title = result

        if chapter_title != last_chapter:
            print(f"📢 New chapter for {title}: {chapter_title}")
            send_discord_notification(title, latest_url, chapter_title, thumbnail_url)
            item["last_chapter"] = chapter_title
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
