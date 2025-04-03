
import streamlit as st
import pandas as pd
import datetime
from google.oauth2 import service_account
import gspread

# 認證與連接 Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"]
)
gc = gspread.authorize(credentials)
sheet_url = st.secrets["GOOGLE_SERVICE_ACCOUNT"]["GOOGLE_SHEET_URL"]
sheet_tab = st.secrets["GOOGLE_SERVICE_ACCOUNT"]["GOOGLE_SHEET_TAB"]
sh = gc.open_by_url(sheet_url)
worksheet = sh.worksheet(sheet_tab)

# 載入資料
data = worksheet.get_all_records()
df = pd.DataFrame(data)

st.title("🧠 記憶追蹤器")
st.write("這是一個幫助你建立長期記憶回顧計劃的工具。")

# 顯示現有 Snippets 表格
st.dataframe(df if not df.empty else pd.DataFrame(columns=[
    "date_created", "snippet_type", "snippet_id", "snippet_content", "review_date", "completed"
]))

st.markdown("---")
st.header("➕ 新增 Snippet")

col1, col2 = st.columns(2)
with col1:
    snippet_type = st.selectbox("類型", ["quote", "vocabulary", "concept", "other"])
with col2:
    date_created = st.date_input("建立日期", datetime.date.today())

today_str = date_created.strftime("%Y%m%d")
existing_count = df[df["snippet_id"].str.startswith(today_str, na=False)].shape[0]
snippet_id = f"{today_str}-{existing_count + 1:02d}"

snippet_content = st.text_area("內容")
if st.button("新增"):
    if snippet_content.strip() == "":
        st.warning("請輸入內容")
    else:
        new_row = [str(date_created), snippet_type, snippet_id, snippet_content, "", ""]
        worksheet.append_row(new_row)
        st.success(f"已新增 snippet：{snippet_id}")

# 編輯 Snippet 區塊
st.markdown("---")
st.header("✏️ 修改 Snippet")
if not df.empty:
    snippet_to_edit = st.selectbox("選擇要修改的 Snippet ID", df["snippet_id"])
    row_idx = df.index[df["snippet_id"] == snippet_to_edit].tolist()[0]

    new_type = st.selectbox("修改類型", ["quote", "vocabulary", "concept", "other"], index=["quote", "vocabulary", "concept", "other"].index(df.loc[row_idx, "snippet_type"]))
    new_content = st.text_area("修改內容", df.loc[row_idx, "snippet_content"])

    if st.button("儲存修改"):
        worksheet.update_cell(row_idx + 2, 2, new_type)  # snippet_type
        worksheet.update_cell(row_idx + 2, 4, new_content)  # snippet_content
        st.success("修改完成！")
else:
    st.info("目前還沒有任何 snippet 可供修改。")
