from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float

    @property
    def ret(self) -> float:
        return self.exit_price / self.entry_price - 1


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: pd.Series

    @property
    def total_return(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        return float(self.equity_curve.iloc[-1] - 1)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.ret > 0)
        return wins / len(self.trades)

    @property
    def avg_trade_return(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.ret for t in self.trades) / len(self.trades)

    @property
    def max_drawdown(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        peak = self.equity_curve.cummax()
        drawdown = self.equity_curve / peak - 1
        return float(drawdown.min())


def load_ohlcv_from_csv(path: str, code: Optional[str] = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV 缺少必需列: {sorted(missing)}")

    if "code" in df.columns:
        if code is None:
            first_code = str(df["code"].iloc[0])
            df = df[df["code"] == first_code].copy()
        else:
            df = df[df["code"] == code].copy()
        if df.empty:
            raise ValueError(f"CSV 中找不到股票代码: {code}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    return df


def ma_cross_signals(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> Tuple[pd.Series, pd.Series]:
    fast_ma = df["close"].rolling(fast).mean()
    slow_ma = df["close"].rolling(slow).mean()

    long_signal = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
    exit_signal = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
    return long_signal.fillna(False), exit_signal.fillna(False)


def breakout_signals(df: pd.DataFrame, n: int = 20) -> Tuple[pd.Series, pd.Series]:
    prev_high = df["high"].shift(1).rolling(n).max()
    prev_low = df["low"].shift(1).rolling(n).min()

    long_signal = df["close"] > prev_high
    exit_signal = df["close"] < prev_low
    return long_signal.fillna(False), exit_signal.fillna(False)


def backtest_long_only(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    fee_rate: float = 0.0005,
) -> BacktestResult:
    if not (len(df) == len(entry_signal) == len(exit_signal)):
        raise ValueError("数据与信号长度不一致")

    in_position = False
    entry_price: Optional[float] = None
    entry_date: Optional[pd.Timestamp] = None
    equity = 1.0
    equity_curve = []
    trades: List[Trade] = []

    for dt, row in df.iterrows():
        price = float(row["close"])

        if (not in_position) and bool(entry_signal.loc[dt]):
            in_position = True
            entry_price = price * (1 + fee_rate)
            entry_date = dt

        elif in_position and bool(exit_signal.loc[dt]):
            assert entry_price is not None and entry_date is not None
            exit_price = price * (1 - fee_rate)
            trade = Trade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=dt,
                exit_price=exit_price,
            )
            trades.append(trade)
            equity *= (1 + trade.ret)
            in_position = False
            entry_price, entry_date = None, None

        equity_curve.append((dt, equity))

    if in_position and entry_price is not None and entry_date is not None:
        final_price = float(df["close"].iloc[-1]) * (1 - fee_rate)
        trade = Trade(
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=df.index[-1],
            exit_price=final_price,
        )
        trades.append(trade)
        equity *= (1 + trade.ret)
        equity_curve[-1] = (df.index[-1], equity)

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series({k: v for k, v in equity_curve}).sort_index(),
    )


def run_strategy(df: pd.DataFrame, strategy: str) -> BacktestResult:
    if strategy == "ma_cross":
        entry, exit_ = ma_cross_signals(df)
    elif strategy == "breakout":
        entry, exit_ = breakout_signals(df)
    else:
        raise ValueError(f"未知策略: {strategy}")
    return backtest_long_only(df, entry, exit_)


def print_report(result: BacktestResult) -> None:
    print("=== 回测报告 ===")
    print(f"交易次数: {len(result.trades)}")
    print(f"胜率: {result.win_rate:.2%}")
    print(f"平均单笔收益: {result.avg_trade_return:.2%}")
    print(f"总收益: {result.total_return:.2%}")
    print(f"最大回撤: {result.max_drawdown:.2%}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A股历史回测工具（CSV输入）")
    parser.add_argument("--csv", required=True, help="历史数据CSV路径")
    parser.add_argument("--code", default=None, help="若CSV含多股票，请指定股票代码，例如 sh.600000")
    parser.add_argument(
        "--strategy",
        default="ma_cross",
        choices=["ma_cross", "breakout"],
        help="策略名称",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_ohlcv_from_csv(args.csv, code=args.code)
    result = run_strategy(df, args.strategy)
    print_report(result)


if __name__ == "__main__":
    main()
