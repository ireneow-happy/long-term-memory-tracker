# main.py
import streamlit as st
import pandas as pd
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os # 引入 os 模組檢查 secrets 文件

# --- Google Sheets 驗證 ---
# 檢查 Streamlit Secrets 是否已載入
if "GOOGLE_SERVICE_ACCOUNT" not in st.secrets or "general" not in st.secrets:
    st.error("❌ 錯誤：找不到必要的 Secrets 配置 (GOOGLE_SERVICE_ACCOUNT 或 general)。")
    st.info("請確認你的 .streamlit/secrets.toml 文件已正確設置。")
    st.info("""
        範例 `secrets.toml`:
        ```toml
        # .streamlit/secrets.toml
        [GOOGLE_SERVICE_ACCOUNT]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "your-private-key-id"
        private_key = "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----\\n"
        client_email = "[已移除電子郵件地址]"
        client_id = "your-client-id"
        auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://www.google.com/search?q=https://accounts.google.com/o/oauth2/auth)"
        token_uri = "[https://oauth2.googleapis.com/token](https://www.google.com/search?q=https://oauth2.googleapis.com/token)"
        auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.google.com/search?q=https://www.googleapis.com/oauth2/v1/certs)"
        client_x509_cert_url = "[https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-project-id.iam.gserviceaccount.com](https://www.google.com/search?q=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%2540your-project-id.iam.gserviceaccount.com)"

        [general]
        GOOGLE_SHEET_URL = "[https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit#gid=0](https://www.google.com/search?q=https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit%23gid%3D0)"
        GOOGLE_SHEET_TAB = "工作表1" # 或是你的工作表分頁名稱
        ```
    """)
    st.stop() # 停止執行

try:
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["GOOGLE_SERVICE_ACCOUNT"]
    )
    sheet_url = st.secrets["general"]["GOOGLE_SHEET_URL"]
    sheet_tab = st.secrets["general"]["GOOGLE_SHEET_TAB"] # 工作表名稱 (Tab Name)
    spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]

    service = build("sheets", "v4", credentials=credentials)
    gsheet = service.spreadsheets() # Renamed for clarity
except KeyError as e:
    st.error(f"❌ Secrets 配置錯誤：缺少鍵 '{e}'。請檢查 .streamlit/secrets.toml 文件。")
    st.stop()
except Exception as e:
    st.error(f"❌ Google Sheets 連接或驗證失敗: {e}")
    st.stop() # 如果驗證失敗，停止執行

# --- Helper Function: 取得 Sheet ID (gid) ---
# 刪除操作需要 sheetId (gid)，而不是工作表名稱
@st.cache_data(ttl=600) # 快取 10 分鐘
def get_sheet_id(_service_obj, spreadsheet_id, sheet_name):
    """根據工作表名稱獲取 sheetId (gid)"""
    try:
        sheet_metadata = _service_obj.get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        for sheet in sheets:
            if sheet.get("properties", {}).get("title", "") == sheet_name:
                return sheet.get("properties", {}).get("sheetId", 0)
        st.error(f"找不到名為 '{sheet_name}' 的工作表。請檢查 GOOGLE_SHEET_TAB 設定。")
        return None
    except HttpError as e:
        st.error(f"無法獲取 Sheet ID: {e}")
        return None
    except Exception as e:
        st.error(f"獲取 Sheet ID 時發生未知錯誤: {e}")
        return None

