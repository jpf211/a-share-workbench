
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="A股量化工作台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股量化工作台 V3")
st.write("A股历史行情 · K线 · 六均线 · 成交量 · 涨跌幅")


def convert_a_share_code(code):
    code = code.strip().upper()

    if code.endswith((".SS", ".SZ")):
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

            df = df.sort_index().reset_index()

            if len(df) < 2:
                st.warning("数据不足两个交易日，无法计算涨跌幅。")
                st.stop()

            st.success("行情读取成功！")

            # 最新收盘价和前一交易日收盘价
            latest_close = float(df["Close"].iloc[-1])
            previous_close = float(df["Close"].iloc[-2])

            change_amount = latest_close - previous_close

            change_pct = (
                change_amount / previous_close * 100
                if previous_close != 0 else 0
            )

            latest_date = pd.to_datetime(
                df["Date"].iloc[-1]
            ).strftime("%Y-%m-%d")

            # 顶部行情指标
            st.subheader("📊 最新交易日行情")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    label="最新收盘价（元）",
                    value=f"{latest_close:,.2f}",
                    delta=f"{change_amount:+.2f} 元",
                    delta_color="off"
                )

            with col2:
                st.metric(
                    label="当日涨跌幅",
                    value=f"{change_pct:+.2f}%",
                    delta=f"{change_amount:+.2f} 元",
                    delta_color="off"
                )

            st.caption(
                f"数据日期：{latest_date} | "
                "涨跌幅相对上一交易日收盘价计算，"
                "并非实时行情。"
            )

            # 六条自定义均线
            ma_periods = [6, 16, 26, 46, 62, 80]

            ma_colors = [
                "#38BDF8",
                "#FCA5A5",
                "#FF5252",
                "#4ADE80",
                "#2DD4BF",
                "#FACC15"
            ]

            for period in ma_periods:
                df[f"MA{period}"] = (
                    df["Close"].rolling(period).mean()
                )

            st.subheader(f"📈 {ticker_code} K线与成交量")

            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[0.75, 0.25]
            )

            # K线
            fig.add_trace(
                go.Candlestick(
                    x=df["Date"],
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="K Line",
                    increasing_line_color="#EF4444",
                    decreasing_line_color="#22C55E"
                ),
                row=1,
                col=1
            )

            # 六条均线
            for period, color in zip(ma_periods, ma_colors):
                fig.add_trace(
                    go.Scatter(
                        x=df["Date"],
                        y=df[f"MA{period}"],
                        mode="lines",
                        name=f"MA{period}",
                        line=dict(
                            color=color,
                            width=1.5
                        )
                    ),
                    row=1,
                    col=1
                )

            # 成交量柱状图
            volume_colors = [
                "#EF4444" if close >= open_price
                else "#22C55E"
                for close, open_price in zip(
                    df["Close"],
                    df["Open"]
                )
            ]

            fig.add_trace(
                go.Bar(
                    x=df["Date"],
                    y=df["Volume"],
                    name="Volume",
                    marker_color=volume_colors
                ),
                row=2,
                col=1
            )

            fig.update_layout(
                title=f"{ticker_code} Price & Volume",
                height=800,
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                xaxis2_rangeslider_visible=False,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    y=1.08,
                    x=0
                ),
                margin=dict(
                    l=40,
                    r=30,
                    t=100,
                    b=40
                )
            )

            fig.update_yaxes(
                title_text="Price",
                row=1,
                col=1
            )

            fig.update_yaxes(
                title_text="Volume",
                row=2,
                col=1
            )

            fig.update_xaxes(
                title_text="Date",
                row=2,
                col=1
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # 最近30个交易日数据
            st.subheader("最近30个交易日数据")

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
