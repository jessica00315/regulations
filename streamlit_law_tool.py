# 法規擷取並輸出為完整 HTML 表格（Streamlit 版）

import streamlit as st
import requests
import html
import re
from bs4 import BeautifulSoup
from datetime import datetime

# ======= 網頁標題與說明 =======
st.set_page_config(page_title="法規清單擷取工具", layout="wide")
st.title("📘 法規擷取工具（支援多網址）")
st.markdown("輸入法規網址，每行一筆，會輸出與 Colab 相同格式的 HTML 檔案")

# ======= 使用者輸入網址 =======
urls_input = st.text_area("輸入法規網址（每行一筆）：",
    """https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0130002
https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0130069""",
    height=150)

# ======= 主邏輯：擷取資料 =======
def get_law_data_and_meta(url):
    res = requests.get(url)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    title = soup.find('title').text.split('-')[0].strip()
    date_label = '修正日期'
    amend_tr = soup.find('tr', id='trLNNDate') or soup.find('tr', id='trLNODate')
    if amend_tr:
        td = amend_tr.find('td')
        amend_date = td.text.strip() if td else ''
        if 'trLNODate' in amend_tr.get('id', ''):
            date_label = '發布日期'
    else:
        amend_date = ''

    content = soup.find('div', class_='law-content')
    main = content.find('div', class_='law-reg-content') if content else None
    blocks = main.find_all('div', recursive=False) if main else []

    chapter, section = '', ''
    law_data = []
    for block in blocks:
        classes = block.get("class", [])
        if 'h3' in classes and 'char-2' in classes:
            chapter = block.get_text(strip=True)
        elif 'row' in classes:
            num = block.find('div', class_='col-no')
            data = block.find('div', class_='col-data')
            if num and data:
                no_text = num.get_text(strip=True)
                content_text = data.get_text("\n", strip=True)
                if '條' in no_text:
                    law_data.append({
                        '章': chapter,
                        '章節': section,
                        '條': no_text,
                        '條文內容': content_text
                    })
                elif '節' in content_text and '條' not in content_text:
                    section = content_text
    return title, date_label, amend_date, law_data

# ======= 輸出 HTML 檔案 =======
def generate_html(title, date_label, date_text, law_data):
    filename = f"{title}.html"
    html_header = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
    <style>
    body {{ font-family: '微軟正黑體'; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #aaa; padding: 8px; text-align: left; vertical-align: top; word-break: break-word; }}
    thead th {{ background: #eee; position: sticky; top: 0; z-index: 1; }}
    tbody tr:nth-child(even) {{ background-color: #f9f9f9; }}
    tbody tr:hover {{ background-color: #eef; }}
    textarea {{ width: 100%; height: 80px; padding: 4px; box-sizing: border-box; }}
    select:disabled, textarea:disabled {{ background-color: #f5f5f5; color: #333; }}
    .button {{ padding: 10px 15px; margin: 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }}
    </style>
    <script>
    let confirmed = false;
    function toggleEdit() {{
      confirmed = false;
      document.querySelectorAll('select, textarea').forEach(el => el.disabled = false);
    }}
    function confirmEdit() {{
      confirmed = true;
      document.querySelectorAll('select, textarea').forEach(el => el.disabled = true);
    }}
    function downloadModifiedHTML() {{
      if (!confirmed) return alert('請先完成更新');
      document.querySelectorAll('tr').forEach((row) => {{
        row.querySelectorAll('select').forEach(sel => sel.setAttribute('data-selected', sel.value));
        const txt = row.querySelector('textarea');
        if (txt) txt.setAttribute('data-content', txt.value);
      }});
      const blob = new Blob(['<!DOCTYPE html>' + document.documentElement.outerHTML], {{ type: 'text/html' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = '{title}_更新版.html';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }}
    window.onload = () => {{
      document.querySelectorAll('tr').forEach((row) => {{
        row.querySelectorAll('select').forEach(sel => sel.value = sel.getAttribute('data-selected') || '否');
        const txt = row.querySelector('textarea');
        if (txt) txt.value = txt.getAttribute('data-content') || '';
      }});
    }}
    </script>
    </head><body>
    <h2>{title}</h2>
    <p><strong>{date_label}：</strong>{date_text}</p>
    <table><thead><tr><th>章</th><th>章節</th><th>條</th><th>條文內容</th><th>定義條文</th><th>是否適用</th><th>是否符合</th><th>備註</th></tr></thead><tbody>
    '''
    rows = ""
    for row in law_data:
        content = html.escape(row['條文內容']).replace('\n', '<br>')
        rows += f'''<tr>
        <td>{html.escape(row['章'])}</td>
        <td>{html.escape(row['章節'])}</td>
        <td>{html.escape(row['條'])}</td>
        <td>{content}</td>
        <td><select data-selected="否" disabled><option>否</option><option>是</option></select></td>
        <td><select data-selected=" " disabled><option> </option><option>適用</option><option>不適用</option></select></td>
        <td><select data-selected=" " disabled><option> </option><option>符合</option><option>不符合</option></select></td>
        <td><textarea data-content="" disabled></textarea></td>
        </tr>'''

    html_footer = '''</tbody></table>
    <div>
    <button class="button" onclick="toggleEdit()">更新</button>
    <button class="button" onclick="confirmEdit()">完成更新</button>
    <button class="button" onclick="downloadModifiedHTML()">下載更新版本</button>
    </div></body></html>'''

    full_html = html_header + rows + html_footer
    return filename, full_html

# ======= 主執行流程 =======
if st.button("🚀 擷取並產出 HTML"):
    urls = [u.strip() for u in urls_input.strip().splitlines() if u.strip()]
    for url in urls:
        try:
            st.write(f"🔍 處理：{url}")
            title, label, date, data = get_law_data_and_meta(url)
            filename, html_string = generate_html(title, label, date, data)
            st.success(f"✅ 已完成：{title} 共 {len(data)} 條")
            st.download_button(
                label=f"⬇️ 下載：{filename}",
                data=html_string,
                file_name=filename,
                mime="text/html"
            )
        except Exception as e:
            st.error(f"❌ 發生錯誤：{e}")
