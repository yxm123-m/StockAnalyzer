"""
SQLite 数据库层 — 建表、CRUD、缓存管理
"""
import sqlite3
import os
from datetime import datetime

from config import DB_PATH


def get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """建表"""
    conn = get_conn()
    cur = conn.cursor()

    # 股票列表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_list (
        code        TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        market      TEXT,
        industry    TEXT,
        listed_date TEXT,
        is_st       INTEGER DEFAULT 0,
        updated_at  TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # 日K线
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_kline (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT NOT NULL,
        trade_date  TEXT NOT NULL,
        open        REAL, high REAL, low REAL, close REAL,
        volume      REAL, amount REAL,
        pre_close   REAL, change_pct REAL,
        UNIQUE(code, trade_date)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kline_code ON daily_kline(code, trade_date)")

    # 集合竞价汇总
    cur.execute("""
    CREATE TABLE IF NOT EXISTS call_auction (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT NOT NULL,
        trade_date      TEXT NOT NULL,
        auction_volume  REAL,
        auction_amount  REAL,
        open_price      REAL,
        pre_close       REAL,
        open_gap_pct    REAL,
        bid_vol         REAL,
        ask_vol         REAL,
        imbalance_ratio REAL,
        auction_high    REAL,
        auction_low     REAL,
        price_trend_slope REAL,
        vol_ma5         REAL,
        vol_ma10        REAL,
        vol_ma20        REAL,
        vol_ratio_vs_ma20 REAL,
        total_score     REAL,
        UNIQUE(code, trade_date)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ca_date ON call_auction(trade_date)")

    # 策略信号
    cur.execute("""
    CREATE TABLE IF NOT EXISTS strategy_signals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT NOT NULL,
        name            TEXT,
        trade_date      TEXT NOT NULL,
        volume_score    REAL, trend_score REAL,
        imbalance_score REAL, gap_score REAL,
        total_score     REAL,
        grade           TEXT,
        rank            INTEGER,
        open_gap_pct    REAL,
        auction_volume  REAL,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(code, trade_date)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sig_date ON strategy_signals(trade_date, rank)")

    # 回测运行记录
    cur.execute("""
    CREATE TABLE IF NOT EXISTS backtest_runs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        run_name        TEXT,
        start_date      TEXT, end_date TEXT,
        initial_cash    REAL DEFAULT 100000,
        strategy_params TEXT,
        final_value     REAL,
        total_return    REAL, annual_return REAL,
        sharpe_ratio    REAL, max_drawdown REAL,
        win_rate        REAL, total_trades INTEGER,
        created_at      TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # 模拟账户
    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_account (
        id          INTEGER PRIMARY KEY CHECK (id = 1),
        cash        REAL DEFAULT 1000000,
        initial_cash REAL DEFAULT 1000000,
        commission  REAL DEFAULT 0,
        stamp_tax   REAL DEFAULT 0,
        updated_at  TEXT DEFAULT (datetime('now','localtime'))
    )""")
    # 确保有默认行
    cur.execute("INSERT OR IGNORE INTO paper_account(id) VALUES(1)")

    # 模拟持仓
    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_positions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        code          TEXT NOT NULL UNIQUE,
        name          TEXT,
        shares        INTEGER NOT NULL,
        avg_cost      REAL,
        current_price REAL,
        market_value  REAL,
        unrealized_pnl REAL,
        updated_at    TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # 模拟订单
    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        code          TEXT NOT NULL,
        name          TEXT,
        direction     TEXT NOT NULL,
        price         REAL,
        shares        INTEGER NOT NULL,
        filled_shares INTEGER DEFAULT 0,
        status        TEXT DEFAULT 'FILLED',
        commission    REAL DEFAULT 0,
        stamp_tax     REAL DEFAULT 0,
        reason        TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime'))
    )""")

    conn.commit()
    conn.close()


# ===================== 股票列表 =====================

def save_stock_list(stocks):
    """stocks: list of (code, name, market)"""
    conn = get_conn()
    conn.executemany(
        "INSERT OR REPLACE INTO stock_list(code, name, market, updated_at) VALUES(?,?,?,datetime('now','localtime'))",
        stocks
    )
    conn.commit()
    conn.close()


def get_all_stocks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM stock_list ORDER BY code").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock_count():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM stock_list").fetchone()[0]
    conn.close()
    return count


# ===================== 日K线 =====================

def save_daily_kline(rows):
    """rows: list of (code, date, open, high, low, close, volume, amount, pre_close, change_pct)"""
    conn = get_conn()
    conn.executemany(
        """INSERT OR REPLACE INTO daily_kline(code, trade_date, open, high, low, close, volume, amount, pre_close, change_pct)
           VALUES(?,?,?,?,?,?,?,?,?,?)""", rows
    )
    conn.commit()
    conn.close()


def get_daily_kline(code, start_date=None, end_date=None):
    conn = get_conn()
    sql = "SELECT * FROM daily_kline WHERE code=?"
    params = [code]
    if start_date:
        sql += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND trade_date <= ?"
        params.append(end_date)
    sql += " ORDER BY trade_date"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===================== 集合竞价 =====================

def save_call_auction(rows):
    """rows: list of dicts"""
    conn = get_conn()
    for r in rows:
        conn.execute("""
            INSERT OR REPLACE INTO call_auction
            (code, trade_date, auction_volume, auction_amount, open_price, pre_close,
             open_gap_pct, bid_vol, ask_vol, imbalance_ratio, auction_high, auction_low,
             price_trend_slope, vol_ma5, vol_ma10, vol_ma20, vol_ratio_vs_ma20, total_score)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r.get('code'), r.get('trade_date'), r.get('auction_volume'), r.get('auction_amount'),
            r.get('open_price'), r.get('pre_close'), r.get('open_gap_pct'),
            r.get('bid_vol'), r.get('ask_vol'), r.get('imbalance_ratio'),
            r.get('auction_high'), r.get('auction_low'), r.get('price_trend_slope'),
            r.get('vol_ma5'), r.get('vol_ma10'), r.get('vol_ma20'),
            r.get('vol_ratio_vs_ma20'), r.get('total_score'),
        ))
    conn.commit()
    conn.close()


