-- Expense Tracker schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS expenses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date   TEXT    NOT NULL,                       -- ISO format YYYY-MM-DD
    amount         REAL    NOT NULL CHECK (amount > 0),
    category_id    INTEGER NOT NULL,
    payment_method TEXT    NOT NULL,
    description    TEXT    DEFAULT '',
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

CREATE TABLE IF NOT EXISTS income (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    income_date TEXT NOT NULL,
    amount      REAL NOT NULL CHECK (amount > 0),
    source      TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    month       TEXT    NOT NULL,                          -- YYYY-MM
    amount      REAL    NOT NULL CHECK (amount > 0),
    UNIQUE (category_id, month),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

CREATE INDEX IF NOT EXISTS idx_expenses_date     ON expenses (expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category_id);
CREATE INDEX IF NOT EXISTS idx_income_date       ON income (income_date);
