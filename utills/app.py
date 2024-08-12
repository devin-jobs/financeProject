import json
import redis
import datetime
import pandas as pd
from PIL import Image
import streamlit as st
import plotly.express as px
from filter import filter_data
import plotly.graph_objects as go
from data_import import import_data_from_file
from data_validater import validate_and_save_data
from date_editor import show_edit_income_expense_table,handle_submit_and_save_buttons

# 创建Redis连接
r = redis.Redis(host='localhost', port=6379, db=0)

# 定义固定的开始和结束日期
start_date = datetime.date(2024, 1, 1)
end_date = datetime.date(2024, 12, 31)

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

# 定义获取今天的记录函数
def get_today_records(records):
    today = datetime.datetime.now().date()
    today_records = [record for record in records if pd.to_datetime(record['日期']).date() == today]
    return today_records

def login():
    username = st.text_input('Username:')
    password = st.text_input('Password:', type='password')
    if st.button('Login'):
        if username and password:
            # 验证用户凭证
            if username == 'admin' and password == 'secret':
                st.session_state.logged_in = True
            else:
                st.error('Invalid credentials.')
                return False
        else:
            st.error('Please enter both username and password.')
            return False
    return False
def main_program():
    # 如果已登录，则隐藏登录表单
    if st.session_state.logged_in:
        # ----- TITLE & TABS -----
        # 页面布局，一共由四个tab组成
        st.header('Personal Finance Dashboard')
        tab1, tab2, tab3 = st.tabs(['今天收支', '数据录入', '可视化展示'])

        # ----- SIDE BAR -----
        with st.sidebar:
            st.title('个人主页')

        # ----- Today -----
        with tab1:
            with st.container():
                # 展示今天的记录
                today_records = get_today_records(st.session_state.records)
                if today_records:
                    st.subheader("今天收支")
                    st.dataframe(today_records, use_container_width=True)
                else:
                    st.warning("No records found for today.")

                image = Image.open('D:/pycharm/python_project/financeProject/utills/images/dog.png')
                # image = Image.open('static/images/logo.png')
                # image = Image.open('images/logo.png')
                st.image(image, caption='lucky dog')

        with tab2:
            # st.title("数据录入")
            #  ----- 创建上下的布局 -----
            top_container = st.container()
            bottom_container = st.container()

            #  ----- 顶部的容器  文件导入 -----
            with top_container:
                st.header("批量导入文件")
                import_data_from_file()

            #  ----- 底部的容器 可编辑图表 验证数据并保存 -----
            with bottom_container:
                st.header("添加数据")
                # show_edit_income_expense_table函数的两个按钮对应的两个表格 点击提交数据和保存都会触发相同的功能
                # 有点混乱 为了让两个按钮联合起来 handle_submit_and_save_buttons又包含了data_validater的检查函数（检查数据并保存）
                table_records, df_income_expenses, new_save_button, save_button = show_edit_income_expense_table()

                handle_submit_and_save_buttons(table_records, df_income_expenses, new_save_button, save_button)

        with tab3:
            with st.container():
                st.header('视图')
                # Views filter
                view = st.radio("Select view:", ["monthly", "daily"], index=1, horizontal=True, key="sidebar")

                # 用户可以选择一个日期或月份
                if view == 'daily':
                    # 设置默认日期为今天
                    today = datetime.datetime.now().date()
                    daily_view_date = st.date_input("选择日期", value=today)
                    filtered_df, income_total, expense_total = filter_data(st.session_state.records, 'daily',
                                                                           daily_view_date)
                    st.markdown("""---""")

                    # 展示DataFrame
                    st.dataframe(filtered_df, use_container_width=True)

                    # 展示收入和支出的总和
                    st.write(f"期间收入总和: {income_total}")
                    st.write(f"期间支出总和: {expense_total}")

                    b1, b2 = st.columns(2)
                    with b1:
                        # 绘制收入饼图
                        income_data = filtered_df[filtered_df['收入/支出'] == '收入'].groupby('明细备注')[
                            '金额'].sum().reset_index()
                        if not income_data.empty:
                            fig1 = px.pie(income_data, values='金额', names='明细备注',
                                          title='收入分布', labels={'明细备注': '明细备注', '金额': '金额'})
                            fig1.update_traces(textinfo='percent+label+value')
                            st.plotly_chart(fig1)
                    with b2:
                        # 绘制支出饼图
                        expense_data = filtered_df[filtered_df['收入/支出'] == '支出'].groupby('明细备注')[
                            '金额'].sum().reset_index()
                        if not expense_data.empty:
                            fig2 = px.pie(expense_data, values='金额', names='明细备注',
                                          title='支出分布', labels={'明细备注': '明细备注', '金额': '金额'})
                            fig2.update_traces(textinfo='percent+label+value')
                            st.plotly_chart(fig2)
                elif view == 'monthly':
                    # 生成月份和年份的选项列表
                    months_years = [f"{year}/{month:02d}" for year in range(2024, 2026) for month in range(1, 13)]

                    # 获取当前的年月并确保它存在于列表中
                    current_month_year = f"{datetime.datetime.now().year}/{datetime.datetime.now().month:02d}"
                    if current_month_year not in months_years:
                        current_month_year = months_years[0]

                    # 设置默认选项为当前年月
                    selected_month_year = st.selectbox("选择月份", months_years,
                                                       index=months_years.index(current_month_year))

                    filtered_df, income_total, expense_total = filter_data(st.session_state.records, 'monthly',
                                                                           selected_month_year)

                    # 展示DataFrame
                    st.dataframe(filtered_df, use_container_width=True)

                    # 展示收入和支出的总和
                    st.write(f"期间收入总和: {income_total}")
                    st.write(f"期间支出总和: {expense_total}")

                    b1, b2 = st.columns(2)
                    with b1:
                        # 绘制收入饼图
                        income_data = filtered_df[filtered_df['收入/支出'] == '收入'].groupby('明细备注')[
                            '金额'].sum().reset_index()
                        if not income_data.empty:
                            fig1 = px.pie(income_data, values='金额', names='明细备注',
                                          title='收入分布', labels={'明细备注': '明细备注', '金额': '金额'})
                            fig1.update_traces(textinfo='percent+label+value')
                            st.plotly_chart(fig1)
                    with b2:
                        # 绘制支出饼图
                        expense_data = filtered_df[filtered_df['收入/支出'] == '支出'].groupby('明细备注')[
                            '金额'].sum().reset_index()
                        if not expense_data.empty:
                            fig2 = px.pie(expense_data, values='金额', names='明细备注',
                                          title='支出分布', labels={'明细备注': '明细备注', '金额': '金额'})
                            fig2.update_traces(textinfo='percent+label+value')
                            st.plotly_chart(fig2)

                    st.markdown("""---""")

                    c1, c2 = st.columns(2)
                    # 绘制收入树状图
                    with c1:
                        if not filtered_df.empty:
                            # 确保日期列是datetime类型
                            filtered_df['日期'] = pd.to_datetime(filtered_df['日期'])

                            # 按日分组计算收入总额
                            daily_income = \
                                filtered_df[filtered_df['收入/支出'] == '收入'].groupby(filtered_df['日期'].dt.date)[
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

                    # 绘制收入树状图
                    with c2:
                        if not filtered_df.empty:
                            # 确保日期列是datetime类型
                            filtered_df['日期'] = pd.to_datetime(filtered_df['日期'])

                            # 按日分组计算收入总额
                            daily_income = \
                                filtered_df[filtered_df['收入/支出'] == '支出'].groupby(
                                    filtered_df['日期'].dt.date)[
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
                                yaxis_title='支出',
                                xaxis=dict(type='category'),  # 使x轴按照日期分类显示
                            )
                            st.plotly_chart(fig3)

                else:
                    st.warning("未选择有效的视图选项。")
    else:
        # 显示登录表单
        st.markdown('<div style="background-color: white; padding: 1rem;">')
        st.markdown(f'<h1 style="color: black">Personal Finance Dashboard</h1>')
        st.markdown('<hr/>')
        st.markdown('<p>Today\'s Income and Expenditure | Data Entry | Visualizations</p>')
        st.markdown('</div>')

        # LOGIN
        st.markdown('<div style="background-color: white; padding: 1rem;">')
        st.markdown('<form action="">')
        st.markdown(f'<input type="text" placeholder="Username" value="{st.session_state.username}" />')
        st.markdown(f'<input type="password" placeholder="Password" value="{st.session_state.password}" />')
        st.markdown('<button>Login</button>')
        st.markdown('</form>')
        st.markdown('</div>')
# 主函数
def main():
    # 页面设置
    st.set_page_config(page_title='Personal Finance Dashboard',
                       page_icon=':money_with_wings:',
                       layout='wide')
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ''
        st.session_state.password = ''

    if not st.session_state.logged_in:
        logged_in = login()

        if logged_in:
            st.success('Logged in successfully!')  # 登录成功后显示绿色的消息条
    else:
        main_program()



if __name__ == '__main__':
    main()