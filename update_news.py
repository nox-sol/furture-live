import os
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from google import genai

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

RSS_FEEDS = [
    ("BBC", "https://feeds" + ".bbci.co.uk/news/science_and_environment/rss.xml")
]

KEYWORDS = ["climate", "green", "energy", "solar", "wind", "carbon", "emission", "nature", "wildlife", "ocean", "plastic", "recycle", "sustainab", "environment", "warming", "ev", "electric", "forest", "water", "net zero", "planet", "pollution", "biodiversity", "coal", "fossil"]

def fetch_rss():
    items = []
    for source, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item'):
                title = item.findtext('title') or ''
                link = item.findtext('link') or ''
                desc = item.findtext('description') or ''
                text_check = (title + " " + desc).lower()
                if any(k in text_check for k in KEYWORDS):
                    items.append({"source": source, "title": title.strip(), "link": link.strip(), "desc": desc.strip()})
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    return items

def generate_article_data(raw_item):
    prompt = f"""
    你是一位專業的英語教學與環境永續新聞主編。請將以下新聞改寫為適合台灣學習者的「完整長篇」英語閱讀教材，並嚴格依照歐洲共同語言參考標準（CEFR）分級為 A2、B1、B2 三種難度。
    
    新聞來源：{raw_item['source']}
    原始標題：{raw_item['title']}
    原始摘要：{raw_item['desc']}
    
    【重要寫作與分級要求】：
    1. **不限字數，內容務必豐富完整**：請根據該新聞主題的完整脈絡，擴寫並呈現充足的背景資訊、成因分析、具體數據案例、各方觀點與未來影響，讓每個難度等級都是一篇結構完整、有深度且讀起來過癮的長篇文章（不要只寫短短幾句話的摘要）。
    2. **嚴格依照 CEFR 程度分級**：
       - **A2（基礎級）**：使用高頻基礎單字與簡單清晰的句型（以簡單句與基本連接詞為主），把複雜的環境概念用淺顯易懂的方式完整說明。
       - **B1（進階級）**：使用標準新聞英語詞彙、適度的複合句與轉折詞，完整傳達新聞細節與因果邏輯。
       - **B2（高階級）**：使用道地精準的學術與新聞專業詞彙、多元進階句型（如分詞構句、關係子句、被動與假設語氣），展現深度報導的專業語氣。
    3. **逐句對照**：每個等級都必須拆分成獨立的英文句子，並附上自然流暢的繁體中文（台灣用語）翻譯。
    4. **主題分類**：從以下四項中選出最貼切的一個：「氣候變遷與環境現況」、「永續生活與環保行動」、「國家政策與能源挑戰」、「綠色能源與環保科技」。
    5. **內建單字庫**：從 A2、B1、B2 三個版本的文章中，提取所有重要或值得學習的英文單字（全部轉為小寫，至少 40～60 個單字），提供繁體中文詞性與解釋。
    
    請嚴格只輸出純 JSON 格式（不要包含 markdown 標記或其他多餘說明文字），格式如下：
    {{
      "id": "news_{int(time.time())}",
      "date": "{datetime.now().strftime('%Y-%m-%d')}",
      "source": "{raw_item['source']}",
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
    available = [m.name for m in client.models.list() if "flash" in m.name.lower()]
    chosen_model = available if available else "gemini-2.0-flash"
    response = client.models.generate_content(
        model=chosen_model,
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
            articles = json.load(f)
    except Exception:
        articles = []

    existing_titles = {a.get("title_en", "").lower() for a in articles}
    raw_items = fetch_rss()
    
    added = 0
    for item in raw_items:
        if added >= 2:
            break
        try:
            new_art = generate_article_data(item)
            if new_art["title_en"].lower() not in existing_titles:
                new_art["id"] = f"news_{int(time.time())}_{added}"
                articles.insert(0, new_art)
                existing_titles.add(new_art["title_en"].lower())
                added += 1
                time.sleep(2)
        except Exception as e:
            print(f"Failed to process {item['title']}: {e}")

    articles = articles[:60]
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Added {added} new articles.")

if __name__ == "__main__":
    main()
