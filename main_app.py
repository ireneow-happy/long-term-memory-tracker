
import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

st.set_page_config(page_title="記憶追蹤器", page_icon="🧠", layout="centered")

st.title("🧠 記憶追蹤器")
st.markdown("這是一個幫助你建立長期記憶回顧計劃的工具。")

# 認證並連接 Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
sheet_url = st.secrets["GOOGLE_SERVICE_ACCOUNT"]["GOOGLE_SHEET_URL"]
worksheet = gc.open_by_url(sheet_url).worksheet(st.secrets["GOOGLE_SERVICE_ACCOUNT"]["GOOGLE_SHEET_TAB"])

# 讀取現有資料
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 建立 Snippet 區域
st.subheader("➕ 新增 Snippet")
with st.form(key="add_snippet_form"):
    snippet_type = st.selectbox("類型", ["quote", "definition", "concept", "custom"])
    date_created = st.date_input("建立日期", datetime.date.today())
    today_str = date_created.strftime("%Y%m%d")

    # 建立自動編號 ID
    if df.empty:
        existing_count = 0
    else:
        existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)].shape[0]
    snippet_id = f"{today_str}-{existing_count+1:02d}"

    st.text_input("Snippet ID", snippet_id, disabled=True, key="new_snippet_id")
    snippet_content = st.text_area("內容")
    submitted = st.form_submit_button("新增")

    if submitted and snippet_content.strip():
        review_dates = [date_created + datetime.timedelta(days=offset) for offset in [1, 3, 7, 14, 30]]
        for review_date in review_dates:
            worksheet.append_row([
                date_created.strftime("%Y-%m-%d"),
                snippet_type,
                snippet_id,
                snippet_content,
                review_date.strftime("%Y-%m-%d"),
                "FALSE"
            ])
        st.success(f"已新增 Snippet：{snippet_id}")

# 顯示現有資料表格
st.subheader("📋 Snippet 資料表")
if df.empty:
    st.info("尚未新增任何 Snippet。")
else:
    edited_df = df.copy()
    selected = st.selectbox("選擇要刪除的 snippet_id", [""] + df["snippet_id"].unique().tolist())
    if selected:
        if st.button("❌ 刪除選取的 Snippet"):
            indexes_to_delete = df[df["snippet_id"] == selected].index.tolist()
            for i in reversed(indexes_to_delete):
                worksheet.delete_rows(i + 2)  # 加2是因為 gspread 是從 1 開始，且有標題列
            st.success(f"已刪除 Snippet：{selected}")
            st.experimental_rerun()
    st.dataframe(df)
