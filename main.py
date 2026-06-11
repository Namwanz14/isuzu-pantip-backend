from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = FastAPI()

# อนุญาตให้หน้าเว็บเรียกได้ (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# คำที่ใช้วิเคราะห์ Sentiment (ภาษาไทย)
POSITIVE_WORDS = [
    "ดี", "เยี่ยม", "ชอบ", "ประทับใจ", "คุ้ม", "สวย", "แรง", "ประหยัด",
    "น่าซื้อ", "แนะนำ", "โคตรดี", "เจ๋ง", "ถูก", "ดีมาก", "ไม่ผิดหวัง",
    "พอใจ", "ยอดเยี่ยม", "ใช้ดี", "แข็งแรง", "ทนทาน", "น่าใช้", "ปลื้ม"
]

NEGATIVE_WORDS = [
    "แย่", "ผิดหวัง", "เสีย", "แพง", "ห่วย", "ปัญหา", "บกพร่อง", "ชำรุด",
    "ไม่ดี", "เสียดาย", "ช้า", "ไม่พอใจ", "ร้องเรียน", "เสียเงิน", "หลอก",
    "ไม่คุ้ม", "อย่าซื้อ", "เน่า", "พัง", "ซ่อม", "เบื่อ", "หนัก"
]


def analyze_sentiment(text: str) -> str:
    """วิเคราะห์ sentiment จากคำในข้อความ"""
    text_lower = text.lower()
    pos_score = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    neg_score = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    if pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    else:
        return "neutral"


def scrape_pantip(keyword: str = "isuzu", pages: int = 3) -> list:
    """ดึงกระทู้จาก Pantip ที่พูดถึง keyword"""
    results = []

    for page in range(1, pages + 1):
        url = f"https://pantip.com/search?q={keyword}&page={page}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            # ดึง topic items
            topics = soup.select("li.search-result-item")

            for topic in topics:
                try:
                    title_el = topic.select_one("h2 a")
                    snippet_el = topic.select_one(".search-result-snippet")
                    date_el = topic.select_one(".search-result-date")
                    votes_el = topic.select_one(".votes-count")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    date_str = date_el.get_text(strip=True) if date_el else ""
                    votes = votes_el.get_text(strip=True) if votes_el else "0"
                    link = "https://pantip.com" + title_el.get("href", "")

                    full_text = f"{title} {snippet}"
                    sentiment = analyze_sentiment(full_text)

                    results.append({
                        "title": title,
                        "snippet": snippet[:200],
                        "date": date_str,
                        "votes": re.sub(r"\D", "", votes) or "0",
                        "link": link,
                        "sentiment": sentiment,
                        "platform": "Pantip"
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            continue

    return results


def summarize(posts: list) -> dict:
    """สรุปสถิติจาก posts ที่ดึงมา"""
    total = len(posts)
    if total == 0:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0}

    pos = sum(1 for p in posts if p["sentiment"] == "positive")
    neg = sum(1 for p in posts if p["sentiment"] == "negative")
    neu = total - pos - neg

    return {
        "total": total,
        "positive": pos,
        "positive_pct": round(pos / total * 100),
        "negative": neg,
        "negative_pct": round(neg / total * 100),
        "neutral": neu,
        "neutral_pct": round(neu / total * 100),
    }


# ── API Endpoints ──────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Isuzu Pantip Monitor API is running"}


@app.get("/api/mentions")
def get_mentions(keyword: str = "isuzu", pages: int = 2):
    """ดึงข้อมูล mentions จาก Pantip"""
    posts = scrape_pantip(keyword, pages)
    summary = summarize(posts)
    return {
        "keyword": keyword,
        "scraped_at": datetime.now().isoformat(),
        "summary": summary,
        "posts": posts
    }


@app.get("/api/summary")
def get_summary(keyword: str = "isuzu"):
    """ดึงแค่ summary ไม่เอา posts"""
    posts = scrape_pantip(keyword, pages=2)
    return summarize(posts)
