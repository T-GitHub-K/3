import os
import sys
import webbrowser
from datetime import datetime
from collections import defaultdict

# --- 外部ライブラリの読み込みチェック ---
missing_modules = []

try:
    import feedparser
except ImportError:
    missing_modules.append("feedparser")

try:
    from bs4 import BeautifulSoup
except ImportError:
    missing_modules.append("beautifulsoup4")

try:
    from dateutil import parser as date_parser
except ImportError:
    missing_modules.append("python-dateutil")

if missing_modules:
    print("\n" + "=" * 60)
    print("❌ 実行に必要なライブラリが不足しています。")
    print(f"    pip install {' '.join(missing_modules)}")
    print("=" * 60 + "\n")
    sys.exit(1)

# --- アクセス拒否回避用のUser-Agent設定 ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- 安定して取得できるGoogleニュース検索RSSに変更 ---
RSS_FEEDS = [
    {
        "category": "タクシー・ライドシェア",
        "badge_color": "#f59e0b",
        "url": "https://news.google.com/rss/search?q=%E3%82%BF%E3%82%AF%E3%82%B7%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja"
    },
    {
        "category": "タクシー・ライドシェア",
        "badge_color": "#f59e0b",
        "url": "https://news.google.com/rss/search?q=%E3%83%A9%E3%82%A4%E3%83%89%E3%82%B7%E3%82%A7%E3%82%A2&hl=ja&gl=JP&ceid=JP:ja"
    },
    {
        "category": "静岡ローカル（タクシー）",
        "badge_color": "#e11d48",
        "url": "https://news.google.com/rss/search?q=%E9%9D%99%E5%B2%A1+%E3%82%BF%E3%82%AF%E3%82%B7%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja"
    },
    {
        "category": "自動運転・モビリティIT",
        "badge_color": "#7c3aed",
        "url": "https://news.google.com/rss/search?q=%E8%87%AA%E5%8B%95%E9%81%8B%E8%BB%A2+%E3%82%BF%E3%82%AF%E3%82%B7%E3%83%BC&hl=ja&gl=JP&ceid=JP:ja"
    },
    {
        "category": "国土交通省（行政）",
        "badge_color": "#0284c7",
        "url": "https://www.mlit.go.jp/rss/press.xml"
    }
]

# --- 排除したいノイズ（NGワード） ---
EXCLUDE_KEYWORDS = ["バス事故", "路線バス", "電車遅延", "新幹線", "飛行機", "JRダイヤ", "フェリー"]

# --- 地域優先度設定 ---
REGION_SETTINGS = [
    {
        "name": "関東圏",
        "score": 30,
        "bg_color": "#2563eb",
        "keywords": ["東京", "神奈川", "横浜", "川崎", "埼玉", "千葉", "茨城", "栃木", "群馬", "関東", "首都圏"]
    },
    {
        "name": "静岡",
        "score": 20,
        "bg_color": "#e11d48",
        "keywords": ["静岡", "浜松", "沼津", "富士", "伊豆", "熱海", "掛川", "藤枝", "三島", "島田"]
    },
    {
        "name": "大都市圏",
        "score": 10,
        "bg_color": "#059669",
        "keywords": ["大阪", "名古屋", "愛知", "京都", "神戸", "福岡", "札幌", "仙台", "関西", "中京", "近畿"]
    }
]


def detect_region(text):
    """テキストから該当する地域グループ、スコア、バッジカラーを特定"""
    for reg in REGION_SETTINGS:
        if any(kw in text for kw in reg["keywords"]):
            return reg["name"], reg["score"], reg["bg_color"]
    return "全国・その他", 0, "#64748b"


def is_relevant_taxi_news(title, summary, category):
    """ニュースの適合度判定（NGワードチェックのみに緩和）"""
    text = title + " " + summary

    # NGワードが含まれる場合のみ弾く
    if any(ng in text for ng in EXCLUDE_KEYWORDS):
        return False

    # 国土交通省などの全体プレスリリースの場合のみキーワードチェック
    if category == "国土交通省（行政）":
        return any(kw in text for kw in ["タクシー", "ハイヤー", "ライドシェア", "自動車運送"])

    return True


def parse_datetime(entry):
    raw_date = entry.get("published", entry.get("updated", None))
    if not raw_date:
        return datetime.min
    try:
        return date_parser.parse(raw_date)
    except Exception:
        return datetime.min


