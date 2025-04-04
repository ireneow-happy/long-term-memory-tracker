
import streamlit as st
from datetime import date, timedelta
import pandas as pd
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="記憶追蹤器", layout="centered")

# --- 初始化 session_state ---
def init_session_state():
    defaults = {
        "snippet_content": "",
        "review_days": "1,3,7,14,30",
        "reset_snippet": False,
        "prev_snippet_id": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- 載入資料 ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"]
)
sheet_url = st.secrets["general"]["GOOGLE_SHEET_URL"]
sheet_tab = st.secrets["general"]["GOOGLE_SHEET_TAB"]
spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]

service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheet_tab).execute()
values = result.get("values", [])
headers = values[0] if values else []
data = values[1:] if len(values) > 1 else []
filtered_data = [row for row in data if len(row) == len(headers)]
df = pd.DataFrame(filtered_data, columns=headers) if filtered_data else pd.DataFrame(columns=headers)

# --- 準備 Snippet ID ---
today = datetime.date.today()
today_str = today.strftime("%Y%m%d")
if "snippet_count" not in st.session_state:
    existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)]["snippet_id"].nunique() if "snippet_id" in df.columns else 0
    st.session_state["snippet_count"] = existing_count

new_snippet_id = f"{today_str}-{st.session_state['snippet_count'] + 1:02d}"
if st.session_state["prev_snippet_id"] != new_snippet_id:
    st.session_state["snippet_content"] = ""
    st.session_state["review_days"] = "1,3,7,14,30"
    st.session_state["prev_snippet_id"] = new_snippet_id

# --- 建立 review_map ---
df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
df["completed"] = df["completed"].fillna("FALSE")

review_map = {}
for i, row in df.iterrows():
    if pd.isna(row["review_date"]):
        continue
    review_day = row["review_date"].date()
    if review_day not in review_map:
        review_map[review_day] = []
    short_id = row["snippet_id"][-7:] if len(row["snippet_id"]) > 7 else row["snippet_id"]
    review_map[review_day].append({
        "snippet_id": row["snippet_id"],
        "short_id": short_id,
        "row_index": i + 1,
        "checked": row["completed"] == "TRUE",
        "key": f"chk_{row['snippet_id']}_{i}"
    })

# --- 顯示表格版月曆 ---
st.markdown("### 🗓️ 最近 4 週回顧任務")

# 計算最近 4 週的範圍（從週一開始）
start_of_week = today - timedelta(days=today.weekday())
end_date = start_of_week + timedelta(days=27)
days_range = pd.date_range(start=start_of_week, end=end_date)

# 填補空格至整數週
first_day_index = days_range[0].weekday()
padded_days = [None] * first_day_index + list(days_range)
while len(padded_days) % 7 != 0:
    padded_days.append(None)
weeks = [padded_days[i:i+7] for i in range(0, len(padded_days), 7)]

# 星期列
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 建立 HTML 月曆表格
calendar_html = "<style>table.calendar { border-collapse: collapse; width: 100%; table-layout: fixed; }"
calendar_html += "table.calendar td, table.calendar th { border: 1px solid #ccc; vertical-align: top; padding: 4px; font-size: 12px; }"
calendar_html += "table.calendar th { background: #f0f0f0; text-align: center; font-weight: bold; }</style>"
calendar_html += "<table class='calendar'>"
calendar_html += "<tr>" + "".join(f"<th>{day}</th>" for day in day_names) + "</tr>"

# 填入每格資料（checkbox 為展示用）
for week in weeks:
    calendar_html += "<tr>"
    for day in week:
        if day:
            date_str = f"{day.month}/{day.day}"
            content = f"<strong>{date_str}</strong><br>"
            snippets = review_map.get(day.date(), [])
            for item in snippets:
                label = item["short_id"]
                checkbox_html = f"<label><input type='checkbox' {'checked' if item['checked'] else ''} disabled> {label}</label><br>"
                content += checkbox_html
            calendar_html += f"<td>{content}</td>"
        else:
            calendar_html += "<td></td>"
    calendar_html += "</tr>"
calendar_html += "</table>"

st.markdown(calendar_html, unsafe_allow_html=True)
