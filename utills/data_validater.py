import json
import re
import datetime
import streamlit as st
import pandas as pd


# 正则表达式，用于检查日期格式是否为 YYYY-MM-DD
date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# 创建正则表达式模式以匹配中文字符
chinese_pattern = re.compile(r'^$|^\s*$|^[\u4e00-\u9fa5]+$', re.U)

# 定义一个函数用来检查这列数据的合法性
def is_valid_row(row):
    return (
        (isinstance(row["收入/支出"], str) and bool(chinese_pattern.match(row["收入/支出"])) or row["收入/支出"] is None)
        and (isinstance(row["金额"], (int, float)) or row["金额"] is None)
        and (isinstance(row["明细备注"], str) and bool(chinese_pattern.match(row["明细备注"])) or row["明细备注"] is None)
        and (isinstance(row["日期"], str) and bool(date_pattern.match(row["日期"])) or row["日期"] is None)
    )

def validate_and_save_data(records,df_income_expense):
    from app import r
    # 保存按钮
    save_button = st.button('保存')

    # 当用户点击保存按钮时，验证数据并保存
    if save_button and records is not None:
        # 验证收入/支出来源和明细备注，确保只包含中文字符和空格
        def is_valid_chinese_string(s):
            return s is None or isinstance(s, str) and bool(chinese_pattern.match(s))

        # 新增一行验证，确保收入/支出列只允许输入"收入"、"支出"或None
        def is_valid_income_or_expense(income_expense):
            return income_expense in ["收入", "支出", None]

        if not all(records["收入/支出"].apply(is_valid_income_or_expense)):
            st.error("收入/支出只能输入'收入'、'支出'或留空，请检查并重新输入。")
            return
        if not all(records["明细备注"].apply(is_valid_chinese_string)):
            st.error("明细备注只能包含中文字符，请检查并重新输入。")
            return

        # 验证金额是否在指定范围内
        if (records["金额"] < -100000).any() or (records["金额"] > 100000).any():
            st.error("金额必须介于-100000和100000之间，请检查并重新输入。")
            return

        records['日期'] = records['日期'].astype(str)

        # 更新st.session_state.records，始终保留表头
        st.session_state.records = [st.session_state.records[0]] + records.to_dict('records')

        # 将更新后的数据保存到Redis，先将数据转换为JSON字符串
        r.set('income_data', json.dumps(st.session_state.records).encode('utf-8'))

    else:
        df_income_expense = pd.DataFrame(columns=["收入/支出", "金额", "明细备注", "日期"])

