-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица генераций тестов (с новыми полями)
CREATE TABLE IF NOT EXISTS generations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(500) NOT NULL,
    num_questions INTEGER NOT NULL,
    quiz_text TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    parent_id INTEGER REFERENCES generations(id) ON DELETE SET NULL,
    model_used VARCHAR(100) DEFAULT 'local',
    generation_time DOUBLE PRECISION,
    prompt_length INTEGER,
    response_length INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица логов генераций
CREATE TABLE IF NOT EXISTS generation_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    topic VARCHAR(500) NOT NULL,
    num_questions INTEGER NOT NULL,
    quiz_text TEXT NOT NULL,
    model_used VARCHAR(100),
    generation_time DOUBLE PRECISION,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);