# --- Helper Function: 載入資料 ---
@st.cache_data(ttl=60) # 快取 1 分鐘，避免頻繁讀取
def load_data(_gsheet_service, spreadsheet_id, sheet_tab_name):
    """從 Google Sheet 載入資料到 DataFrame"""
    try:
        result = _gsheet_service.values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_tab_name
        ).execute()
        values = result.get("values", [])
        if not values:
            # 如果工作表完全為空，返回預設結構
            st.warning("工作表中沒有資料或只有標題。")
            # 定義預期的欄位結構，即使工作表是空的
            default_headers = ["建立日期", "類型", "snippet_id", "內容", "回顧日期", "完成狀態"]
            return pd.DataFrame(columns=default_headers), default_headers, []

        headers = values[0]
        data = values[1:] if len(values) > 1 else []

        # 確保所有行的列數與標題一致
        num_columns = len(headers)
        cleaned_data = []
        for i, row in enumerate(data):
            # 如果行比標題短，用空字串補齊
            row.extend([''] * (num_columns - len(row)))
            # 如果行比標題長，截斷
            cleaned_data.append(row[:num_columns])

        # 檢查 headers 是否為空列表
        if not headers:
             st.error("讀取的 Google Sheet 標頭行為空，無法處理資料。")
             # 使用預設標頭避免錯誤
             default_headers = ["建立日期", "類型", "snippet_id", "內容", "回顧日期", "完成狀態"]
             return pd.DataFrame(columns=default_headers), default_headers, []


        df = pd.DataFrame(cleaned_data, columns=headers)
        return df, headers, values # 返回 DataFrame, 標頭, 原始值 (包含標頭)
    except HttpError as e:
        st.error(f"讀取 Google Sheet 資料時發生錯誤: {e}")
        default_headers = ["建立日期", "類型", "snippet_id", "內容", "回顧日期", "完成狀態"]
        return pd.DataFrame(columns=default_headers), default_headers, []
    except Exception as e:
        st.error(f"處理資料時發生未知錯誤: {e}")
        default_headers = ["建立日期", "類型", "snippet_id", "內容", "回顧日期", "完成狀態"]
        return pd.DataFrame(columns=default_headers), default_headers, []


# --- 主要應用邏輯 ---

# --- UI 設定 ---
st.set_page_config(page_title="記憶追蹤器", layout="centered")
st.title("🌀 記憶追蹤器")
st.write("這是一個幫助你建立長期記憶回顧計劃的工具。")

# 載入資料
df, headers, all_values = load_data(gsheet, spreadsheet_id, sheet_tab)

# 檢查載入後的 headers 是否有效
if not headers:
    st.error("無法從 Google Sheet 獲取有效的欄位標頭，應用程式無法繼續。請檢查工作表是否至少包含一行標頭。")
    st.stop()

# 顯示資料表
# 如果 DataFrame 是空的 (但有 headers)，顯示帶有標題的空表格
if df.empty:
    st.info("目前沒有 Snippet 資料。")
    st.dataframe(pd.DataFrame(columns=headers)) # 顯示空的 DataFrame 架構
else:
    st.dataframe(df)


# --- 取得 Sheet ID ---
sheet_id_gid = get_sheet_id(gsheet, spreadsheet_id, sheet_tab)
if sheet_id_gid is None:
    # get_sheet_id 內部已有錯誤提示，這裡直接停止
    st.stop()


# --- 自動產生 Snippet ID ---
new_snippet_id = ""
snippet_id_col_name = "snippet_id" # 將欄位名稱定義為變數，方便修改

if snippet_id_col_name not in headers:
    st.warning(f"工作表中缺少 '{snippet_id_col_name}' 欄位，無法自動產生 ID 或執行刪除操作。請新增此欄位。")
    snippet_id_col_name = None # 標記此欄位不可用
    # 提供一個預設值或禁用相關功能
    new_snippet_id = f"{datetime.date.today().strftime('%Y%m%d')}-MANUAL"

else:
    today = datetime.date.today()
    today_str = today.strftime("%Y%m%d")
    # 篩選前確保 df 不是空的，且 snippet_id 欄存在且非空值
    if not df.empty and snippet_id_col_name in df.columns and not df[snippet_id_col_name].isnull().all():
         # 轉換為字串進行比較，更安全
        existing_today = df[df[snippet_id_col_name].astype(str).str.startswith(today_str, na=False)]
        # 從符合條件的 ID 中找出最大序號
        max_seq = 0
        for sid in existing_today[snippet_id_col_name]:
            try:
                # 假設 ID 格式為 YYYYMMDD-XX
                seq = int(sid.split('-')[-1])
                if seq > max_seq:
                    max_seq = seq
            except:
                pass # 忽略格式不符的 ID
        existing_count = max_seq # 最大序號即為下一個 ID 的基礎
    else:
        existing_count = 0
    new_snippet_id = f"{today_str}-{existing_count+1:02d}"


