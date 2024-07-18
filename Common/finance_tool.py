import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime

# 初始化session_state中的记录，包含表头
if 'records' not in st.session_state:
    # 初始化包含表头的records
    st.session_state.records = [{"具体行为": "具体行为", "金额": "金额", "类别": "类别", "日期": "日期"}]
#st.session_state是一个特定于每个独立运行的Streamlit应用的临时存储空间

#添加收入的函数
# 定义一个函数来展示并编辑收入表格
def show_edit_income_table():
    # 将当前records转换为DataFrame以便于编辑
    # 从第二个元素开始视为数据行，排除表头
    if len(st.session_state.records) > 1:
        df_income = pd.DataFrame(st.session_state.records[1:])
    else:
        df_income = pd.DataFrame()

    # 使用st.data_editor创建一个可编辑的表格
    #num_rows="dynamic" 的作用是设置可以根据内容动态调整行
    edited_df_income = st.data_editor(df_income, num_rows="dynamic",
                                       use_container_width=True,
                                       key="income_table")

    # 处理st.data_editor的返回值以适应新的st.session_state格式
    if edited_df_income is not df_income:  # 检查是否发生了更改
        # 由于st.data_editor直接作用于DataFrame，我们不需要特别处理格式变更
        # 直接更新st.session_state.records，保留表头
        #to_dict('records')将DataFrame转换为一个字典列表，Pandas DataFrame提供的一种转换方式
        st.session_state.records = st.session_state.records[:1] + edited_df_income.to_dict('records')

    # 添加收入表单
    st.subheader("添加新收入记录")
    new_income_amount = st.number_input("金额", min_value=0.0, step=1.0)
    new_income_category = st.selectbox("类别", ["工资", "奖金", "投资收入", "其他"])
    new_income_date = st.date_input("日期")
    if st.button("添加新收入"):
        # 直接添加到 st.session_state.records
        st.session_state.records.append(
            {"具体行为": "收入", "金额": new_income_amount, "类别": new_income_category, "日期": new_income_date})
        st.success("新收入记录已成功添加！")

    # 确保表头和新添加的数据一起展示
    records_to_display = [{"具体行为": "具体行为", "金额": "金额", "类别": "类别",
                           "日期": "日期"}] + st.session_state.records
    edited_df_income = st.data_editor(records_to_display[1:], num_rows="dynamic",
                                      use_container_width=True,
                                      key="income_table_3")



#添加支出的函数
def add_expense():
    date = st.date_input("支出日期")
    amount = st.number_input("金额", min_value=0.0, step=-1.0)
    category = st.selectbox("类别", ["食品", "交通", "房租", "娱乐", "其他"])
    note = st.text_input("备注")
    if st.button("添加支出"):
        st.session_state.records.append({"类型": "支出", "日期": date, "金额": amount, "类别": category, "备注": note})
        st.success("支出记录已添加！")


#数据汇总
def categorize_by_month(df):
    """按月份分类汇总收入与支出"""
    # 尝试转换'日期'列，同时指定可能出现的日期格式
    try:
        df['日期'] = pd.to_datetime(df['日期'], errors='raise')  # errors='raise'会让转换过程抛出错误
    except ValueError as e:
    #df 是一个Pandas DataFrame的对象
        st.error(f"日期转换错误: {e}. 请确保所有日期格式正确。")
        return None  # 或者根据需要处理错误，比如返回None或空DataFrame

    df['Month'] = df['日期'].dt.to_period('M')
    monthly_summary = df.groupby(['Month', '类型'])['金额'].sum().unstack().fillna(0)
    monthly_summary['总支出'] = monthly_summary['支出'].sum()
    monthly_summary['总收入'] = monthly_summary['收入'].sum()
    return monthly_summary


