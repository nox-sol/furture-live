import os
import re
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

def fetch_full_article_text(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, flags=re.DOTALL)
        clean_paras = []
        for p in paragraphs:
            text = re.sub(r'<[^>]+>', '', p).strip()
            if len(text) > 45 and "BBC" not in text and "cookie" not in text.lower():
                clean_paras.append(text)
        return "\n".join(clean_paras[:25])
    except Exception as e:
        print(f"Full text fetch warning: {e}")
        return ""

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
                    full_text = fetch_full_article_text(link.strip())
                    items.append({
                        "source": source,
                        "title": title.strip(),
                        "link": link.strip(),
                        "desc": desc.strip(),
                        "full_text": full_text if len(full_text) > 200 else desc.strip()
                    })
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    return items

def generate_article_data(raw_item):
    prompt = f"""
    你是一位專業的英語教學與環境永續新聞主編。請根據以下新聞的完整內容，改寫為「內容豐富、篇幅完整」的深度英語閱讀教材，並嚴格依照 CEFR 標準分為 A2、B1、B2 三種難度。
    
    新聞來源：{raw_item['source']}
    原始標題：{raw_item['title']}
    完整新聞內容：
    {raw_item['full_text']}
    
    【強制寫作與難度分級規範（務必嚴格遵守）】：
    1. **篇幅要長、細節要完整**：每個難度等級（A2、B1、B2）**至少必須包含 14 到 20 個完整英文句子**（不限字數上限，越完整越好），請把新聞中的起因、數據、地點、人物觀點、環境衝擊與解決方案全部寫出來，絕對禁止只寫 4、5 句的短摘要！
    2. **讓 A2 / B1 / B2 產生極明顯的難易度落差**：
       - **A2（基礎入門級）**：只使用最基礎的 1500 個日常英文單字，每句話控制在 8～13 個字以內的簡單短句（例如使用 because, so, but, when），把複雜新聞拆解成極度好懂的白話短句。
       - **B1（中級進階級）**：使用高中與多益標準新聞字彙，每句約 15～22 個字，運用關係代名詞（which, who, that）、現在完成式與轉折連接詞（however, therefore, meanwhile），呈現流暢的新聞敘事。
       - **B2（高階專業級）**：使用《經濟學人》或托福/雅思等級的進階學術與環境專業詞彙（如 mitigate, unprecedented, biodiversity, implementation, infrastructure），每句約 22～32 個字，大量運用分詞構句、倒裝、被動語態與複雜從屬子句，展現高度專業的新聞分析語氣。
    3. **逐句對照翻譯**：每一個英文句子都必須搭配精準、道地的繁體中文（台灣習慣用語）翻譯。
    4. **主題分類**：從「氣候變遷與環境現況」、「永續生活與環保行動」、「國家政策與能源挑戰」、「綠色能源與環保科技」中選最貼切的一項。
    5. **豐富單字庫**：從三篇文章中提取至少 50 個重要英文單字（全部小寫），提供繁體中文詞性與解釋。
    
    請嚴格只輸出純 JSON 格式（不要包含 markdown 標記或其他說明文字），格式如下：
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
    chosen_model = available.pop(0) if available else "gemini-2.0-flash"
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
