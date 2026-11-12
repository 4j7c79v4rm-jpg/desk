"""SQLite schema (STEP 4) + helpers. WAL mode."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS coins (
    mint TEXT PRIMARY KEY,
    name TEXT, symbol TEXT, pool TEXT, migrated_at TEXT,
    creator TEXT, creator_balance_at_migration REAL, holders INTEGER
);
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint TEXT, ts TEXT, liquidity_usd REAL, top10_pct REAL,
    h1_change_pct REAL, age_min INTEGER, verdict TEXT, reason TEXT
);
CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint TEXT, ts TEXT, layer INTEGER, name TEXT, value_text TEXT,
    pass INTEGER, source TEXT
);
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint TEXT, ts TEXT, alive_6h REAL, organic REAL, flush REAL, chase REAL,
    score INTEGER, pass INTEGER, reason TEXT, input_tokens INTEGER
);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint TEXT, ts TEXT, price REAL, size_usd REAL, stack_pct REAL,
    link TEXT, mode TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint TEXT, opened_at TEXT, entry_price REAL, size_usd REAL,
    peak_price REAL, stop_price REAL, trail_active INTEGER,
    closed_at TEXT, exit_price REAL, exit_reason TEXT,
    pnl_usd REAL, fees_usd REAL, mode TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, kind TEXT, mint TEXT, agent TEXT, title TEXT, subtitle TEXT, value TEXT
);
CREATE TABLE IF NOT EXISTS prices (
    mint TEXT, ts TEXT, price REAL, volume_m5 REAL
);
CREATE TABLE IF NOT EXISTS balance (
    ts TEXT, value REAL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS change_log (
    ts TEXT, key TEXT, old TEXT, new TEXT, who TEXT
);
CREATE TABLE IF NOT EXISTS skips (
    mint TEXT, until TEXT
);
CREATE TABLE IF NOT EXISTS heartbeats (
    agent TEXT, ts TEXT
);
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint TEXT PRIMARY KEY, p256dh TEXT, auth TEXT, created_at TEXT
);
"""


def connect(path: str = "desk.db") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn
