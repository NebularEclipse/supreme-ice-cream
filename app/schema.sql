DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL
);

DROP TABLE IF EXISTS accounts;

CREATE TABLE accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT NOT NULL,
    type            TEXT CHECK (type IN ('asset', 'liability', 'equity', 'revenue', 'expense')) NOT NULL,
    balance         REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    date            TEXT NOT NULL,
    description     TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS transaction_entries;

CREATE TABLE transaction_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL,
    credited_id      INTEGER NOT NULL,
    debited_id     INTEGER NOT NULL,
    amount          REAL NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (credited_id) REFERENCES accounts(id)
    FOREIGN KEY (debited_id) REFERENCES accounts(id)
);