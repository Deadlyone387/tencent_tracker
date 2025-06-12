import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Load Discord Webhook URL from environment variable
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Load series list from JSON
def load_series():
    with open("series.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Save updated chapter URLs back to JSON
def save_series(series):
    with open("series.json", "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=2)

# Scrape Tencent Comics for the latest chapter
def get_latest_chapter_tencent(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # Find first chapter link (latest)
    chapter = soup.select_one("a.comic-chapter__item")
    if chapter:
        href = chapter.get("href", "")
        return "https://ac.qq.com" + href, chapter.get_text(strip=True)

    return None, None

# Send a styled Discord embed notification
def send_discord_notification(title, chapter_url, chapter_title):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL not set.")
        return

    embed = {
        "title": "📢 Tencent Tracking Bot",
        "description": f"**New chapter released for _{title}_!**\n\n📖 **[{chapter_title}]({chapter_url})**",
        "color": 0x1abc9c,
        "thumbnail": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/5/55/Tencent_Logo.png"
        },
        "footer": {
            "text": "Powered by Tencent Tracking Bot • Updates every 10 minutes"
        }
    }

    data = { "embeds": [embed] }

    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"⚠️ Discord message failed: {response.status_code} {response.text}")
    else:
        print(f"✅ Notification sent for {title}")

# Main logic
def main():
    series = load_series()
    updated = False

    for entry in series:
        if entry.get("site") != "tencent":
            continue

        title = entry["name"]
        url = entry["url"]
        print(f"🔍 Checking {title}...")

        latest_url, chapter_name = get_latest_chapter_tencent(url)

        if latest_url and latest_url != entry.get("latest", ""):
            print(f"🆕 New chapter found: {chapter_name}")
            send_discord_notification(title, latest_url, chapter_name)
            entry["latest"] = latest_url
            updated = True
        else:
            print(f"✅ No update for {title}")

    if updated:
        save_series(series)

if __name__ == "__main__":
    main()
