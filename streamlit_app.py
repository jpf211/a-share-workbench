import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="A股量化工作台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股量化工作台")
st.write("输入股票代码，读取真实 A 股历史行情，并显示 K 线与多周期均线。")


def convert_a_share_code(code):
    code = code.strip().upper()

    if code.endswith(".SS") or code.endswith(".SZ"):
        return code

    if code.startswith(("5", "6", "9")):
        return code + ".SS"

    if code.startswith(("0", "1", "2", "3")):
        return code + ".SZ"

    return code


stock_code = st.text_input(
    "请输入股票代码",
    value="600519",
    placeholder="例如：600519"
)

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
                st.stop()

            st.success("行情读取成功！")

            df = df.reset_index()

            # 计算均线
            df["MA6"] = df["Close"].rolling(6).mean()
            df["MA16"] = df["Close"].rolling(16).mean()
            df["MA26"] = df["Close"].rolling(26).mean()
            df["MA46"] = df["Close"].rolling(46).mean()
            df["MA62"] = df["Close"].rolling(62).mean()
            df["MA80"] = df["Close"].rolling(80).mean()

            st.subheader(f"📊 {ticker_code} K线图")

            fig = go.Figure()

            # K线
            fig.add_trace(
                go.Candlestick(
                    x=df["Date"],
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="K Line"
                )
            )

            # MA6
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA6"],
                    mode="lines",
                    name="MA6"
                )
            )

            # MA16
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA16"],
                    mode="lines",
                    name="MA16"
                )
            )

            # MA26
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA26"],
                    mode="lines",
                    name="MA26"
                )
            )

            # MA46
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA46"],
                    mode="lines",
                    name="MA46"
                )
            )

            # MA62
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA62"],
                    mode="lines",
                    name="MA62"
                )
            )

            # MA80
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["MA80"],
                    mode="lines",
                    name="MA80"
                )
            )

            fig.update_layout(
                title=f"{ticker_code} Price Chart",
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                height=650
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader("最近 30 个交易日数据")

            show_columns = [
                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "MA6",
                "MA16",
                "MA26",
                "MA46",
                "MA62",
                "MA80"
            ]

            st.dataframe(
                df[show_columns].tail(30),
                use_container_width=True
            )

        except Exception as e:
            st.error(f"读取失败：{e}")
