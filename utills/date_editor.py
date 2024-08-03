
import re
import json
import redis
import datetime
import streamlit as st
import pandas as pd


def show_edit_income_expense_table():
    """
    展示一个可编辑的收入和支出表格。

    如果 `st.session_state.records` 包含至少两条记录（第一条是表头），则创建一个 DataFrame，
    否则创建一个空的 DataFrame 并设置列名。
    """

    # 将当前 records 转换为 DataFrame 以便于编辑
    if len(st.session_state.records) > 1:
        df_income_expense = pd.DataFrame(st.session_state.records[1:])  # 不包含表头的第一条记录
    else:
        # 如果没有足够的记录，创建一个空的 DataFrame 并设置列名
        df_income_expense = pd.DataFrame(
            columns=["收入/支出", "金额", "明细备注", "日期"]
        )  # 设置列名，但不包含任何数据

    # # 使用 pd.to_datetime 将日期列转换为 pd.Timestamp 类型，单个单个 Timestamp 输出结果是2023-01-01 00:00:00格式
    # df_income_expense["日期"] = pd.to_datetime(df_income_expense["日期"], errors="coerce")

    # 将日期列转换为 pd.Timestamp 类型，并将时间设为午夜
    df_income_expense['日期'] = pd.to_datetime(df_income_expense['日期'], errors='coerce').dt.floor('D')
    # 添加午夜时间
    df_income_expense['日期'] = df_income_expense['日期'].apply(lambda x: x.replace(hour=0, minute=0, second=0))



    # 使用 st.data_editor 创建一个可编辑的表格
    table_record = st.data_editor(
        df_income_expense,
        column_config={
            "金额": st.column_config.NumberColumn("金额", min_value=-100000, max_value=100000),
            "收入/支出": st.column_config.TextColumn("收入/支出"),
            "明细备注": st.column_config.TextColumn("明细备注"),
            "日期": st.column_config.DatetimeColumn("日期"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="income_expense_table",
    )

    return table_record, df_income_expense




