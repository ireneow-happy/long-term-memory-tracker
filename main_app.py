
import streamlit as st
from datetime import date, timedelta
st.set_page_config(page_title="記憶追蹤器", layout="centered")
import pandas as pd
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

# --- UI ---
st.title("🌀 記憶追蹤器")

# --- 雙月曆顯示 ---
st.markdown("## 📅 本月與下月複習排程")

first_day = today.replace(day=1)
last_day_next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) + timedelta(days=31)
end_date = last_day_next_month

days_range = pd.date_range(start=first_day, end=end_date)
weeks = []
week = [None]*7
for d in days_range:
    weekday = d.weekday()
    if weekday == 0 and any(week):
        weeks.append(week)
        week = [None]*7
    week[weekday] = d
if any(week):
    weeks.append(week)

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

# --- 自訂樣式 ---
st.markdown("""
<style>
    .week-header { font-weight: bold; text-align: center; font-size: 14px; padding: 6px; }
    .day-box { border: 1px solid #ddd; min-height: 120px; padding: 4px; font-size: 12px; border-radius: 4px; }
    .day-title { font-weight: bold; text-align: center; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 新週視圖（最近 4 週） ---
st.markdown("### 🗓️ 最近 4 週回顧任務")

start_date = today - timedelta(days=today.weekday())  # 本週一
end_date = start_date + timedelta(days=27)
date_list = pd.date_range(start=start_date, end=end_date)

padded = [None] * date_list[0].weekday() + list(date_list)
weeks = [padded[i:i+7] for i in range(0, len(padded), 7)]

# 星期列
cols = st.columns(7)
for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    cols[i].markdown(f"<div class='week-header'>{day}</div>", unsafe_allow_html=True)

# 每週列
for week in weeks:
    cols = st.columns(7)
    for i, d in enumerate(week):
        with cols[i]:
            if d is None:
                st.markdown("<div class='day-box'>&nbsp;</div>", unsafe_allow_html=True)
                continue

            st.markdown(f"<div class='day-box'><div class='day-title'>{d.month}/{d.day}</div>", unsafe_allow_html=True)
            tasks = review_map.get(d.date(), [])
            for task in tasks:
                current = st.checkbox(task["short_id"], value=task["checked"], key=task["key"], help=task["snippet_id"])
                if current != task["checked"]:
                    sheet.values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_tab}!F{task['row_index']+1}",
                        valueInputOption="USER_ENTERED",
                        body={"values": [["TRUE" if current else "FALSE"]]}
                    ).execute()
            st.markdown("</div>", unsafe_allow_html=True)
