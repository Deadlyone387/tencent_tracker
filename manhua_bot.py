import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

def load_series():
    with open("series.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_series(series):
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

def write_latest_chapters(series):
    with open("latest_chapters.txt", "w", encoding="utf-8") as f:
        for item in series:
            chapter_title = item.get("last_chapter_title", "Unknown")
            f.write(f"{item['title']}: {chapter_title}\n")

import re

def get_latest_chapter_tencent(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # Find all chapter links with the known pattern
    chapter_links = soup.select("a[href^='/ComicView/index/id/']")
    latest_chapter = None
    highest_cid = -1

    for link in chapter_links:
        href = link.get("href", "")
        title = link.get("title") or link.text.strip()
        match = re.search(r"/cid/(\d+)", href)
        if match:
            cid = int(match.group(1))
            if cid > highest_cid:
                highest_cid = cid
                latest_chapter = {
                    "url": "https://ac.qq.com" + href,
                    "title": title.strip() or "Untitled Chapter"
                }

    if latest_chapter:
        return latest_chapter

    print("⚠️ No chapter found in HTML after trying all selectors!")
    return None



def send_discord_notification(series_title, chapter_title, chapter_url, thumbnail):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK is not set in environment variables.")
        return

    release_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    embed = {
        "title": f"📢 New Chapter for {series_title}!",
        "description": (
            f"**[{chapter_title}]({chapter_url})**\n"
            f"🕒 Released: `{release_time}`"
        ),
        "color": 0x1abc9c,
        "thumbnail": {"url": thumbnail},
        "footer": {"text": "Tencent Tracking Bot"}
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
        last_chapter = item.get("last_chapter", "")
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
            item["last_chapter_title"] = result["title"]
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

    write_latest_chapters(series)

if __name__ == "__main__":
    main()
