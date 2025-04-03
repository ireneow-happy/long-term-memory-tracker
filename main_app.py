
import streamlit as st
import pandas as pd
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Google Sheets 驗證 ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"]
)
sheet_url = st.secrets["general"]["GOOGLE_SHEET_URL"]
sheet_tab = st.secrets["general"]["GOOGLE_SHEET_TAB"]
spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]

service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

# --- 載入資料 ---
result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheet_tab).execute()
values = result.get("values", [])
headers = values[0] if values else []
data = values[1:] if len(values) > 1 else []
filtered_data = [row for row in data if len(row) == len(headers)]
df = pd.DataFrame(filtered_data, columns=headers) if filtered_data else pd.DataFrame(columns=headers)

# --- UI 設定 ---
st.set_page_config(page_title="記憶追蹤器", layout="centered")
st.title("🌀 記憶追蹤器")
st.write("這是一個幫助你建立長期記憶回顧計劃的工具。")

# --- 自動產生 Snippet ID ---
today = datetime.date.today()
today_str = today.strftime("%Y%m%d")

if "snippet_count" not in st.session_state:
    existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)].shape[0]
    st.session_state["snippet_count"] = existing_count

if "snippet_content" not in st.session_state:
    st.session_state["snippet_content"] = ""

if "review_days" not in st.session_state:
    st.session_state["review_days"] = "1,3,7,14,30"

new_snippet_id = f"{today_str}-{st.session_state['snippet_count'] + 1:02d}"

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

        # reset content and count
        st.session_state["snippet_count"] += 1
        st.session_state["snippet_content"] = ""
        st.session_state["review_days"] = "1,3,7,14,30"

        st.success("✅ Snippet 已新增！請重新整理查看最新內容。")
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
        ordered_options = ["note", "vocab", "quote", "other"]

        with st.form("edit_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_type = st.selectbox("類型", ordered_options, index=ordered_options.index(old_type))
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

                indices_to_delete = [i+1 for i, row in df.iterrows() if row["snippet_id"] == selected_id]
                for index in sorted(indices_to_delete, reverse=True):
                    sheet.values().clear(
                        spreadsheetId=spreadsheet_id,
                        range=f"{sheet_tab}!A{index+1}:F{index+1}"
                    ).execute()

                sheet.values().append(
                    spreadsheetId=spreadsheet_id,
                    range=sheet_tab,
                    valueInputOption="USER_ENTERED",
                    body={"values": updated_rows}
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
        indices_to_delete = [i+1 for i, row in df.iterrows() if row["snippet_id"] == selected_del_id]
        delete_requests = [{
            "deleteDimension": {
                "range": {
                    "sheetId": 0,
                    "dimension": "ROWS",
                    "startIndex": index,
                    "endIndex": index + 1
                }
            }
        } for index in sorted(indices_to_delete, reverse=True)]

        if delete_requests:
            sheet.batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": delete_requests}
            ).execute()

        st.success("✅ Snippet 已刪除。")
        st.rerun()
