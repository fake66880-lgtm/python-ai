from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import List

import baostock as bs
import pandas as pd


def _to_a_share_codes(stock_df: pd.DataFrame) -> List[str]:
    stock_df = stock_df.copy()
    stock_df = stock_df[stock_df["code"].str.startswith(("sh.", "sz."))]
    return stock_df["code"].dropna().unique().tolist()


def _fetch_one(code: str, start_date: str, end_date: str, adjustflag: str) -> pd.DataFrame:
    rs = bs.query_history_k_data_plus(
        code,
        "date,code,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag=adjustflag,
    )
    rows = []
    while (rs.error_code == "0") and rs.next():
        rows.append(rs.get_row_data())
    if not rows:
        return pd.DataFrame(columns=["date", "code", "open", "high", "low", "close", "volume", "amount"])
    out = pd.DataFrame(rows, columns=rs.fields)
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def build_dataset(start_date: str, end_date: str, adjustflag: str, limit: int | None = None) -> pd.DataFrame:
    login_res = bs.login()
    if login_res.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {login_res.error_msg}")

    try:
        rs = bs.query_all_stock(day=end_date)
        all_rows = []
        while (rs.error_code == "0") and rs.next():
            all_rows.append(rs.get_row_data())
        all_stocks = pd.DataFrame(all_rows, columns=rs.fields)

        codes = _to_a_share_codes(all_stocks)
        if limit is not None:
            codes = codes[:limit]

        frames = []
        for idx, code in enumerate(codes, start=1):
            frame = _fetch_one(code=code, start_date=start_date, end_date=end_date, adjustflag=adjustflag)
            if not frame.empty:
                frames.append(frame)
            if idx % 200 == 0:
                print(f"已抓取 {idx}/{len(codes)} 支股票")

        if not frames:
            return pd.DataFrame(columns=["date", "code", "open", "high", "low", "close", "volume", "amount"])

        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values(["code", "date"]).reset_index(drop=True)
        return df
    finally:
        bs.logout()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="下载并构建A股近20年日线CSV数据库")
    parser.add_argument("--output", default="data/ashare_20y_daily.csv", help="输出CSV路径")
    parser.add_argument("--start-date", default=None, help="开始日期，格式 YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="结束日期，格式 YYYY-MM-DD")
    parser.add_argument("--adjustflag", default="2", choices=["1", "2", "3"], help="复权类型: 1后复权, 2前复权, 3不复权")
    parser.add_argument("--limit", type=int, default=None, help="仅下载前N只股票，便于测试")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    end_date = args.end_date or dt.date.today().strftime("%Y-%m-%d")
    start_date = args.start_date or (dt.date.today() - dt.timedelta(days=365 * 20)).strftime("%Y-%m-%d")

    df = build_dataset(start_date=start_date, end_date=end_date, adjustflag=args.adjustflag, limit=args.limit)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"完成: {output_path}")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"记录数: {len(df)}")
    print("字段: date, code, open, high, low, close, volume, amount")


if __name__ == "__main__":
    main()
