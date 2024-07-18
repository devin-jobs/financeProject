import datetime
import calendar
import pandas as pd
import streamlit as st


def filter_data(records, view, selected_date):
    # 如果view为'daily'，则直接使用selected_date
    if view == 'daily':
        # 确保selected_date是一个datetime对象
        if isinstance(selected_date, datetime.date):
            start_date = end_date = datetime.datetime.combine(selected_date, datetime.time.min)
        else:
            raise ValueError("Daily view expects a date object.")
    else:  # 否则，我们假设view为'monthly'
        if isinstance(selected_date, str):
            # 从selected_date获取月份和年份
            year, month = map(int, selected_date.split('/'))
            # 计算筛选的起始和结束日期
            start_date = datetime.datetime(year, month, 1)
            _, days_in_month = calendar.monthrange(year, month)
            end_date = start_date.replace(day=days_in_month)
        else:
            raise ValueError("Monthly view expects a string in the format 'YYYY/MM'.")

    # 筛选数据
    filtered_records = []
    income_total = 0
    expense_total = 0

    for record in records:
        if isinstance(record['日期'], str):
            try:
                # 转换记录中的日期为datetime.date类型
                record_date = datetime.datetime.strptime(record['日期'], '%Y-%m-%d').date()

                # 检查日期是否在范围内
                if start_date.date() <= record_date <= end_date.date():
                    filtered_records.append(record)
                    if record['收入/支出'] == '收入':
                        income_total += record['金额']
                    elif record['收入/支出'] == '支出':
                        expense_total += record['金额']

            except ValueError:
                pass  # 忽略无法转换的日期

    # 将筛选出的数据转换为DataFrame，确保即使列表为空也返回一个DataFrame
    filtered_df = pd.DataFrame(filtered_records) if filtered_records else pd.DataFrame(
        columns=['日期', '收入/支出', '金额', '明细备注'])

    # 确保'日期'列是datetime类型
    filtered_df['日期'] = pd.to_datetime(filtered_df['日期'], errors='coerce')

    # # 展示DataFrame
    # st.dataframe(filtered_df)
    #
    # # 展示收入和支出的总和
    # st.write(f"期间收入总和: {income_total}")
    # st.write(f"期间支出总和: {expense_total}")
    #
    # return filtered_df

    return filtered_df, income_total, expense_total