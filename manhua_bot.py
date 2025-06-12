import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

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
        return "https://ac.qq.com" + chapter["href"], chapter.get_text(strip=True)
    return None, None

def send_discord_notification(title, chapter_url, chapter_title):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL not set.")
        return

    data = {
        "embeds": [
            {
                "title": f"📖 New Chapter: {title}",
                "description": f"[{chapter_title}]({chapter_url})",
                "color": 0x00ffcc
            }
        ]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def main():
    series = load_series()
    updated = False

    for entry in series:
        if entry["site"] != "tencent":
            continue

        url = entry["url"]
        title = entry["name"]
        print(f"🔍 Checking: {title}")

        latest_url, chapter_name = get_latest_chapter_tencent(url)

        if latest_url and latest_url != entry["latest"]:
            print(f"🆕 New chapter found: {chapter_name}")
            send_discord_notification(title, latest_url, chapter_name)
            entry["latest"] = latest_url
            updated = True
        else:
            print("✅ No new chapter.")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