# --- 新增表單 ---
st.markdown("## ➕ 新增 Snippet")
with st.form("add_snippet_form"):
    col1, col2 = st.columns(2)

    # 使用 headers 列表檢查欄位是否存在
    type_options = ["quote", "vocab", "note", "other"]
    snippet_type = col1.selectbox("類型", type_options, key="add_type") if "類型" in headers else col1.text_input("類型 (欄位缺失)", key="add_type_alt")

    snippet_date = col2.date_input("建立日期", value=datetime.date.today()) if "建立日期" in headers else col2.date_input("建立日期 (欄位缺失)", value=datetime.date.today(), key="add_date_alt")

    # 顯示 Snippet ID 輸入框，如果欄位缺失則允許輸入
    if snippet_id_col_name:
        st.text_input("Snippet ID", value=new_snippet_id, disabled=True, key="add_snippet_id")
        current_snippet_id = new_snippet_id # 使用自動產生的ID
    else:
        current_snippet_id = st.text_input("Snippet ID (欄位缺失, 請手動輸入)", key="add_snippet_id_manual")


    snippet_content = st.text_area("內容") if "內容" in headers else st.text_area("內容 (欄位缺失)")
    review_days = st.text_input("回顧日（以逗號分隔）", "1,3,7,14,30")

    submitted = st.form_submit_button("新增")
    if submitted:
        # 檢查必要欄位
        if not snippet_content:
            st.warning("請輸入 Snippet 內容。")
        elif not snippet_id_col_name and not current_snippet_id:
             st.warning("工作表缺少 'snippet_id' 欄位，請在上方手動輸入 ID。")
        else:
            try:
                rows_to_add = []
                review_dates_list = [day.strip() for day in review_days.split(",") if day.strip().isdigit()]

                if not review_dates_list:
                    st.warning("請輸入有效的數字回顧日（例如 1, 3, 7）。")
                else:
                    for day in review_dates_list:
                        review_date_obj = snippet_date + datetime.timedelta(days=int(day))
                        review_date_str = review_date_obj.strftime("%Y-%m-%d") if "回顧日期" in headers else ""

                        # 根據 headers 建立資料字典，然後按順序生成列表
                        row_dict = {
                            "建立日期": snippet_date.strftime("%Y-%m-%d") if "建立日期" in headers else "",
                            "類型": snippet_type if "類型" in headers else "",
                            snippet_id_col_name if snippet_id_col_name else "snippet_id": current_snippet_id, # 使用 current_snippet_id
                            "內容": snippet_content if "內容" in headers else "",
                            "回顧日期": review_date_str,
                            "完成狀態": "FALSE" if "完成狀態" in headers else ""
                        }
                        # 確保即使欄位缺失，也是按照 headers 的順序填寫
                        new_row = [row_dict.get(header, "") for header in headers]
                        rows_to_add.append(new_row)

                    # 執行 Append 操作
                    gsheet.values().append(
                        spreadsheetId=spreadsheet_id,
                        range=sheet_tab, # 使用工作表名稱即可 for append
                        valueInputOption="USER_ENTERED",
                        insertDataOption="INSERT_ROWS", # 插入新行
                        body={"values": rows_to_add}
                    ).execute()

                    st.success("✅ Snippet 已新增！")
                    # 清除快取並重新執行以更新畫面
                    st.cache_data.clear()
                    st.rerun() # 使用 st.rerun() 替代舊版方法

            except HttpError as e:
                st.error(f"新增資料到 Google Sheet 時發生錯誤: {e}")
            except Exception as e:
                st.error(f"新增過程中發生未知錯誤: {e}")


# --- 刪除區塊 ---
st.markdown("---")
st.markdown("## 🗑️ 刪除 Snippet")

