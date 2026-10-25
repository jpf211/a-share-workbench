import streamlit as st

st.set_page_config(
    page_title="A股量化工作台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股量化工作台")

st.write("输入股票代码，开始研究 A 股。")

stock_code = st.text_input(
    "请输入股票代码",
    value="600519",
    placeholder="例如：600519"
)

st.write("你输入的股票代码是：", stock_code)
