# app.py
import streamlit as st
import requests, html, re
from bs4 import BeautifulSoup
from io import BytesIO
import zipfile

st.set_page_config(page_title="法規條文擷取工具", layout="wide")
st.title("📜 法規條文擷取 + 標註工具")

urls = st.text_area("請輸入法規網址（每行一筆）", height=150,
                    value="""
https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0130002
https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0130069
""")

run_button = st.button("🚀 開始擷取")

# --- 法規擷取函式 ---
def get_law_data_and_meta(url):
    res = requests.get(url)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    law_title = soup.find('title').text.split('-')[0].strip()

    amend_tr = soup.find('tr', id='trLNNDate')
    date_label = '修正日期'
    if not amend_tr:
        amend_tr = soup.find('tr', id='trLNODate')
        date_label = '發布日期'
    amend_date = amend_tr.find('td').text.strip() if amend_tr and amend_tr.find('td') else ''

    content = soup.find('div', class_='law-content')
    main_content = content.find('div', class_='law-reg-content') if content else None
    rows = main_content.find_all('div', recursive=False) if main_content else []
    chapter, section = '', ''
    law_data = []

    for r in rows:
        class_list = r.get('class', [])
        if 'h3' in class_list and 'char-2' in class_list:
            chapter = r.get_text(strip=True)
            continue
        if 'row' in class_list:
            num_div = r.find('div', class_='col-no')
            data_div = r.find('div', class_='col-data')
            if num_div and data_div:
                num = num_div.get_text(strip=True)
                text = data_div.get_text("\n", strip=True)
                if '條' in num:
                    law_data.append({
                        '章': chapter,
                        '章節': section,
                        '條': num,
                        '條文內容': text
                    })
                elif '節' in text and '條' not in text:
                    section = text

    return law_title, date_label, amend_date, law_data


# --- HTML 產出函式 ---
def generate_html(title, date_label, date_text, law_data):
    html_content = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
    <style>
    body {{ font-family: '微軟正黑體'; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #aaa; padding: 8px; text-align: left; vertical-align: top; word-break: break-word; }}
    thead th {{ background: #eee; position: sticky; top: 0; z-index: 1; }}
    tbody tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style></head><body>
    <h2>{title}</h2>
    <p><strong>{date_label}：</strong>{date_text}</p>
    <table>
    <thead><tr><th>章</th><th>章節</th><th>條</th><th>條文內容</th></tr></thead>
    <tbody>
    '''
    for row in law_data:
        content = html.escape(row['條文內容']).replace('\n', '<br>')
        html_content += f'''<tr>
        <td>{html.escape(row['章'])}</td>
        <td>{html.escape(row['章節'])}</td>
        <td>{html.escape(row['條'])}</td>
        <td>{content}</td>
        </tr>'''
    html_content += '''</tbody></table></body></html>'''
    return html_content

# --- 執行區 ---
if run_button:
    urls_list = [u.strip() for u in urls.strip().splitlines() if u.strip()]
    if not urls_list:
        st.warning("請輸入至少一筆網址")
    else:
        zf_buffer = BytesIO()
        with zipfile.ZipFile(zf_buffer, mode='w') as zf:
            for url in urls_list:
                try:
                    st.info(f"處理中：{url}")
                    title, label, date, data = get_law_data_and_meta(url)
                    html_str = generate_html(title, label, date, data)
                    zf.writestr(f"{title}.html", html_str)
                    st.success(f"✅ {title} 擷取完成，共 {len(data)} 條條文")
                except Exception as e:
                    st.error(f"❌ 錯誤：{url}\n{e}")
        st.download_button("📥 下載所有法規 HTML（zip）", data=zf_buffer.getvalue(), file_name="laws_export.zip", mime="application/zip")
