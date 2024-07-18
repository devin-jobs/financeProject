import re
import streamlit as st
import pandas as pd
from datetime import datetime
import json
import redis

# 创建正则表达式模式以匹配中文字符
chinese_pattern = re.compile(r'^$|^\s*$|^[\u4e00-\u9fa5]+$', re.U)

# 正则表达式，用于检查日期格式是否为 YYYY-MM-DD
date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')


# 定义一个函数用来检查导入的文件的数据的合法性
def is_valid_row(row):
    return (
        (isinstance(row["收入/支出"], str) and bool(chinese_pattern.match(row["收入/支出"])) or row["收入/支出"] is None)
        and (isinstance(row["金额"], (int, float)) or row["金额"] is None)
        and (isinstance(row["明细备注"], str) and bool(chinese_pattern.match(row["明细备注"])) or row["明细备注"] is None)
        and (isinstance(row["日期"], str) and bool(date_pattern.match(row["日期"])) or row["日期"] is None)
    )

def import_data_from_file():
    # 增加批量导入数据功能
    # 添加文件上传器
    uploaded_file = st.file_uploader("上传收入支出数据文件", type=['csv', 'xlsx'])

    # 如果文件被上传
    if uploaded_file is not None:
        # 根据文件类型读取数据
        if uploaded_file.name.endswith('.csv'):
            df_import = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df_import = pd.read_excel(uploaded_file)

        # 将数据转换为合适的格式
        df_import['日期'] = pd.to_datetime(df_import['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_import['金额'] = pd.to_numeric(df_import['金额'], errors='coerce')

        # 检查数据的合法性
        if all(df_import.apply(is_valid_row, axis=1)):
            # 将导入的数据转换为字典列表
            new_records = df_import.to_dict('records')

            # 添加到现有的数据中
            if 'records' not in st.session_state:
                st.session_state.records = []
            st.session_state.records.extend(new_records)

            # 将更新后的数据保存到Redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.set('income_data', json.dumps(st.session_state.records).encode('utf-8'))

            st.success("数据导入成功！")
        else:
            st.error("导入的数据包含不合法的条目，请检查数据格式。")

