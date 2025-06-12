import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
from googletrans import Translator

translator = Translator()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def load_series():
    with open("series.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_series(series):
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

def get_latest_chapter_tencent(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    chapter_link = soup.select_one("a[href^='/ComicView/index/id/']")
    if not chapter_link:
        print("⚠️ No chapter found in HTML!")
        return None

    latest_url = "https://ac.qq.com" + chapter_link["href"]
    chapter_title = chapter_link.get_text(strip=True)
    return latest_url, chapter_title

def send_discord_message(title, chapter_title, url, site, thumbnail):
    translated_title = chapter_title
    try:
        translated_title = translator.translate(chapter_title, src="zh-CN", dest="en").text
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")

    release_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    embed = {
        "title": f"📢 New chapter for {title}",
        "description": f"**Original Title:** {chapter_title}\n**Translated:** {translated_title}\n[Read Now]({url})",
        "color": 0x00ff99,
        "thumbnail": {"url": thumbnail},
        "footer": {"text": f"{site.capitalize()} • Released at {release_time}"}
    }

    data = {"embeds": [embed]}
    try:
        response = requests.post(WEBHOOK_URL, json=data)
        if response.status_code != 204:
            print(f"⚠️ Discord request failed: {response.text}")
    except Exception as e:
        print(f"⚠️ Discord error: {e}")

def main():
    series = load_series()
    updated = False
    for item in series:
        url = item["url"]
        site = item["site"]
        title = item["title"]
        last_chapter = item["last_chapter"]
        thumbnail = item["thumbnail"]

        print(f"🔍 Checking {title}...")

        if site == "tencent":
            result = get_latest_chapter_tencent(url)
            if not result:
                print(f"⚠️ Skipped {title} due to missing chapter info.")
                continue
            latest_url, chapter_title = result
        else:
            print(f"⚠️ Unsupported site for {title}: {site}")
            continue

        if chapter_title != last_chapter:
            print(f"📢 New chapter for {title}: {chapter_title}")
            send_discord_message(title, chapter_title, latest_url, site, thumbnail)
            item["last_chapter"] = chapter_title
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
