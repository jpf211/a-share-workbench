import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="A股量化工作台 V6",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股量化工作台 V6")
st.write(
    "A股历史行情 · 六均线 · 金叉死叉 · 成交量 · MA6/MA16 策略回测"
)


# =========================================================
# 股票代码转换
# =========================================================
def convert_a_share_code(code):
    code = code.strip().upper()

    if code.endswith((".SS", ".SZ")):
        return code

    if code.startswith(("5", "6", "9")):
        return code + ".SS"

    if code.startswith(("0", "1", "2", "3")):
        return code + ".SZ"

    return code


# =========================================================
# CAGR
# =========================================================
def calculate_cagr(equity, dates):
    if len(equity) < 2:
        return 0.0

    start_value = float(equity.iloc[0])
    end_value = float(equity.iloc[-1])

    days = (
        pd.to_datetime(dates.iloc[-1])
        - pd.to_datetime(dates.iloc[0])
    ).days

    if start_value <= 0 or end_value <= 0 or days <= 0:
        return 0.0

    years = days / 365.25

    if years <= 0:
        return 0.0

    return (end_value / start_value) ** (1 / years) - 1


# =========================================================
# 最大回撤
# =========================================================
def calculate_max_drawdown(equity):
    running_max = equity.cummax()

    drawdown = (
        equity / running_max
        - 1
    )

    return float(drawdown.min())


