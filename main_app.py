
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
df = pd.DataFrame(data, columns=headers) if data else pd.DataFrame(columns=headers)

# --- UI 設定 ---
st.set_page_config(page_title="記憶追蹤器", layout="centered")
st.title("🌀 記憶追蹤器")
st.write("這是一個幫助你建立長期記憶回顧計劃的工具。")
st.dataframe(df)

# --- 自動產生 Snippet ID ---
today = datetime.date.today()
today_str = today.strftime("%Y%m%d")
existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)].shape[0]
new_snippet_id = f"{today_str}-{existing_count+1:02d}"

# --- 表單 ---
st.markdown("## ➕ 新增 Snippet")
with st.form("add_snippet_form"):
    col1, col2 = st.columns(2)
    with col1:
        snippet_type = st.selectbox("類型", ["quote", "vocab", "note", "other"])
    with col2:
        snippet_date = st.date_input("建立日期", value=today)

    st.text_input("Snippet ID", value=new_snippet_id, disabled=True)
    snippet_content = st.text_area("內容")
    review_days = st.text_input("回顧日（以逗號分隔）", "1,3,7,14,30")

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

        st.success("✅ Snippet 已新增！請重新整理查看最新內容。")
