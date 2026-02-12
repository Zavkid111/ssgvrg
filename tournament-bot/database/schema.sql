CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_banned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    max_players INTEGER,
    entry_fee INTEGER,
    prize_places INTEGER,
    prizes TEXT,
    requisites TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER,
    user_id INTEGER,
    username TEXT,
    nickname TEXT,
    payment_status TEXT,
    result_status TEXT,
    claimed_place INTEGER,
    requisites TEXT
);
