import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

def render_weekly_calendar(review_map, sheet, spreadsheet_id, sheet_tab, today):
    # --- 週視圖（月曆格式） ---
    st.markdown("### 🗓️ 最近 4 週回顧任務")

    # 加入 CSS：讓每格排版清楚、整齊
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

    # 日期處理
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=27)
    date_range = pd.date_range(start=start_date, end=end_date)
    padded_days = [None] * date_range[0].weekday() + list(date_range)
    weeks = [padded_days[i:i+7] for i in range(0, len(padded_days), 7)]

    # 星期列
    cols = st.columns(7)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(7):
        cols[i].markdown(f"<div class='week-header'>{days[i]}</div>", unsafe_allow_html=True)

    # HTML form
    with st.form("weekly_snippets"):
        checkbox_inputs = {}

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


# --- 程式開始 ---

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













render_weekly_calendar(review_map, sheet, spreadsheet_id, sheet_tab, today)

# --- 新增 Snippet 表單 ---
st.markdown("## ➕ 新增 Snippet")
with st.form("add_snippet_form"):
    col1, col2 = st.columns(2)
    with col1:
        snippet_type = st.selectbox("類型", ["note", "vocab", "quote", "other"], index=0)
    with col2:
        snippet_date = st.date_input("建立日期", value=today)

    st.text_input("Snippet ID", value=new_snippet_id, disabled=True)
    snippet_content = st.text_area("內容", value=st.session_state["snippet_content"])
    review_days = st.text_input("回顧日（以逗號分隔）", value=st.session_state["review_days"])

    submitted = st.form_submit_button("新增")
    if submitted:
        rows_to_add = []
        for day in review_days.split(","):
            day = day.strip()
            if day.isdigit():
                review_date = snippet_date + datetime.timedelta(days=int(day))
                rows_to_add.append([
                    snippet_date.strftime("%Y-%m-%d"),
                    snippet_type,
                    new_snippet_id,
                    snippet_content,
                    review_date.strftime("%Y-%m-%d"),
                    "FALSE"
                ])

        sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_tab,
            valueInputOption="USER_ENTERED",
            body={"values": rows_to_add}
        ).execute()

        st.session_state["snippet_count"] += 1
        st.session_state["snippet_content"] = ""
        st.session_state["review_days"] = "1,3,7,14,30"

        st.success("✅ Snippet 已新增！")
        st.rerun()

# --- 修改 Snippet ---
st.markdown("---")
st.markdown("## 📝 修改 Snippet")
unique_ids = df["snippet_id"].unique()
selected_id = st.selectbox("選擇要修改的 Snippet ID", unique_ids)

if selected_id:
    snippet_rows = df[df["snippet_id"] == selected_id]
    if not snippet_rows.empty:
        old_type = snippet_rows.iloc[0]["snippet_type"]
        old_date = snippet_rows.iloc[0]["date_created"]
        old_content = snippet_rows.iloc[0]["snippet_content"]

        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_type = st.selectbox("類型", ["note", "vocab", "quote", "other"], index=["note", "vocab", "quote", "other"].index(old_type))
            with col2:
                new_date = st.date_input("建立日期", value=datetime.datetime.strptime(old_date, "%Y-%m-%d").date())
            new_content = st.text_area("內容", value=old_content)

            update_btn = st.form_submit_button("更新 Snippet")
            if update_btn:
                review_offsets = (pd.to_datetime(snippet_rows["review_date"]) - pd.to_datetime(old_date)).dt.days
                updated_rows = [[
                    new_date.strftime("%Y-%m-%d"),
                    new_type,
                    selected_id,
                    new_content,
                    (new_date + datetime.timedelta(days=int(offset))).strftime("%Y-%m-%d"),
                    snippet_rows.iloc[i]["completed"]
                ] for i, offset in enumerate(review_offsets)]

                matching_indices = [i+1 for i, row in df.iterrows() if row["snippet_id"] == selected_id]
                for row_index, row_data in zip(matching_indices, updated_rows):
                    sheet.values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_tab}!A{row_index+1}:F{row_index+1}",
                        valueInputOption="USER_ENTERED",
                        body={"values": [row_data]}
                    ).execute()

                st.success("✅ Snippet 已更新。")
                st.rerun()

# --- 刪除 Snippet ---
st.markdown("---")
st.markdown("## 🗑️ 刪除 Snippet")
selected_del_id = st.selectbox("選擇要刪除的 Snippet ID", unique_ids, key="delete")

if selected_del_id:
    confirm = st.button("確認刪除")
    if confirm:
        for index in sorted([i+1 for i, row in df.iterrows() if row["snippet_id"] == selected_del_id], reverse=True):
            sheet.values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_tab}!A{index+1}:F{index+1}"
            ).execute()

        st.success("✅ Snippet 已刪除。")
        st.rerun()