# 確保 'snippet_id' 欄位存在且 DataFrame 非空
if snippet_id_col_name and snippet_id_col_name in df.columns and not df.empty:
    # 處理可能的 NaN 或非字串類型
    valid_ids = df[snippet_id_col_name].dropna().astype(str).unique()
    unique_snippet_ids = sorted(valid_ids.tolist())

    if not unique_snippet_ids:
        st.info("目前沒有可刪除的 Snippet ID。")
    else:
        ids_to_delete = st.multiselect(
            "選擇要刪除的 Snippet ID (將刪除所有相關的回顧記錄):",
            options=unique_snippet_ids
        )

        if st.button("🟥 確認刪除選取的 Snippet"):
            if not ids_to_delete:
                st.warning("請先選擇要刪除的 Snippet ID。")
            else:
                try:
                    st.info(f"準備刪除 Snippet ID: {', '.join(ids_to_delete)} ...")
                    delete_placeholder = st.empty() # 建立一個空容器顯示進度

                    # **重要：** 重新獲取最新的數據和行號
                    latest_result = gsheet.values().get(
                        spreadsheetId=spreadsheet_id,
                        range=sheet_tab,
                        majorDimension='ROWS' # 確保是按行讀取
                    ).execute()
                    latest_values = latest_result.get("values", [])

                    if not latest_values or len(latest_values) <= 1:
                        delete_placeholder.warning("工作表似乎是空的或只有標題，無法執行刪除。")
                    else:
                        latest_headers = latest_values[0]
                        latest_data_rows = latest_values[1:]

                        # 再次確認 snippet_id 欄位索引
                        try:
                           id_column_index = latest_headers.index(snippet_id_col_name)
                        except ValueError:
                           delete_placeholder.error(f"在工作表中找不到 '{snippet_id_col_name}' 欄位，無法執行刪除。")
                           st.stop() # 停止執行

                        # 找出需要刪除的行的索引 (1-based index in the sheet)
                        row_indices_to_delete = []
                        for i, row in enumerate(latest_data_rows):
                            # 檢查行長度是否足夠，以及 ID 是否匹配 (轉換為字串比較)
                            if len(row) > id_column_index and str(row[id_column_index]) in ids_to_delete:
                                # i 是 data rows 的 0-based index
                                # 對應到 sheet 的 row index 是 i + 1 (因為 data 從第二行開始)
                                # API 的 DeleteDimensionRequest 需要 0-based index
                                sheet_row_index = i + 1 # 這是相對於 data rows 的 0-based index + 1 (跳過 header)
                                row_indices_to_delete.append(sheet_row_index)

                        if not row_indices_to_delete:
                            delete_placeholder.warning(f"在工作表中找不到對應 Snippet ID {', '.join(ids_to_delete)} 的資料列。")
                        else:
                            # **建立刪除請求 (從後往前刪除)**
                            requests = []
                            # 將 row indices 轉換為 API 需要的 0-based index 並降冪排序
                            api_indices_to_delete = sorted([idx for idx in row_indices_to_delete], reverse=True)
                            delete_placeholder.info(f"找到 {len(api_indices_to_delete)} 行符合條件，準備執行刪除...")

                            for index in api_indices_to_delete:
                                requests.append({
                                    "deleteDimension": {
                                        "range": {
                                            "sheetId": sheet_id_gid, # 使用之前獲取的 GID
                                            "dimension": "ROWS",
                                            # API index 是 0-based, sheet 第 index+1 行
                                            "startIndex": index, # 要刪除的行的起始索引 (0-based)
                                            "endIndex": index + 1   # 要刪除的行的結束索引 (不包含)
                                        }
                                    }
                                })

                            if requests:
                                # 執行批次更新
                                body = {"requests": requests}
                                gsheet.batchUpdate(
                                    spreadsheetId=spreadsheet_id,
                                    body=body
                                ).execute()
                                delete_placeholder.success(f"✅ Snippet ID: {', '.join(ids_to_delete)} 已成功刪除！")
                                # 清除快取並重新執行以更新畫面
                                st.cache_data.clear()
                                st.rerun() # 使用 st.rerun()
                            else:
                                delete_placeholder.warning("沒有產生任何刪除請求。")

                except HttpError as e:
                    st.error(f"刪除 Google Sheet 資料時發生錯誤: {e}")
                except Exception as e:
                    st.error(f"刪除過程中發生未知錯誤: {e}")
else:
     st.info("沒有可供刪除的 Snippet 資料 (工作表可能為空、缺少 'snippet_id' 欄位或該欄位無有效資料)。")

st.markdown("---")
# 可選：添加頁腳或其他資訊
st.caption(f"資料來源: Google Sheet (ID: {spreadsheet_id}, Tab: {sheet_tab})")
st.caption(f"目前時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")