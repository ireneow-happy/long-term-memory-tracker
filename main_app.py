import streamlit as st
from datetime import date, datetime, timedelta
import pandas as pd
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
        "week_offset": 0
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
today = date.today()
today_str = today.strftime("%Y%m%d")
if "snippet_count" not in st.session_state:
    existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)]["snippet_id"].nunique() if "snippet_id" in df.columns else 0
    st.session_state["snippet_count"] = existing_count

new_snippet_id = f"{today_str}-{st.session_state['snippet_count'] + 1:02d}"
if st.session_state["prev_snippet_id"] != new_snippet_id:
    st.session_state["snippet_content"] = ""
    st.session_state["review_days"] = "1,3,7,14,30"
    st.session_state["prev_snippet_id"] = new_snippet_id

st.title("🌀 記憶追蹤器")

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

# --- 週視圖（月曆格式） ---
def render_weekly_calendar(review_map, sheet, spreadsheet_id, sheet_tab, today):
    st.markdown("### 🗓️ 最近 4 週回顧任務")

    col_prev, col_spacer, col_next = st.columns([1, 5, 1])
    with col_prev:
        if st.button("⏪ 前四週"):
            st.session_state["week_offset"] -= 4
    with col_next:
        if st.button("⏩ 後四週"):
            st.session_state["week_offset"] += 4

    st.markdown("""
    <style>
        .week-header {
            font-weight: bold;
            text-align: center;
            font-size: 13px;
            padding: 6px;
            border-bottom: 1px solid #ccc;
        }
        .calendar-cell {
            border: 1px solid #ccc;
            min-height: 100px;
            padding: 6px;
            font-size: 12px;
        }
        .date-label {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .checkbox-list {
            padding-left: 2px;
            line-height: 1.6;
        }
        .checkbox-list input[type=checkbox] {
            margin-right: 6px;
        }
    </style>
    """, unsafe_allow_html=True)

    start_date = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state["week_offset"])
    end_date = start_date + timedelta(days=27)
    date_range = pd.date_range(start=start_date, end=end_date)
    padded_days = [None] * date_range[0].weekday() + list(date_range)
    weeks = [padded_days[i:i+7] for i in range(0, len(padded_days), 7)]

    cols = st.columns(7)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(7):
        cols[i].markdown(f"<div class='week-header'>{days[i]}</div>", unsafe_allow_html=True)

    with st.form("weekly_snippets"):
        for week in weeks:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if not day:
                        st.markdown("<div class='calendar-cell'>&nbsp;</div>", unsafe_allow_html=True)
                        continue

                    snippets = review_map.get(day.date(), [])
                    html = f"<div class='calendar-cell'>"
                    html += f"<div class='date-label'>{day.month}/{day.day}</div>"
                    html += "<div class='checkbox-list'>"

                    for item in snippets:
                        html_id = item["key"]
                        snippet_id = item["short_id"]
                        checked = "checked" if item["checked"] else ""
                        html += f"<label><input type='checkbox' name='{html_id}' {checked}> {snippet_id}</label><br>"

                    html += "</div></div>"
                    st.markdown(html, unsafe_allow_html=True)

        submitted = st.form_submit_button("✅ 儲存所有勾選結果")
        if submitted:
            for week in weeks:
                for day in week:
                    if not day:
                        continue
                    snippets = review_map.get(day.date(), [])
                    for item in snippets:
                        key = item["key"]
                        user_checked = st.session_state.get(key, False)
                        if user_checked != item["checked"]:
                            sheet.values().update(
                                spreadsheetId=spreadsheet_id,
                                range=f"{sheet_tab}!F{item['row_index']+1}",
                                valueInputOption="USER_ENTERED",
                                body={"values": [["TRUE" if user_checked else "FALSE"]]}
                            ).execute()
            st.success("✅ 已更新 Google Sheets")

render_weekly_calendar(review_map, sheet, spreadsheet_id, sheet_tab, today)
