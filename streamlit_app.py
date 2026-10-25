import streamlit as st
import yfinance as yf
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

def convert_a_share_code(code):
    code = code.strip().upper()

    # 如果已经输入了 .SS 或 .SZ，就直接使用
    if code.endswith(".SS") or code.endswith(".SZ"):
        return code

    # 沪市常见代码
    if code.startswith(("5", "6", "9")):
        return code + ".SS"

    # 深市常见代码
    if code.startswith(("0", "1", "2", "3")):
        return code + ".SZ"

    return code

if st.button("读取行情"):

    ticker_code = convert_a_share_code(stock_code)

    st.write("正在查询：", ticker_code)

    with st.spinner("正在读取行情数据..."):

        try:
            stock = yf.Ticker(ticker_code)

            df = stock.history(
                period="1y",
                interval="1d",
                auto_adjust=False
            )

            if df.empty:
                st.warning("没有获取到数据，请检查股票代码。")

            else:
                st.success("行情读取成功！")

                st.subheader(f"股票代码：{ticker_code}")

                df = df.reset_index()

                st.dataframe(
                    df.tail(30),
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"读取失败：{e}")
