
import re
import json
import redis
import datetime
import streamlit as st
import pandas as pd


def show_edit_income_expense_table():
    # 将当前records转换为DataFrame以便于编辑
    if len(st.session_state.records) > 1:
        df_income_expense = pd.DataFrame(st.session_state.records[1:])
    else:
        df_income_expense = pd.DataFrame(columns=["收入/支出", "金额", "明细备注", "日期"])

    # 使用pd.to_datetime将日期列转换为pd.Timestamp类型
    df_income_expense['日期'] = pd.to_datetime(df_income_expense['日期'], errors='coerce')

    # 使用st.data_editor创建一个可编辑的表格
    table_record = st.data_editor(df_income_expense,
                                              column_config={
                                                  "金额": st.column_config.NumberColumn("金额", min_value=-100000,
                                                                                        max_value=100000),
                                                  "收入/支出": st.column_config.TextColumn("收入/支出"),
                                                  "明细备注": st.column_config.TextColumn("明细备注"),
                                                  "日期": st.column_config.DatetimeColumn("日期")
                                              },
                                              num_rows="dynamic",
                                              use_container_width=True,
                                              key="income_expense_table")
    return table_record, df_income_expense


