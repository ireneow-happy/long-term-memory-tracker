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


# --- 週視圖（近 4 週）+ hover + tooltip ---
st.markdown("### 🗓️ 過去 4 週回顧任務")

# 加上樣式
st.markdown("""
<style>
.hover-box {
    padding: 6px;
    border: 1px solid #DDD;
    border-radius: 8px;
    min-height: 50px;
    text-align: center;
    transition: background-color 0.3s;
}
.hover-box:hover {
    background-color: #f0f0f0;
}
.grid-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}
.grid-cell {
    width: 13%;
}
.day-label {
    font-weight: bold;
    text-align: center;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

# 計算日期
start_of_week = today - timedelta(days=today.weekday())
last_day = start_of_week + timedelta(weeks=4, days=-1)
date_range = pd.date_range(start=start_of_week, end=last_day)

# 建立每週資料
weekly_view = []
week = [None]*7
for d in date_range:
    weekday = d.weekday()
    if weekday == 0 and any(week):
        weekly_view.append(week)
        week = [None]*7
    week[weekday] = d
if any(week):
    weekly_view.append(week)

# 顯示星期列
day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
st.markdown('<div class="grid-row">' + ''.join([f'<div class="grid-cell day-label">{day}</div>' for day in day_names]) + '</div>', unsafe_allow_html=True)

# 顯示每週區塊
for week in weekly_view:
    html_row = '<div class="grid-row">'
    for day in week:
        if day:
            date_str = f"{day.month}/{day.day}"
            items = review_map.get(day.date(), [])
            content = f"<strong>{date_str}</strong><br>"
            for item in items:
                content += f'<div title="Snippet ID: {item["snippet_id"]}">🔲 {item["short_id"]}</div>'
            html_row += f'<div class="grid-cell"><div class="hover-box">{content}</div></div>'
        else:
            html_row += '<div class="grid-cell"><div class="hover-box">&nbsp;</div></div>'
    html_row += '</div>'
    st.markdown(html_row, unsafe_allow_html=True)
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

                # 找出原始資料的 row index 並逐列覆蓋更新
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