import os
import re
import webbrowser
from dotenv import load_dotenv
from google import genai

# ---------------------------------------------------------
# 0. .env ファイルから環境変数を読み込み
# ---------------------------------------------------------
load_dotenv()  # スクリプトと同じ階層にある .env を読み込みます

# ---------------------------------------------------------
# 1. テキストファイルからデータの読み込みと解析
# ---------------------------------------------------------
def parse_input_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # ケース単位（=== CASE X ===）で分割
    cases_raw = re.split(r'===\s*(CASE\s*\d+|\w+)\s*===', content)
    test_cases = []

    for i in range(1, len(cases_raw), 2):
        case_title = cases_raw[i].strip()
        case_body = cases_raw[i+1]

        orig = re.search(r'\[ORIGINAL\]\n(.*?)(?=\n\[INSTRUCTION\]|$)', case_body, re.DOTALL)
        inst = re.search(r'\[INSTRUCTION\]\n(.*?)(?=\n\[ORIGINAL\]|$)', case_body, re.DOTALL)

        test_cases.append({
            "title": case_title,
            "original": orig.group(1).strip() if orig else "",
            "instruction": inst.group(1).strip() if inst else ""
        })

    return test_cases

# ---------------------------------------------------------
# 2. Gemini APIの呼び出し
# ---------------------------------------------------------
def call_ai(original, instruction):
    # .envから読み込まれたGEMINI_API_KEYが自動的に適用されます
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(".env ファイルに GEMINI_API_KEY が設定されていません。")

    client = genai.Client(api_key=api_key)

    prompt = f"""以下の[元の文章]に基づき、[指示内容]に従って回答を作成してください。

[元の文章]
{original}

[指示内容]
{instruction}
"""
    
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt
    )
    return response.text

# ---------------------------------------------------------
# 3. HTMLの生成
# ---------------------------------------------------------
def generate_html(results, output_html_path):
    html_cases = ""
    for item in results:
        html_cases += f"""
        <div class="test-case">
            <div class="case-header">{item['title']}</div>
            <div class="case-body">
                <div class="section-box box-original">
                    <span class="section-title">元の文章 (ORIGINAL)</span>
                    <pre class="content-text">{item['original']}</pre>
                </div>
                <div class="section-box box-instruction">
                    <span class="section-title">指示内容 (INSTRUCTION)</span>
                    <pre class="content-text">{item['instruction']}</pre>
                </div>
                <div class="section-box box-response">
                    <span class="section-title">AIの回答 (RESPONSE)</span>
                    <pre class="content-text">{item['response']}</pre>
                </div>
            </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>AI回答確認レポート</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f4f6f9; padding: 20px; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .test-case {{ background: #fff; border-radius: 8px; margin-bottom: 25px; border: 1px solid #ddd; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .case-header {{ background: #2c3e50; color: #fff; padding: 10px 15px; font-weight: bold; }}
        .case-body {{ padding: 20px; display: flex; flex-direction: column; gap: 15px; }}
        .section-box {{ border-left: 5px solid; padding: 12px 15px; border-radius: 4px; }}
        .section-title {{ font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: 3px; color: #fff; display: inline-block; margin-bottom: 6px; }}
        
        .box-original {{ background: #f8f9fa; border-color: #6c757d; }}
        .box-original .section-title {{ background: #6c757d; }}
        
        .box-instruction {{ background: #eef7ff; border-color: #007bff; }}
        .box-instruction .section-title {{ background: #007bff; }}
        
        .box-response {{ background: #f0fff4; border-color: #28a745; }}
        .box-response .section-title {{ background: #28a745; }}
        
        .content-text {{ white-space: pre-wrap; margin: 0; font-size: 14px; line-height: 1.6; word-break: break-word; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>AI実行・回答比較レポート</h2>
        {html_cases}
    </div>
</body>
</html>"""

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

# ---------------------------------------------------------
# 4. メイン処理
# ---------------------------------------------------------
if __name__ == "__main__":
    input_txt = "input_prompts.txt"
    output_html = os.path.abspath("ai_result_report.html")

    print("テキストファイルを読み込み中...")
    cases = parse_input_file(input_txt)

    results = []
    for case in cases:
        print(f"AI処理中: {case['title']} ...")
        ai_response = call_ai(case['original'], case['instruction'])
        case['response'] = ai_response
        results.append(case)

    print("HTMLを作成中...")
    generate_html(results, output_html)

    print("ブラウザを起動します...")
    webbrowser.open(f"file://{output_html}")
    print("完了しました。")