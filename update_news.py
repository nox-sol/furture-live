import os
import json
import feedparser
from datetime import datetime
from google import genai

# 初始化 Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# BBC 與 CNN 環保/科學公開 RSS 來源
RSS_FEEDS = [
    ("BBC", "https://feeds" + ".bbci.co.uk/news/science_and_environment/rss.xml")
   
]



def fetch_latest_articles():
    items = []
    for source, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            # 簡單篩選與氣候、能源、環境相關的新聞
            keywords = ["climate", "green", "energy", "carbon", "eco", "solar", "wind", "planet", "environment", "warming", "nature", "recycle", "ocean", "forest", "emission"]
            if any(k in (title + " " + summary).lower() for k in keywords) or source == "BBC":
                items.append({
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "link": link
                })
            if len(items) >= 3:
                break
        if len(items) >= 3:
            break
    return items[:2]  # 每天自動精選 2 篇最新報導

def generate_lesson(raw_item):
    prompt = f"""
你是一位專業的英語教學編輯。請根據以下新聞素材，改寫成適合台灣學習者的「每日永續英文閱讀教材」。
新聞來源：{raw_item['source']}
原始標題：{raw_item['title']}
原始摘要：{raw_item['summary']}

請嚴格遵守以下要求，並**只輸出純 JSON 格式**（不要加 ```json 標記，不要任何多餘文字）：
1. "category": 必須從這四個選項中挑一個最適合的："氣候變遷與環境現況"、"永續生活與環保行動"、"國家政策與能源挑戰"、"綠色能源與環保科技"。
2. "levels": 包含 "A2"、"B1"、"B2" 三個難度版本。每個版本長度約 200~300 字（約一張 A4 紙閱讀量），必須拆解成句子陣列 "sentences"，每個元素包含 "en"（英文句子）和 "zh"（流暢的繁體中文翻譯）。
3. "dictionary": 提取這三種版本中出現的所有重要英文單字（全部轉為小寫、去掉標點符號），建立中英對照字典，格式為 {{"word": "(詞性) 繁體中文解釋"}}。

JSON 輸出格式範例：
{{
  "id": "{datetime.now().strftime('%Y%m%d')}_{raw_item['source']}_{abs(hash(raw_item['title'])) % 10000}",
  "date": "{datetime.now().strftime('%Y-%m-%d')}",
  "source": "{raw_item['source']}",
  "url": "{raw_item['link']}",
  "category": "綠色能源與環保科技",
  "title_en": "改寫後的英文標題",
  "title_zh": "繁體中文標題",
  "levels": {{
    "A2": {{"sentences": [{{"en": "Sentence 1.", "zh": "第一句中文。"}}]}},
    "B1": {{"sentences": [{{"en": "Sentence 1.", "zh": "第一句中文。"}}]}},
    "B2": {{"sentences": [{{"en": "Sentence 1.", "zh": "第一句中文。"}}]}}
  }},
  "dictionary": {{
    "sentence": "(n.) 句子"
  }}
}}
"""
    response = client.models.generate_content(
        model="gemini-3.0-flash",
        contents=prompt,
    )
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())

def main():
    try:
        with open("articles.json", "r", encoding="utf-8") as f:
            existing_articles = json.load(f)
    except Exception:
        existing_articles = []

    existing_urls = {a.get("url") for a in existing_articles}
    raw_items = fetch_latest_articles()
    new_articles = []

    for item in raw_items:
        if item["link"] not in existing_urls:
            try:
                lesson = generate_lesson(item)
                new_articles.append(lesson)
            except Exception as e:
                print(f"Error generating lesson: {e}")

    if new_articles:
        updated = new_articles + existing_articles
        # 最多保留最近 60 篇文章，避免檔案過大
        with open("articles.json", "w", encoding="utf-8") as f:
            json.dump(updated[:60], f, ensure_ascii=False, indent=2)
        print(f"Added {len(new_articles)} new articles.")
    else:
        print("No new articles added.")

if __name__ == "__main__":
    main()