#数据可视化
# 数据可视化
def visualize_data(data):
    # 筛选出支出记录
    expenses = data[data['类型'] == '支出']

    # 计算各类别的支出总额
    category_totals = expenses.groupby('类别')['金额'].sum()

    # 计算总支出
    total_expenses = category_totals.sum()

    # 计算每个类别的支出比例
    category_percentages = category_totals / total_expenses

    # 生成各类别的支出比例柱状图
    fig1, ax1 = plt.subplots()
    category_percentages.plot(kind='bar', title='各类别的支出比例', ax=ax1)
    ax1.set_xlabel('类别')
    ax1.set_ylabel('支出比例')
    st.pyplot(fig1)  # 使用st.pyplot显示图表

    # 生成总支出的类别占比饼图
    fig2, ax2 = plt.subplots()
    category_percentages.plot(kind='pie', autopct='%1.1f%%', startangle=140, ax=ax2, figsize=(6, 6))
    ax2.set_title('总支出的类别占比')
    st.pyplot(fig2)  # 使用st.pyplot显示图表

#导出文件
def export_data():
    data = pd.DataFrame(st.session_state.records)
    if data.empty:
        st.warning("没有数据可以导出。")
    else:
        csv = data.to_csv(index=False)
        st.download_button(
            label="下载数据为CSV",
            data=csv,
            file_name="finance_records.csv",
            mime="text/csv",
        )


#进行数据过滤和查询
def filter_and_query_records(data):
    # 过滤条件设置
    st.sidebar.header("筛选条件")
    start_date = st.sidebar.date_input("起始日期", data['日期'].min())
    end_date = st.sidebar.date_input("结束日期", data['日期'].max())
    category_filter = st.sidebar.multiselect("类别", data["类别"].unique(), default=data["类别"].unique())

    # 应用筛选条件
    filtered_data = data[
        (data['日期'] >= start_date) &
        (data['日期'] <= end_date) &
        (data['类别'].isin(category_filter))
        ]

    if not filtered_data.empty:
        # 显示筛选后的数据
        st.dataframe(filtered_data)
    else:
        st.info("根据所选条件，没有找到相关记录。")



def main():
    css = """
    h1 {
        color: #FFA500;
        font-size: 32px;
        text-align: center;
    }
    .sidebar-button {
        width: 100%;
        text-align: left;
        margin-bottom: 10px;
        padding: 5px 0;
        display: block;
    }
    .sidebar-button:hover {
        background-color: #f6f6f6;
    }
    """

    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    st.markdown("<h1>个人理财管理工具</h1>", unsafe_allow_html=True)

    # 初始化当前显示的页面
    current_page = ""

    # 侧边栏菜单，使用无样式按钮
    if st.sidebar.button("收入记录", key="income_button"):
        current_page = "收入记录"
        st.title("个人记账系统 - 收入记录")  # 在选择收入记录时显示此标题
    if st.sidebar.button("支出记录", key="expense_button"):
        current_page = "支出记录"
        st.title("个人记账系统 - 支出记录")  # 在选择支出记录时显示此标题
    if st.sidebar.button("数据可视化", key="visualization_button"):
        current_page = "数据可视化"
    if st.sidebar.button("数据导出", key="export_button"):
        current_page = "数据导出"
    if st.sidebar.button("数据过滤和查询", key="filter_button"):
        current_page = "数据过滤和查询"


    # 显示对应的页面内容
    if current_page == "收入记录":
        # 显示并允许编辑收入表格
        show_edit_income_table()

    elif current_page == "支出记录":
        st.subheader("添加支出记录")
        add_expense()
    elif current_page == "数据可视化":
        st.subheader("数据可视化")
        visualize_data(pd.DataFrame(st.session_state.records))
    elif current_page == "数据导出":
        st.subheader("数据导出")
        export_data()
    elif current_page == "数据过滤和查询":
        st.subheader("数据过滤和查询")
        data = pd.DataFrame(st.session_state.records)
        filter_and_query_records(data)

    # 如果没有选择，则显示默认页面或提示信息
    if not current_page:
        st.info("请选择一个菜单项开始操作")


if __name__ == "__main__":
    main()