# =========================================================
# MA6 / MA16 回测
# =========================================================
def run_backtest(
    df,
    years,
    commission_rate,
    stamp_duty_rate,
    slippage_rate
):
    bt = df.copy()

    # 最近 N 年作为正式回测区间
    start_date = (
        bt["Date"].max()
        - pd.DateOffset(years=years)
    )

    bt = bt[
        bt["Date"] >= start_date
    ].copy()

    if bt.empty:
        raise ValueError("回测区间没有可用数据。")

    # -----------------------------------------
    # 信号
    # MA6 > MA16 = 持仓信号
    # MA6 <= MA16 = 空仓信号
    # -----------------------------------------
    bt["Signal"] = (
        bt["MA6"] > bt["MA16"]
    ).astype(int)

    # 非常重要：
    # 今天收盘确认的信号，
    # 下一交易日开盘才执行。
    bt["TargetPosition"] = (
        bt["Signal"]
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    # 初始资金归一化为 1
    cash = 1.0
    shares = 0.0

    equity_curve = []
    position_curve = []

    trade_log = []

    entry_date = None
    entry_price = None
    entry_capital = None

    for _, row in bt.iterrows():

        current_date = row["Date"]

        open_price = float(row["Open"])
        close_price = float(row["Close"])

        target_position = int(
            row["TargetPosition"]
        )

        # =====================================
        # 买入
        # =====================================
        if target_position == 1 and shares == 0:

            # 模拟买入滑点
            execution_price = (
                open_price
                * (1 + slippage_rate)
            )

            entry_capital = cash

            # 买入时扣佣金
            shares = (
                cash
                * (1 - commission_rate)
                / execution_price
            )

            cash = 0.0

            entry_date = current_date
            entry_price = execution_price

        # =====================================
        # 卖出
        # =====================================
        elif target_position == 0 and shares > 0:

            # 模拟卖出滑点
            execution_price = (
                open_price
                * (1 - slippage_rate)
            )

            gross_cash = (
                shares
                * execution_price
            )

            # 卖出扣：
            # 佣金 + 印花税
            cash = (
                gross_cash
                * (
                    1
                    - commission_rate
                    - stamp_duty_rate
                )
            )

            trade_return = (
                cash / entry_capital
                - 1
            )

            holding_days = (
                pd.to_datetime(current_date)
                - pd.to_datetime(entry_date)
            ).days

            trade_log.append(
                {
                    "买入日期": entry_date,
                    "卖出日期": current_date,
                    "买入价": entry_price,
                    "卖出价": execution_price,
                    "持有天数": holding_days,
                    "单笔收益率": trade_return
                }
            )

            shares = 0.0
            entry_date = None
            entry_price = None
            entry_capital = None

        # =====================================
        # 每日收盘资产
        # =====================================
        equity = (
            cash
            + shares * close_price
        )

        equity_curve.append(equity)

        position_curve.append(
            1 if shares > 0 else 0
        )

    bt["StrategyEquity"] = equity_curve
    bt["Position"] = position_curve

    # =========================================
    # 买入并持有基准
    # =========================================
    first_open = float(
        bt["Open"].iloc[0]
    )

    benchmark_entry_price = (
        first_open
        * (1 + slippage_rate)
    )

    benchmark_shares = (
        (1 - commission_rate)
        / benchmark_entry_price
    )

    bt["BuyHoldEquity"] = (
        benchmark_shares
        * bt["Close"]
    )

    # =========================================
    # 回测指标
    # =========================================
    strategy_return = (
        float(
            bt["StrategyEquity"].iloc[-1]
        )
        - 1
    )

    benchmark_return = (
        float(
            bt["BuyHoldEquity"].iloc[-1]
        )
        - 1
    )

    cagr = calculate_cagr(
        bt["StrategyEquity"],
        bt["Date"]
    )

    max_drawdown = calculate_max_drawdown(
        bt["StrategyEquity"]
    )

    completed_trades = len(trade_log)

    if completed_trades > 0:
        winning_trades = sum(
            trade["单笔收益率"] > 0
            for trade in trade_log
        )

        win_rate = (
            winning_trades
            / completed_trades
        )

    else:
        win_rate = 0.0

    # 当前持仓
    current_position = (
        "持仓"
        if shares > 0
        else "空仓"
    )

    trade_df = pd.DataFrame(
        trade_log
    )

    return {
        "data": bt,
        "trade_log": trade_df,
        "strategy_return": strategy_return,
        "benchmark_return": benchmark_return,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "completed_trades": completed_trades,
        "win_rate": win_rate,
        "current_position": current_position
    }


# =========================================================
# 用户输入
# =========================================================
stock_code = st.text_input(
    "请输入股票代码",
    value="600519",
    placeholder="例如：600519"
)


# =========================================================
# 回测参数
# =========================================================
with st.sidebar:

    st.header("⚙️ 回测参数")

    backtest_years = st.selectbox(
        "回测时间",
        options=[1, 2, 3, 5],
        index=2,
        format_func=lambda x: f"{x} 年"
    )

    commission_bp = st.number_input(
        "佣金（单边，bp）",
        min_value=0.0,
        max_value=100.0,
        value=2.5,
        step=0.5,
        help=(
            "2.5 bp = 0.025%。"
            "不同券商账户可能不同。"
        )
    )

    stamp_duty_pct = st.number_input(
        "卖出印花税（%）",
        min_value=0.0,
        max_value=1.0,
        value=0.05,
        step=0.01
    )

    slippage_bp = st.number_input(
        "单边滑点（bp）",
        min_value=0.0,
        max_value=100.0,
        value=2.0,
        step=0.5
    )

    st.caption(
        "这些参数只是回测假设，"
        "应根据自己的账户和实际成交情况调整。"
    )


# 转换成小数
commission_rate = (
    commission_bp / 10000
)

stamp_duty_rate = (
    stamp_duty_pct / 100
)

slippage_rate = (
    slippage_bp / 10000
)


# =========================================================
# 主程序
# =========================================================
if st.button(
    "读取行情并运行回测",
    type="primary"
):

    ticker_code = convert_a_share_code(
        stock_code
    )

    st.write(
        "正在查询：",
        ticker_code
    )

    with st.spinner(
        "正在读取行情并运行策略回测..."
    ):

        try:

            # =============================================
            # 下载 5 年日线
            # =============================================
            stock = yf.Ticker(
                ticker_code
            )

            df = stock.history(
                period="5y",
                interval="1d",
                auto_adjust=True,
                repair=false
            )

            if df.empty:
                st.warning(
                    "没有获取到数据，请检查股票代码。"
                )
                st.stop()

            # 去除时区，方便回测日期比较
            if getattr(
                df.index,
                "tz",
                None
            ) is not None:
                df.index = (
                    df.index
                    .tz_localize(None)
                )

            df = (
                df
                .sort_index()
                .reset_index()
            )

            if len(df) < 100:
                st.warning(
                    "历史数据太少，无法进行完整均线回测。"
                )
                st.stop()

            # =============================================
            # 六条均线
            # =============================================
            ma_periods = [
                6,
                16,
                26,
                46,
                62,
                80
            ]

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
                    df["Close"]
                    .rolling(period)
                    .mean()
                )

            # =============================================
            # 最新行情
            # =============================================
            latest_close = float(
                df["Close"].iloc[-1]
            )

            previous_close = float(
                df["Close"].iloc[-2]
            )

            latest_volume = float(
                df["Volume"].iloc[-1]
            )

            change_amount = (
                latest_close
                - previous_close
            )

            change_pct = (
                change_amount
                / previous_close
                * 100
            )

            latest_date = (
                pd.to_datetime(
                    df["Date"].iloc[-1]
                )
                .strftime("%Y-%m-%d")
            )

            # =============================================
            # 当前六均线排列
            # =============================================
            latest = df.iloc[-1]

            ma_values = [
                latest[f"MA{x}"]
                for x in ma_periods
            ]

            if any(
                pd.isna(v)
                for v in ma_values
            ):
                trend = "数据不足"

            elif all(
                ma_values[i]
                > ma_values[i + 1]
                for i in range(
                    len(ma_values) - 1
                )
            ):
                trend = "多头排列"

            elif all(
                ma_values[i]
                < ma_values[i + 1]
                for i in range(
                    len(ma_values) - 1
                )
            ):
                trend = "空头排列"

            else:
                trend = "混合排列"

            # =============================================
            # 顶部指标
            # =============================================
            st.success(
                "行情读取成功！"
            )

            st.subheader(
                "📊 最新交易日行情"
            )

            col1, col2, col3, col4 = (
                st.columns(4)
            )

            col1.metric(
                "最新收盘价",
                f"{latest_close:,.2f} 元",
                f"{change_amount:+.2f} 元"
            )

            col2.metric(
                "当日涨跌幅",
                f"{change_pct:+.2f}%"
            )

            col3.metric(
                "成交量",
                f"{latest_volume / 10000:,.0f} 万股"
            )

            col4.metric(
                "六均线排列",
                trend
            )

            st.caption(
                f"数据日期：{latest_date}。"
                "历史日线数据，不是实时行情。"
            )

            # =============================================
            # MA6 / MA16 金叉死叉
            # =============================================
            ma6 = df["MA6"]
            ma16 = df["MA16"]

            golden_cross = (
                (
                    ma6.shift(1)
                    <= ma16.shift(1)
                )
                & (
                    ma6 > ma16
                )
            )

            death_cross = (
                (
                    ma6.shift(1)
                    >= ma16.shift(1)
                )
                & (
                    ma6 < ma16
                )
            )

            golden_df = df[
                golden_cross
            ]

            death_df = df[
                death_cross
            ]

            # =============================================
            # 最新交叉状态
            # =============================================
            st.subheader(
                "🔍 MA6 / MA16 最新信号"
            )

            if golden_cross.iloc[-1]:

                st.success(
                    "最新交易日出现 MA6 上穿 MA16（金叉）"
                )

            elif death_cross.iloc[-1]:

                st.warning(
                    "最新交易日出现 MA6 下穿 MA16（死叉）"
                )

            else:

                st.info(
                    "最新交易日没有发生 MA6 / MA16 交叉"
                )

            st.write(
                f"5年数据中金叉：{int(golden_cross.sum())} 次 | "
                f"死叉：{int(death_cross.sum())} 次"
            )

            # =============================================
            # K线图显示最近一年
            # =============================================
            chart_start = (
                df["Date"].max()
                - pd.DateOffset(years=1)
            )

            chart_df = df[
                df["Date"]
                >= chart_start
            ].copy()

            chart_golden = chart_df[
                (
                    chart_df["MA6"].shift(1)
                    <= chart_df["MA16"].shift(1)
                )
                & (
                    chart_df["MA6"]
                    > chart_df["MA16"]
                )
            ]

            chart_death = chart_df[
                (
                    chart_df["MA6"].shift(1)
                    >= chart_df["MA16"].shift(1)
                )
                & (
                    chart_df["MA6"]
                    < chart_df["MA16"]
                )
            ]

            st.subheader(
                f"📈 {ticker_code} K线与成交量"
            )

            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=[
                    0.75,
                    0.25
                ]
            )

            # K线
            fig.add_trace(
                go.Candlestick(
                    x=chart_df["Date"],
                    open=chart_df["Open"],
                    high=chart_df["High"],
                    low=chart_df["Low"],
                    close=chart_df["Close"],
                    name="K线",
                    increasing_line_color="#EF4444",
                    decreasing_line_color="#22C55E"
                ),
                row=1,
                col=1
            )

            # 六均线
            for period, color in zip(
                ma_periods,
                ma_colors
            ):

                fig.add_trace(
                    go.Scatter(
                        x=chart_df["Date"],
                        y=chart_df[
                            f"MA{period}"
                        ],
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

            # 金叉
            fig.add_trace(
                go.Scatter(
                    x=chart_golden["Date"],
                    y=(
                        chart_golden["Low"]
                        * 0.985
                    ),
                    mode="markers",
                    name="金叉",
                    marker=dict(
                        symbol="triangle-up",
                        size=13,
                        color="#EF4444"
                    ),
                    hovertemplate=(
                        "%{x}<br>"
                        "MA6/MA16 金叉"
                        "<extra></extra>"
                    )
                ),
                row=1,
                col=1
            )

            # 死叉
            fig.add_trace(
                go.Scatter(
                    x=chart_death["Date"],
                    y=(
                        chart_death["High"]
                        * 1.015
                    ),
                    mode="markers",
                    name="死叉",
                    marker=dict(
                        symbol="triangle-down",
                        size=13,
                        color="#22C55E"
                    ),
                    hovertemplate=(
                        "%{x}<br>"
                        "MA6/MA16 死叉"
                        "<extra></extra>"
                    )
                ),
                row=1,
                col=1
            )

            # 成交量颜色
            volume_colors = [
                (
                    "#EF4444"
                    if close >= open_price
                    else "#22C55E"
                )
                for close, open_price in zip(
                    chart_df["Close"],
                    chart_df["Open"]
                )
            ]

            fig.add_trace(
                go.Bar(
                    x=chart_df["Date"],
                    y=chart_df["Volume"],
                    name="成交量",
                    marker_color=volume_colors
                ),
                row=2,
                col=1
            )

            fig.update_layout(
                title=(
                    f"{ticker_code} "
                    "价格、均线与成交量"
                ),
                height=820,
                template="plotly_dark",
                hovermode="x unified",
                xaxis_rangeslider_visible=False,
                xaxis2_rangeslider_visible=False,
                legend=dict(
                    orientation="h",
                    y=1.08,
                    x=0
                )
            )

            fig.update_yaxes(
                title_text="价格",
                row=1,
                col=1
            )

            fig.update_yaxes(
                title_text="成交量",
                row=2,
                col=1
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # =============================================
            # V6 回测
            # =============================================
            st.subheader(
                "🧪 MA6 / MA16 策略回测"
            )

            st.caption(
                "规则：当天收盘确认 MA6/MA16 状态，"
                "下一交易日开盘执行。"
                "MA6 > MA16 持仓，否则空仓。"
            )

            result = run_backtest(
                df=df,
                years=backtest_years,
                commission_rate=commission_rate,
                stamp_duty_rate=stamp_duty_rate,
                slippage_rate=slippage_rate
            )

            bt = result["data"]

            # =============================================
            # 回测指标
            # =============================================
            r1, r2, r3 = st.columns(3)

            r1.metric(
                "策略累计收益",
                f"{result['strategy_return'] * 100:+.2f}%"
            )

            r2.metric(
                "买入并持有",
                f"{result['benchmark_return'] * 100:+.2f}%"
            )

            r3.metric(
                "策略当前状态",
                result["current_position"]
            )

            r4, r5, r6 = st.columns(3)

            r4.metric(
                "策略年化收益",
                f"{result['cagr'] * 100:+.2f}%"
            )

            r5.metric(
                "最大回撤",
                f"{result['max_drawdown'] * 100:.2f}%"
            )

            r6.metric(
                "完成交易次数",
                result["completed_trades"]
            )

            r7, r8 = st.columns(2)

            r7.metric(
                "历史胜率",
                f"{result['win_rate'] * 100:.1f}%"
            )

            excess_return = (
                result["strategy_return"]
                - result["benchmark_return"]
            )

            r8.metric(
                "相对买入持有",
                f"{excess_return * 100:+.2f}%"
            )

            # =============================================
            # 资金曲线
            # =============================================
            st.subheader(
                "💰 策略资金曲线"
            )

            equity_fig = go.Figure()

            equity_fig.add_trace(
                go.Scatter(
                    x=bt["Date"],
                    y=(
                        bt["StrategyEquity"]
                        * 100
                    ),
                    mode="lines",
                    name="MA6/MA16 策略"
                )
            )

            equity_fig.add_trace(
                go.Scatter(
                    x=bt["Date"],
                    y=(
                        bt["BuyHoldEquity"]
                        * 100
                    ),
                    mode="lines",
                    name="买入并持有"
                )
            )

            equity_fig.update_layout(
                title=(
                    "初始资金 = 100 "
                    "的历史资金曲线"
                ),
                xaxis_title="日期",
                yaxis_title="资金净值",
                height=520,
                template="plotly_dark",
                hovermode="x unified"
            )

            st.plotly_chart(
                equity_fig,
                use_container_width=True
            )

            # =============================================
            # 每笔交易记录
            # =============================================
            st.subheader(
                "📋 历史交易记录"
            )

            trade_df = result[
                "trade_log"
            ].copy()

            if trade_df.empty:

                st.info(
                    "该回测区间没有完成的交易。"
                )

            else:

                trade_df[
                    "买入日期"
                ] = pd.to_datetime(
                    trade_df["买入日期"]
                ).dt.strftime(
                    "%Y-%m-%d"
                )

                trade_df[
                    "卖出日期"
                ] = pd.to_datetime(
                    trade_df["卖出日期"]
                ).dt.strftime(
                    "%Y-%m-%d"
                )

                trade_df[
                    "买入价"
                ] = trade_df[
                    "买入价"
                ].round(2)

                trade_df[
                    "卖出价"
                ] = trade_df[
                    "卖出价"
                ].round(2)

                trade_df[
                    "单笔收益率"
                ] = (
                    trade_df[
                        "单笔收益率"
                    ]
                    * 100
                ).round(2)

                trade_df = (
                    trade_df.rename(
                        columns={
                            "单笔收益率":
                            "单笔收益率（%）"
                        }
                    )
                )

                st.dataframe(
                    trade_df,
                    use_container_width=True,
                    hide_index=True
                )

            # =============================================
            # 最近30个交易日
            # =============================================
            st.subheader(
                "最近30个交易日数据"
            )

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
                df[
                    show_columns
                ].tail(30),
                use_container_width=True,
                hide_index=True
            )

            # =============================================
            # 风险说明
            # =============================================
            st.info(
                "回测仅用于研究历史规则。"
                "它不代表未来收益。"
                "程序未完整模拟涨跌停无法成交、"
                "停牌、盘口流动性、最低佣金、"
                "大额订单冲击等真实交易因素。"
            )

        except Exception as e:

            st.error(
                f"运行失败：{e}"
            )
