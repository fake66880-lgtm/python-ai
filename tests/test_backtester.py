import pandas as pd

from backtester import backtest_long_only, load_ohlcv_from_csv, ma_cross_signals, run_strategy


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=12, freq="D")
    close = [10, 10.2, 10.4, 10.3, 10.1, 10.5, 10.8, 11.0, 10.9, 11.2, 11.3, 11.1]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [c + 0.1 for c in close],
            "low": [c - 0.1 for c in close],
            "close": close,
        },
        index=idx,
    )
    return df


def test_ma_cross_signal_has_same_length():
    df = _sample_df()
    entry, exit_ = ma_cross_signals(df, fast=2, slow=4)
    assert len(entry) == len(df)
    assert len(exit_) == len(df)


def test_backtest_runs_and_returns_metrics():
    df = _sample_df()
    entry = pd.Series([False, True] + [False] * 10, index=df.index)
    exit_ = pd.Series([False] * 7 + [True] + [False] * 4, index=df.index)

    result = backtest_long_only(df, entry, exit_, fee_rate=0.0)
    assert len(result.trades) == 1
    assert 0 <= result.win_rate <= 1
    assert isinstance(result.total_return, float)


def test_run_strategy_ma_cross():
    df = _sample_df()
    result = run_strategy(df, "ma_cross")
    assert result.equity_curve.index.equals(df.index)


def test_load_multi_code_csv_with_filter(tmp_path):
    csv_path = tmp_path / "market.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-01"],
            "code": ["sh.600000", "sh.600000", "sz.000001"],
            "open": [10, 11, 20],
            "high": [11, 12, 21],
            "low": [9, 10, 19],
            "close": [10.5, 11.5, 20.5],
        }
    ).to_csv(csv_path, index=False)

    df = load_ohlcv_from_csv(str(csv_path), code="sh.600000")
    assert len(df) == 2
