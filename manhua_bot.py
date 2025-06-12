import os
import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from deep_translator import GoogleTranslator

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

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    chapter_link = soup.select_one("a[href^='/ComicView/index/id/']")
    if not chapter_link:
        print("\u26a0\ufe0f No chapter found in HTML!")
        return None

    chapter_url = "https://ac.qq.com" + chapter_link.get("href")
    chapter_title = chapter_link.get("title") or chapter_link.text.strip()

    return chapter_url, chapter_title

def send_discord_notification(title, url, translated_title, thumbnail):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("\u26a0\ufe0f Discord webhook not set.")
        return

    embed = {
        "title": translated_title or title,
        "description": f"[{title}]({url})",
        "url": url,
        "color": 0x00ffcc,
        "thumbnail": {"url": thumbnail},
        "footer": {"text": "Tencent Tracking Bot"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }

    data = {"embeds": [embed]}
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204:
        print(f"\u26a0\ufe0f Discord request failed: {response.text}")


def main():
    series_list = load_series()
    updated = False

    for item in series_list:
        title = item.get("title")
        url = item.get("url")
        site = item.get("site")
        last_seen = item.get("latest_chapter", "")
        thumbnail = item.get("thumbnail")

        print(f"\ud83d\udd0d Checking {title}...")

        if site == "tencent":
            result = get_latest_chapter_tencent(url)
        else:
            print(f"\u26a0\ufe0f Unsupported site: {site}")
            continue

        if not result:
            print(f"\u26a0\ufe0f Skipped {title} due to missing chapter info.")
            continue

        latest_url, chapter_title = result

        if chapter_title != last_seen:
            print(f"\ud83d\udce2 New chapter for {title}: {chapter_title}")
            try:
                translated_title = GoogleTranslator(source='auto', target='en').translate(chapter_title)
            except Exception as e:
                print(f"\u26a0\ufe0f Translation failed: {e}")
                translated_title = None

            send_discord_notification(title, latest_url, translated_title, thumbnail)
            item["latest_chapter"] = chapter_title
            updated = True
        else:
            print(f"\u2705 No update for {title}")

    if updated:
        save_series(series_list)

if __name__ == "__main__":
    main()
