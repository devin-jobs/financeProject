#今天即将休息 现阶段代码进度：能够实现基本的功能，
# 但是筛选日数据还是月数据 这两个地方有冲突
# 我注意到一点 我筛选日的时候 那个选择日的相关代码是放在filter_data函数体里面的
# 但是我晒选月的时候 选择月的相关代码是放在最下面 和调用函数是并列的
# 现在我们先把这两者进行统一 人晕了 合并的路线没搞通 今天12号 一来尝试老路了
import streamlit as st
import pandas as pd
import json
import redis
import re
from datetime import datetime
import matplotlib.pyplot as plt
import mplcursors
import plotly.express as px
import plotly.graph_objects as go


# 设置页面配置
st.set_page_config(page_title="My Streamlit App", page_icon=":rocket:", layout="wide", initial_sidebar_state="expanded")

st.title("Welcome to my Streamlit App")

# 添加自定义 CSS 来设置主题
st.markdown(
    """
    <style>
    /* 设置背景颜色和文字颜色 */
    body {
        background-color: #F5F5F5;
        color: #333333;
    }

    /* 设置标题的样式 */
    h1 {
        color: #FF5733;
    }

    /* 设置按钮的样式 */
    .stButton > button {
        background-color: #007BFF;
        color: white;
    }

    /* 设置输入框的样式 */
    .stTextInput > div > div > input {
        background-color: #ECECEC;
    }

    /* 设置侧边栏的样式 */
    .css-10trblm.e1fqkh3o4 {
        background-color: #ECECEC;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.header('个人理财系统')
# 定义固定的开始和结束日期
start_date = datetime(2022, 1, 1).date()
end_date = datetime(2024, 12, 31).date()

# 创建Redis连接
r = redis.Redis(host='localhost', port=6379, db=0)

# 初始化session_state中的记录，包含表头
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

# 定义一个函数用来检查这列数据的合法性
def is_valid_row(row):
    return (
        (isinstance(row["收入/支出"], str) and bool(chinese_pattern.match(row["收入/支出"])) or row["收入/支出"] is None)
        and (isinstance(row["金额"], (int, float)) or row["金额"] is None)
        and (isinstance(row["明细备注"], str) and bool(chinese_pattern.match(row["明细备注"])) or row["明细备注"] is None)
        and (isinstance(row["日期"], str) and bool(date_pattern.match(row["日期"])) or row["日期"] is None)
    )

def show_edit_income_expense_table():
    # 将当前records转换为DataFrame以便于编辑
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

    # 当用户点击保存按钮时，验证数据并保存
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

def filter_data():
    # 创建UI控件供用户选择筛选模式
    mode = st.selectbox('选择筛选模式', ['by_date', 'by_month'])

    # 检查session_state中是否存在'records'，如果不存在则初始化为空列表
    if 'records' not in st.session_state:
        st.session_state.records = []

    # 将records转换为DataFrame以利用pandas的功能
    records_df = pd.DataFrame(st.session_state.records)

    # 尝试将日期列转换为datetime格式
    if '日期' in records_df.columns:
        records_df['日期'] = pd.to_datetime(records_df['日期'], errors='coerce')

    if mode == 'by_date':
        selected_date = st.date_input("选择日期", value=datetime.now().date())
        if selected_date:
            # 筛选数据
            filtered_df = records_df[records_df['日期'].dt.date == selected_date]
            return filtered_df

    elif mode == 'by_month':
        # 设置年份滑动条的范围为从10年前到当前年份
        current_year = datetime.now().year
        year_range = range(current_year - 10, current_year + 1)
        selected_year = st.slider('选择年份', min_value=min(year_range), max_value=max(year_range), value=current_year)

        # 设置月份滑动条的默认值为当前月份
        current_month = datetime.now().month
        selected_month = st.slider('选择月份', 1, 12, value=current_month)

        # 筛选数据
        filtered_df = records_df[
            (records_df['日期'].dt.year == selected_year) & (records_df['日期'].dt.month == selected_month)]
        return filtered_df

    # 如果没有选择任何模式，返回空的DataFrame
    return pd.DataFrame()

def visualize_income_expense(df):
    # 确保数据存在且非空
    if df is not None and not df.empty:
        # 绘制饼图
        income_data = df[df['收入/支出'] == '收入'].groupby('明细备注')['金额'].sum().reset_index()
        if not income_data.empty:
            fig1 = px.pie(income_data, values='金额', names='明细备注',
                          title='收入分布', labels={'明细备注': '明细备注', '金额': '金额'})
            fig1.update_traces(textinfo='percent+label+value')
            st.plotly_chart(fig1)

        # 绘制支出饼图
        expense_data = df[df['收入/支出'] == '支出'].groupby('明细备注')['金额'].sum().reset_index()
        if not expense_data.empty:
            fig2 = px.pie(expense_data, values='金额', names='明细备注',
                          title='支出分布', labels={'明细备注': '明细备注', '金额': '金额'})
            fig2.update_traces(textinfo='percent+label+value')
            st.plotly_chart(fig2)

        # 新增部分：按日分组绘制收入柱形图
        # 确保日期列是datetime类型
        df['日期'] = pd.to_datetime(df['日期'])

        # 按日分组计算收入总额
        daily_income = df[df['收入/支出'] == '收入'].groupby(df['日期'].dt.date)['金额'].sum()

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
    else:
        st.warning("数据集为空，无法进行可视化。")

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




# 调用函数模块
show_edit_income_expense_table()

# 调用 filter_data 函数获取筛选后的数据
filtered_df = filter_data()

# 检查返回的 DataFrame 是否为空
if not filtered_df.empty:
    # 展示筛选后的 DataFrame
    st.dataframe(filtered_df)

    # 计算并展示收入和支出总和
    income_total = filtered_df[filtered_df['收入/支出'] == '收入']['金额'].sum()
    expense_total = filtered_df[filtered_df['收入/支出'] == '支出']['金额'].sum()
    st.write(f"期间收入总和: {income_total}")
    st.write(f"期间支出总和: {expense_total}")

    # 调用 visualize_income_expense 函数，传递筛选后的数据
    visualize_income_expense(filtered_df)
else:
    st.write("无符合条件的数据")


st.write("Ready to launch your Streamlit app!")