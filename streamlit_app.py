import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(
    page_title="A股量化工作台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股量化工作台")
st.write("输入股票代码，读取真实 A 股历史行情。")

stock_code = st.text_input(
    "请输入股票代码",
    value="600519",
    placeholder="例如：600519"
)

if st.button("读取行情"):

    with st.spinner("正在读取行情数据..."):

        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date="20250101",
                end_date="20261231",
                adjust="qfq"
            )

            if df.empty:
                st.warning("没有获取到数据，请检查股票代码。")
            else:
                st.success("行情读取成功！")

                st.subheader(f"股票代码：{stock_code}")

                st.dataframe(
                    df.tail(30),
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"读取失败：{e}")
