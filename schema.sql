-- Схема Базы Данных для проекта «Умный аналитик рулетки»
-- PostgreSQL

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,     -- Telegram User ID
    username VARCHAR(255),          -- Telegram Username (может быть NULL)
    first_name VARCHAR(255),        -- Telegram First Name
    last_name VARCHAR(255),         -- Telegram Last Name (может быть NULL)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- Дата регистрации в боте
);

-- Таблица игровых сессий
CREATE TABLE IF NOT EXISTS sessions (
    session_id SERIAL PRIMARY KEY,      -- Уникальный ID сессии
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE, -- Связь с пользователем
    strategy_name VARCHAR(100) DEFAULT 'Адаптивный Щит', -- Название используемой стратегии
    initial_bank FLOAT NOT NULL,        -- Начальный банк сессии
    current_bank FLOAT NOT NULL,        
    base_bet FLOAT NOT NULL,           
    current_streak INT DEFAULT 0,      
    z_count_last_50 INT DEFAULT 0,    
    zero_buffer FLOAT DEFAULT 0.0,      
    is_active BOOLEAN DEFAULT TRUE,    
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_update_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    end_time TIMESTAMP WITH TIME ZONE DEFAULT NULL 
);

-- Таблица истории спинов
CREATE TABLE IF NOT EXISTS spins (
    spin_id SERIAL PRIMARY KEY,         
    session_id INT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE, 
    bet_type VARCHAR(50),               
    bet_target VARCHAR(50),             
    bet_amount FLOAT,                   
    win_amount FLOAT,                   
                                        
    bank_after_spin FLOAT NOT NULL,     
    spin_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP 
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions (is_active);
CREATE INDEX IF NOT EXISTS idx_spins_session_id ON spins (session_id);


CREATE OR REPLACE FUNCTION update_session_last_update_time() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_update_time = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_last_update
BEFORE UPDATE ON sessions
FOR EACH ROW
EXECUTE FUNCTION update_session_last_update_time();