def generate_html_report(grouped_articles, per_category_limit, output_filename="news_dashboard.html"):
    sections_html = ""
    total_count = sum(len(articles) for articles in grouped_articles.values())

    for category_name, articles in grouped_articles.items():
        if not articles:
            continue
        
        badge_color = articles[0]["category_badge_color"]
        cards_html = ""
        
        for article in articles:
            date_str = article["datetime"].strftime("%Y-%m-%d %H:%M") if article["datetime"] != datetime.min else "日時不明"
            
            cards_html += f"""
            <div class="news-card">
                <div class="card-header">
                    <span class="region-badge" style="background-color: {article['region_bg_color']};">{article['region_name']}</span>
                    <span class="news-date">⏱ {date_str}</span>
                </div>
                <a class="news-title" href="{article['link']}" target="_blank" rel="noopener noreferrer">
                    {article['title']}
                </a>
                <p class="news-summary">{article['summary']}</p>
                <div class="card-footer">
                    <a class="news-link" href="{article['link']}" target="_blank" rel="noopener noreferrer">
                        記事原文を読む ➔
                    </a>
                </div>
            </div>
            """

        sections_html += f"""
        <section class="category-section">
            <div class="category-header" style="border-left-color: {badge_color};">
                <span class="category-badge" style="background-color: {badge_color};">{category_name}</span>
                <span class="category-count">（地域優先・最新 Top {len(articles)} 件）</span>
            </div>
            <div class="news-grid">
                {cards_html}
            </div>
        </section>
        """

    current_time_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>タクシー・モビリティ業界ニュースダッシュボード</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --border-color: #e2e8f0;
            --accent-color: #2563eb;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 24px 16px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 850px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #ffffff;
            padding: 28px 24px;
            border-radius: 12px;
            margin-bottom: 32px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.6rem;
            font-weight: 700;
        }}
        .header p {{
            margin: 0;
            font-size: 0.9rem;
            color: #94a3b8;
        }}
        .update-tag {{
            display: inline-block;
            margin-top: 12px;
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            color: #38bdf8;
        }}
        .category-section {{
            margin-bottom: 36px;
        }}
        .category-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            padding-left: 10px;
            border-left: 4px solid var(--accent-color);
        }}
        .category-badge {{
            color: #ffffff;
            font-size: 0.9rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 6px;
        }}
        .category-count {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        .news-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 18px 20px;
            margin-bottom: 14px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .news-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 12px -3px rgba(0, 0, 0, 0.05);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .region-badge {{
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .news-date {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .news-title {{
            display: block;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            text-decoration: none;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .news-title:hover {{
            color: var(--accent-color);
        }}
        .news-summary {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin: 0 0 10px 0;
        }}
        .card-footer {{
            text-align: right;
        }}
        .news-link {{
            font-size: 0.825rem;
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 600;
        }}
        .news-link:hover {{
            text-decoration: underline;
        }}
        .footer {{
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚕 タクシー・モビリティ地域優先ダッシュボード</h1>
            <p>地域優先度（関東圏 ➔ 静岡 ➔ 大都市圏）を考慮した業界ニュース</p>
            <div class="update-tag">最終更新: {current_time_str} | 全 {total_count} 件</div>
        </div>

        <div class="news-sections">
            {sections_html}
        </div>

        <div class="footer">
            Generated by Dedicated Regional Taxi News Aggregator
        </div>
    </div>
</body>
</html>
"""

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_filename


def main(category_top_n=10):
    raw_articles = []
    print("ニュースを取得中...\n")

    for feed_info in RSS_FEEDS:
        # User-Agentを指定してHTTP 403ブロックを回避
        parsed = feedparser.parse(feed_info["url"], agent=USER_AGENT)
        fetched_count = len(parsed.entries)
        print(f"📡 [{feed_info['category']}] フィードから {fetched_count} 件取得")

        passed_count = 0
        for entry in parsed.entries:
            title = entry.get("title", "タイトルなし")
            link = entry.get("link", "")
            
            raw_summary = entry.get("summary", entry.get("description", ""))
            clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text().strip()
            if len(clean_summary) > 120:
                clean_summary = clean_summary[:120] + "..."
            
            pub_date = parse_datetime(entry)
            category = feed_info["category"]
            category_badge_color = feed_info["badge_color"]

            if is_relevant_taxi_news(title, clean_summary, category):
                passed_count += 1
                full_text = title + " " + clean_summary
                region_name, region_score, region_bg_color = detect_region(full_text)

                raw_articles.append({
                    "category": category,
                    "category_badge_color": category_badge_color,
                    "region_name": region_name,
                    "region_score": region_score,
                    "region_bg_color": region_bg_color,
                    "title": title,
                    "summary": clean_summary or "（概要テキストなし）",
                    "link": link,
                    "datetime": pub_date
                })
        print(f"   └ フィルタ通過: {passed_count} 件\n")

    # 重複記事の除外
    unique_articles = []
    seen_titles = set()
    for article in raw_articles:
        if article["title"] not in seen_titles:
            seen_titles.add(article["title"])
            unique_articles.append(article)

    # グループ化
    grouped = defaultdict(list)
    for article in unique_articles:
        grouped[article["category"]].append(article)

    # ソート軸：① 地域優先度スコア (降順) ➔ ② 配信日時 (降順)
    final_grouped = {}
    for cat_name, items in grouped.items():
        items.sort(key=lambda x: (x["region_score"], x["datetime"]), reverse=True)
        final_grouped[cat_name] = items[:category_top_n]

    total_final = sum(len(v) for v in final_grouped.values())
    if total_final == 0:
        print("⚠️ 該当する記事が見つかりませんでした。インターネット接続を確認してください。")
        return

    # HTML生成と表示
    html_file = generate_html_report(final_grouped, per_category_limit=category_top_n)
    abs_path = os.path.abspath(html_file)
    webbrowser.open(f"file://{abs_path}")
    print(f"🚀 ダッシュボードを出力しました！（合計 {total_final} 件）")


if __name__ == "__main__":
    main(category_top_n=10)