def get_call_auction(code=None, trade_date=None):
    conn = get_conn()
    sql = "SELECT * FROM call_auction WHERE 1=1"
    params = []
    if code:
        sql += " AND code=?"
        params.append(code)
    if trade_date:
        sql += " AND trade_date=?"
        params.append(trade_date)
    sql += " ORDER BY total_score DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===================== 策略信号 =====================

def save_strategy_signals(signals):
    """signals: list of dicts"""
    conn = get_conn()
    for s in signals:
        conn.execute("""
            INSERT OR REPLACE INTO strategy_signals
            (code, name, trade_date, volume_score, trend_score, imbalance_score, gap_score,
             total_score, grade, rank, open_gap_pct, auction_volume)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            s['code'], s['name'], s['trade_date'],
            s['volume_score'], s['trend_score'], s['imbalance_score'], s['gap_score'],
            s['total_score'], s['grade'], s['rank'],
            s.get('open_gap_pct', 0), s.get('auction_volume', 0),
        ))
    conn.commit()
    conn.close()


def get_strategy_signals(trade_date=None, min_score=0, limit=50):
    conn = get_conn()
    sql = "SELECT * FROM strategy_signals WHERE total_score >= ?"
    params = [min_score]
    if trade_date:
        sql += " AND trade_date=?"
        params.append(trade_date)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ===================== 模拟交易 =====================

def get_paper_account():
    conn = get_conn()
    row = conn.execute("SELECT * FROM paper_account WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else None


def update_paper_account(cash=None, commission=None, stamp_tax=None):
    conn = get_conn()
    parts = []
    params = []
    if cash is not None:
        parts.append("cash=?")
        params.append(cash)
    if commission is not None:
        parts.append("commission=?")
        params.append(commission)
    if stamp_tax is not None:
        parts.append("stamp_tax=?")
        params.append(stamp_tax)
    parts.append("updated_at=datetime('now','localtime')")
    conn.execute(f"UPDATE paper_account SET {','.join(parts)} WHERE id=1", params)
    conn.commit()
    conn.close()


def get_paper_positions():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM paper_positions").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_paper_position(code, name, shares, avg_cost, current_price=None):
    conn = get_conn()
    market_value = shares * (current_price or avg_cost)
    unrealized_pnl = shares * ((current_price or avg_cost) - avg_cost)
    conn.execute("""
        INSERT OR REPLACE INTO paper_positions(code, name, shares, avg_cost, current_price, market_value, unrealized_pnl, updated_at)
        VALUES(?,?,?,?,?,?,?,datetime('now','localtime'))
    """, (code, name, shares, avg_cost, current_price or avg_cost, market_value, unrealized_pnl))
    conn.commit()
    conn.close()


def delete_paper_position(code):
    conn = get_conn()
    conn.execute("DELETE FROM paper_positions WHERE code=?", (code,))
    conn.commit()
    conn.close()


def save_paper_order(code, name, direction, price, shares, commission=0, stamp_tax=0, reason=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO paper_orders(code, name, direction, price, shares, commission, stamp_tax, reason, status, filled_shares)
        VALUES(?,?,?,?,?,?,?,?,'FILLED',?)
    """, (code, name, direction, price, shares, commission, stamp_tax, reason, shares))
    conn.commit()
    conn.close()


def get_paper_orders(limit=100):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM paper_orders ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_backtest_run(data):
    conn = get_conn()
    conn.execute("""
        INSERT INTO backtest_runs(run_name, start_date, end_date, initial_cash, strategy_params,
                                  final_value, total_return, annual_return, sharpe_ratio,
                                  max_drawdown, win_rate, total_trades)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get('run_name'), data.get('start_date'), data.get('end_date'),
        data.get('initial_cash'), data.get('strategy_params'),
        data.get('final_value'), data.get('total_return'), data.get('annual_return'),
        data.get('sharpe_ratio'), data.get('max_drawdown'),
        data.get('win_rate'), data.get('total_trades'),
    ))
    conn.commit()
    conn.close()
