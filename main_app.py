
# --- 週視圖（表格版月曆，依使用者設計圖實作）---
st.markdown("### 🗓️ 最近 4 週回顧任務")

# 計算最近 4 週起始日（週一）
start_of_week = today - timedelta(days=today.weekday())
end_date = start_of_week + timedelta(days=27)
days_range = pd.date_range(start=start_of_week, end=end_date)

# 將日期補齊成 7 天為單位的格子列表
first_day_index = days_range[0].weekday()
padded_days = [None] * first_day_index + list(days_range)
while len(padded_days) % 7 != 0:
    padded_days.append(None)
weeks = [padded_days[i:i+7] for i in range(0, len(padded_days), 7)]

# 星期列
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 渲染表格
calendar_html = "<style>table.calendar { border-collapse: collapse; width: 100%; table-layout: fixed; }"
calendar_html += "table.calendar td, table.calendar th { border: 1px solid #ccc; vertical-align: top; padding: 4px; font-size: 12px; }"
calendar_html += "table.calendar th { background: #f0f0f0; text-align: center; font-weight: bold; }</style>"
calendar_html += "<table class='calendar'>"
calendar_html += "<tr>" + "".join(f"<th>{day}</th>" for day in day_names) + "</tr>"

# 填入每格資料（checkbox 為 disabled 樣式展示）
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
