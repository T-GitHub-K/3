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

# 足りないモジュールがある場合は分かりやすく案内を出して終了
if missing_modules:
    print("\n" + "=" * 60)
    print("❌ 実行に必要なライブラリが不足しています。")
    print("以下のコマンドを実行してライブラリをインストールしてください：\n")
    print(f"    pip install {' '.join(missing_modules)}")
    print("=" * 60 + "\n")
    sys.exit(1)

# --- ここから通常の処理 ---
# 巡回したいRSSフィードの設定
RSS_FEEDS = [
    # --- タクシー・交通関連 ---
    {"category": "タクシー・交通", "badge_color": "#f59e0b", "url": "https://news.yahoo.co.jp/rss/topics/domestic.xml"},
    {"category": "タクシー・交通", "badge_color": "#f59e0b", "url": "https://response.jp/rss/index.rdf"},
    
    # --- 既存カテゴリ ---
    {"category": "経済", "badge_color": "#0284c7", "url": "https://news.yahoo.co.jp/rss/topics/business.xml"},
    {"category": "IT・技術", "badge_color": "#7c3aed", "url": "https://news.yahoo.co.jp/rss/topics/it.xml"},
    {"category": "IT・技術", "badge_color": "#2563eb", "url": "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"},
    {"category": "宇宙", "badge_color": "#059669", "url": "https://sorae.info/feed"},
    {"category": "科学・文化", "badge_color": "#dc2626", "url": "https://www.nhk.or.jp/rss/news/cat3.xml"}
]

# タクシー関連ニュースを特定するためのキーワード判定用
TAXI_KEYWORDS = ["タクシー", "ハイヤー", "ライドシェア", "配車", "自動運転", "運賃", "運転手", "ドライバー", "交通"]

def parse_datetime(entry):
    raw_date = entry.get("published", entry.get("updated", None))
    if not raw_date:
        return datetime.min
    try:
        return date_parser.parse(raw_date)
    except Exception:
        return datetime.min

def generate_html_report(grouped_articles, per_category_limit, output_filename="news_dashboard.html"):
    """
    カテゴリ毎にグループ化した記事データからHTMLを生成
    """
    sections_html = ""
    total_count = sum(len(articles) for articles in grouped_articles.values())

    for category_name, articles in grouped_articles.items():
        if not articles:
            continue
        
        badge_color = articles[0]["badge_color"]
        
        cards_html = ""
        for article in articles:
            date_str = article["datetime"].strftime("%Y-%m-%d %H:%M") if article["datetime"] != datetime.min else "日時不明"
            
            cards_html += f"""
            <div class="news-card">
                <div class="card-header">
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
                <span class="category-count">（最新 Top {len(articles)} 件）</span>
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
    <title>統合ニュースダッシュボード (カテゴリ別表示)</title>
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
            margin-bottom: 6px;
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
            <h1>🚕 統合ニュースダッシュボード</h1>
            <p>カテゴリ別ニュース速報（各カテゴリ Top {per_category_limit} 件抽出）</p>
            <div class="update-tag">最終更新: {current_time_str} | 全 {total_count} 件</div>
        </div>

        <div class="news-sections">
            {sections_html}
        </div>

        <div class="footer">
            Generated by Python RSS News Aggregator Script
        </div>
    </div>
</body>
</html>
"""

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_filename


def main(category_top_n=3):
    """
    :param category_top_n: 各カテゴリ毎に取得する最新ニュースの件数
    """
    raw_articles = []
    print(f"各カテゴリからニュースを取得中（各カテゴリ Top {category_top_n} 件を抽出）...")

    for feed_info in RSS_FEEDS:
        parsed = feedparser.parse(feed_info["url"])
        for entry in parsed.entries:
            title = entry.get("title", "タイトルなし")
            link = entry.get("link", "")
            
            raw_summary = entry.get("summary", entry.get("description", ""))
            clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text().strip()
            if len(clean_summary) > 100:
                clean_summary = clean_summary[:100] + "..."
            
            pub_date = parse_datetime(entry)
            
            category = feed_info["category"]
            badge_color = feed_info["badge_color"]

            # キーワードが含まれる場合は「タクシー・交通」に割り当て
            if any(kw in title or kw in clean_summary for kw in TAXI_KEYWORDS):
                category = "タクシー・交通"
                badge_color = "#f59e0b"

            raw_articles.append({
                "category": category,
                "badge_color": badge_color,
                "title": title,
                "summary": clean_summary or "（概要テキストなし）",
                "link": link,
                "datetime": pub_date
            })

    # 重複記事（タイトル同一）の除外
    unique_articles = []
    seen_titles = set()
    for article in raw_articles:
        if article["title"] not in seen_titles:
            seen_titles.add(article["title"])
            unique_articles.append(article)

    # カテゴリごとにグループ化
    grouped = defaultdict(list)
    for article in unique_articles:
        grouped[article["category"]].append(article)

    # 各カテゴリ内で新着順にソートし、Top N 件に絞り込み
    final_grouped = {}
    for cat_name, items in grouped.items():
        items.sort(key=lambda x: x["datetime"], reverse=True)
        final_grouped[cat_name] = items[:category_top_n]

    # HTML生成とブラウザ自動起動
    html_file = generate_html_report(final_grouped, per_category_limit=category_top_n)
    abs_path = os.path.abspath(html_file)
    webbrowser.open(f"file://{abs_path}")
    print(f"🚀 各カテゴリ Top {category_top_n} 件を取りまとめたダッシュボードを表示しました！")


if __name__ == "__main__":
    # ここで「各カテゴリ毎に何件表示するか」を指定（例: 3件ずつ、5件ずつなど）
    main(category_top_n=20)