
import streamlit as st
import pandas as pd
import json
import redis
import re
import datetime
import matplotlib.pyplot as plt
import mplcursors
import plotly.express as px
import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta
import calendar

# 定义固定的开始和结束日期
start_date = datetime.date(2024, 1, 1)
end_date = datetime.date(2024, 12, 31)

# 创建Redis连接
r = redis.Redis(host='localhost', port=6379, db=0)

# 初始化session_state中的记录，包含表头 我的redis数据库中有一个键叫做 income_date
if 'records' not in st.session_state:
    data_from_redis = r.get('income_data')
    if data_from_redis:
        st.session_state.records = json.loads(data_from_redis.decode('utf-8'))
    else:
        # 如果没有从Redis获取到数据，初始化st.session_state.records
        st.session_state.records = [
            {"收入/支出": "", "金额": 0, "明细备注": "", "日期": pd.NaT}  # 使用pd.NaT表示缺失日期
        ]

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

def show_edit_income_expense_table():
    # 将当前records转换为DataFrame以便于编辑 数据一开始放在df_income_expense
    if len(st.session_state.records) > 1:
        df_income_expense = pd.DataFrame(st.session_state.records[1:])
    else:
        df_income_expense = pd.DataFrame(columns=["收入/支出", "金额", "明细备注", "日期"])

    # 使用pd.to_datetime将日期列转换为pd.Timestamp类型
    df_income_expense['日期'] = pd.to_datetime(df_income_expense['日期'], errors='coerce')

    # 使用st.data_editor创建一个可编辑的表格
    edited_df_income_expense = st.data_editor(df_income_expense,
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

    # 保存按钮
    save_button = st.button('保存')

    # 当用户点击保存按钮时，验证数据并保存 可编辑表格数据被填充后
    if save_button and edited_df_income_expense is not None:
        # 验证收入/支出来源和明细备注，确保只包含中文字符和空格
        def is_valid_chinese_string(s):
            return s is None or isinstance(s, str) and bool(chinese_pattern.match(s))

        # 新增一行验证，确保收入/支出列只允许输入"收入"、"支出"或None
        def is_valid_income_or_expense(income_expense):
            return income_expense in ["收入", "支出", None]

        if not all(edited_df_income_expense["收入/支出"].apply(is_valid_income_or_expense)):
            st.error("收入/支出只能输入'收入'、'支出'或留空，请检查并重新输入。")
            return
        if not all(edited_df_income_expense["明细备注"].apply(is_valid_chinese_string)):
            st.error("明细备注只能包含中文字符，请检查并重新输入。")
            return

        # 验证金额是否在指定范围内
        if (edited_df_income_expense["金额"] < -100000).any() or (edited_df_income_expense["金额"] > 100000).any():
            st.error("金额必须介于-100000和100000之间，请检查并重新输入。")
            return

        edited_df_income_expense['日期'] = edited_df_income_expense['日期'].astype(str)

        # 更新st.session_state.records，始终保留表头
        st.session_state.records = [st.session_state.records[0]] + edited_df_income_expense.to_dict('records')

        # 将更新后的数据保存到Redis，先将数据转换为JSON字符串
        r.set('income_data', json.dumps(st.session_state.records).encode('utf-8'))

    else:
        df_income_expense = pd.DataFrame(columns=["收入/支出", "金额", "明细备注", "日期"])




def filter_data(records, start_date, end_date):
    # 确保start_date和end_date也是datetime.date类型
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # 筛选数据
    filtered_records = []
    income_total = 0
    expense_total = 0

    for record in records:
        if type(record['日期']) == str:
            try:
                # 转换记录中的日期为datetime.date类型
                record_date = datetime.strptime(record['日期'], '%Y-%m-%d').date()
                # 检查日期是否在范围内
                if start_date <= record_date <= end_date:
                    filtered_records.append(record)
                    if record['收入/支出'] == '收入':
                        income_total += record['金额']
                    elif record['收入/支出'] == '支出':
                        expense_total += record['金额']
            except ValueError:
                pass  # 忽略无法转换的日期

    # 将筛选出的数据转换为DataFrame
    if filtered_records:
        filtered_df = pd.DataFrame(filtered_records)

        # 展示DataFrame
        st.dataframe(filtered_df)

        # 展示收入和支出的总和
        st.write(f"期间收入总和: {income_total}")
        st.write(f"期间支出总和: {expense_total}")
        return filtered_df

    else:
        st.write("无符合条件的数据")
        return None
#定义一个可视化展示函数 用来实现可视化处理
def visualize_income_expense(filtered_df):
    if filtered_df is None:
        st.warning("数据集为空，无法进行可视化。")
        return

    # 绘制收入饼图
    income_data = filtered_df[filtered_df['收入/支出'] == '收入'].groupby('明细备注')['金额'].sum().reset_index()
    if not income_data.empty:
        fig1 = px.pie(income_data, values='金额', names='明细备注',
                      title='收入分布', labels={'明细备注': '明细备注', '金额': '金额'})
        fig1.update_traces(textinfo='percent+label+value')
        st.plotly_chart(fig1)

    # 绘制支出饼图
    expense_data = filtered_df[filtered_df['收入/支出'] == '支出'].groupby('明细备注')['金额'].sum().reset_index()
    if not expense_data.empty:
        fig2 = px.pie(expense_data, values='金额', names='明细备注',
                      title='支出分布', labels={'明细备注': '明细备注', '金额': '金额'})
        fig2.update_traces(textinfo='percent+label+value')
        st.plotly_chart(fig2)

        # 新增部分：按日分组绘制收入柱形图
    if not filtered_df.empty:
        # 确保日期列是datetime类型
        filtered_df['日期'] = pd.to_datetime(filtered_df['日期'])

        # 按日分组计算收入总额
        daily_income = filtered_df[filtered_df['收入/支出'] == '收入'].groupby(filtered_df['日期'].dt.date)[
            '金额'].sum()

        # 创建柱形图
        fig3 = go.Figure(data=[go.Bar(
            x=daily_income.index,
            y=daily_income.values,
            marker=dict(color='green')
        )])

        fig3.update_layout(
            title='每日收入变化',
            xaxis_title='日期',
            yaxis_title='收入',
            xaxis=dict(type='category'),  # 使x轴按照日期分类显示
        )
        st.plotly_chart(fig3)


#增加批量导入数据功能
# 添加文件上传器
uploaded_file = st.file_uploader("上传收入支出数据文件", type=['csv', 'xlsx'])

# 如果文件被上传
if uploaded_file is not None:
    # 根据文件类型读取数据
    if uploaded_file.name.endswith('.csv'):
        df_import = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        df_import = pd.read_excel(uploaded_file)

    # 将数据转换为合适的格式 转换为字符串格式，以便于JSON序列化
    df_import['日期'] = pd.to_datetime(df_import['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_import['金额'] = pd.to_numeric(df_import['金额'], errors='coerce')

    # 检查数据的合法性
    if all(df_import.apply(is_valid_row, axis=1)):
        # 将导入的数据转换为字典列表 to_dict()函数的功能
        new_records = df_import.to_dict('records')

        # 添加到现有的数据中
        st.session_state.records.extend(new_records)

        # 将更新后的数据保存到Redis
        r.set('income_data', json.dumps(st.session_state.records).encode('utf-8'))

        st.success("数据导入成功！")
    else:
        st.error("导入的数据包含不合法的条目，请检查数据格式。")


# 显示和编辑收入支出表格
show_edit_income_expense_table()


# UI元素让使用者选择查看某一天或某个月的具体日期范围
is_selecting_day = st.checkbox("选择查看具体的一天？")

if is_selecting_day:
    # 用户选择查看某一天
    selected_date = st.date_input("选择具体的日期:", value=datetime.date.today())
    start_date = end_date = selected_date.strftime('%Y-%m-%d')
else:
    # 用户选择查看某个月
    # 首先获取当前月的第一天和最后一天作为默认值
    today = datetime.date.today()
    start_of_month = datetime.date(today.year, today.month, 1)
    _, days_in_month = calendar.monthrange(today.year, today.month)
    end_of_month = datetime.date(today.year, today.month, days_in_month)

    # 使用两个date_input来分别选择开始和结束日期
    selected_start = st.date_input("选择月份的开始日期:", value=start_of_month)
    selected_end = st.date_input("选择月份的结束日期:", value=end_of_month)

    # 确保结束日期不会小于开始日期
    if selected_end < selected_start:
        selected_end = selected_start

    start_date = selected_start.strftime('%Y-%m-%d')
    end_date = selected_end.strftime('%Y-%m-%d')

# 显示选择的日期范围
st.write(f"您选择了从 {start_date} 到 {end_date} 的数据。")

# 调用filter_data函数筛选数据
filtered_df = filter_data(st.session_state.records, start_date, end_date)

# 对筛选后的数据进行可视化
if filtered_df is not None:
    visualize_income_expense(filtered_df)

