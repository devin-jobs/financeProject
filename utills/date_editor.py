
import re
import json
import redis
import datetime
import streamlit as st
import pandas as pd
from data_validater import validate_and_save_data

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

    # 使用 pd.to_datetime 将日期列转换为 pd.Timestamp 类型，单个单个 Timestamp 输出结果是2023-01-01 00:00:00格式
    # 将日期列转换为 pd.Timestamp 类型，并将时间设为午夜 # 添加午夜时间
    df_income_expense['日期'] = pd.to_datetime(df_income_expense['日期'], errors='coerce').dt.floor('D')
    df_income_expense['日期'] = df_income_expense['日期'].apply(lambda x: x.replace(hour=0, minute=0, second=0))

    # 创建第一个data_editor为了方便输入数据 创建一个空的 DataFrame 作为输入模板
    df_input_template = pd.DataFrame(columns=["收入/支出", "金额", "明细备注", "日期"])
    input_table = st.data_editor(
        df_input_template,
        column_config={
            "金额": st.column_config.NumberColumn("金额", min_value=-100000, max_value=100000),
            "收入/支出": st.column_config.TextColumn("收入/支出"),
            "明细备注": st.column_config.TextColumn("明细备注"),
            "日期": st.column_config.DatetimeColumn("日期"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="input_table",
    )

    # 添加一个新的按钮 第一个
    new_save_button = st.button("提交数据")
    st.header("数据展示")

    # 使用 st.data_editor 创建第二个可编辑的表格
    table_record = st.data_editor(
        #df_income_expense含有旧的数据
        df_income_expense,
        column_config={
            "金额": st.column_config.NumberColumn("金额", min_value=-100000, max_value=100000),
            "收入/支出": st.column_config.TextColumn("收入/支出"),
            "明细备注": st.column_config.TextColumn("明细备注"),
            "日期": st.column_config.DatetimeColumn("日期"),
        },
        num_rows=8,
        use_container_width=True,
        key="income_expense_table",
    )
    # 合并两个表格
    # 新增代码：合并表格前确保日期列的类型一致
    input_table['日期'] = pd.to_datetime(input_table['日期'], errors='coerce').dt.floor('D')
    input_table['日期'] = input_table['日期'].apply(lambda x: x.replace(hour=0, minute=0, second=0))

    # 新增代码：合并表格
    table_record = pd.concat([input_table, table_record], ignore_index=True)

    # if new_save_button:
    #     # 清除输入表格的内容
    #     input_table.drop(input_table.index, inplace=True)

    # 清除输入表格的内容
    input_table.drop(input_table.index, inplace=True)
    # 保存按钮
    save_button = st.button('保存')

    # 返回合并后的表格
    return table_record, df_income_expense,new_save_button, save_button

def handle_submit_and_save_buttons(table_records, df_income_expenses,new_save_button, save_button):
    if new_save_button or save_button:
        validate_and_save_data(table_records, df_income_expenses,new_save_button, save_button)