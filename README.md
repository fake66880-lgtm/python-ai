# python-ai

一个轻量的 A 股历史回测工具（本地 CSV 版），用于快速验证技术策略在历史数据中的表现（尤其是胜率）。

## 功能

- 支持读取本地 OHLCV CSV 数据。
- 支持下载并生成全 A 股近 20 年日线数据库（Baostock）。
- 内置两种示例策略：
  - `ma_cross`：均线金叉/死叉
  - `breakout`：N 日突破
- 输出核心指标：
  - 交易次数
  - 胜率
  - 平均单笔收益
  - 总收益
  - 最大回撤

## 安装

```bash
pip install -r requirements.txt
```

## 先生成全A股近20年CSV数据库

```bash
python scripts/build_ashare_20y_csv.py --output data/ashare_20y_daily.csv
```

说明：
- 默认抓取从“今天往前 20 年”到今天的数据。
- 输出字段：`date, code, open, high, low, close, volume, amount`。
- 若仅想试跑可加 `--limit 100`。

例如（先小规模测试）：

```bash
python scripts/build_ashare_20y_csv.py --output data/ashare_20y_daily.csv --limit 100
```

## 数据格式

回测最低要求列：

- `date`（日期）
- `open`
- `high`
- `low`
- `close`

如果是全市场数据库，建议额外保留：

- `code`
- `volume`
- `amount`

## 使用方式

### 多股票数据库里回测某只股票

```bash
python backtester.py --csv data/ashare_20y_daily.csv --code sh.600000 --strategy ma_cross
```

### 单股票CSV（不含code列）

```bash
python backtester.py --csv your_stock_data.csv --strategy breakout
```

## 测试

```bash
pytest -q
```

## 下一步建议

1. 增加资金管理（仓位控制、止盈止损、滑点模型）。
2. 做组合级回测（多股票、多因子）。
3. 增加 walk-forward 与样本外检验，避免过拟合。
4. 叠加基准对比（沪深300/中证500）与超额收益统计。
