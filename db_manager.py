# roulette_sentinel_core/db_manager.py

"""
Модуль для взаимодействия с базой данных PostgreSQL.
Содержит функции для подключения, CRUD-операций для таблиц users, sessions, spins.
"""




import psycopg2
import psycopg2.extras # Для DictCursor
import os
import logging
import csv
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    client_encoding="UTF8"  # Добавьте эту строку

# Настройка логирования
logger = logging.getLogger(__name__)

# Параметры подключения к БД (лучше брать из переменных окружения)
DB_NAME = os.getenv("DB_NAME", "roulette_db", "roulette_analyst_db")
DB_USER = os.getenv("DB_USER", "roulette_user",)
DB_PASSWORD = os.getenv("DB_PASSWORD", "roulette_pass", "secret123")
DB_HOST = os.getenv("DB_HOST", "localhost") # или IP-адрес/хост контейнера Docker
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    """Устанавливает соединение с базой данных PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info(f"Успешное подключение к БД {DB_NAME} на {DB_HOST}:{DB_PORT}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Ошибка подключения к PostgreSQL: {e}")
        raise

def execute_query(query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    """Выполняет SQL-запрос и возвращает результат."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
                logger.info(f"Запрос выполнен и закоммичен: {query[:50]}...")
                # Для INSERT/UPDATE/DELETE часто нужно вернуть ID или количество строк
                if cur.description and "returning" in query.lower(): # Проверяем, есть ли RETURNING
                    return cur.fetchone()
                return cur.rowcount # Возвращаем количество затронутых строк
            
            if fetch_one:
                return cur.fetchone()
            if fetch_all:
                return cur.fetchall()
            return None # Если не commit и не fetch
    except psycopg2.Error as e:
        logger.error(f"Ошибка выполнения SQL-запроса: {e}\nЗапрос: {query}\nПараметры: {params}")
        if conn and not commit: # Откатываем транзакцию, если это не INSERT/UPDATE с ошибкой до commit
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# --- CRUD для Users ---
def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Получает пользователя по ID или создает нового, если не найден."""
    query_select = "SELECT * FROM users WHERE user_id = %s;"
    user = execute_query(query_select, (user_id,), fetch_one=True)
    if user:
        return dict(user)
    else:
        query_insert = """
        INSERT INTO users (user_id, username, first_name, last_name) 
        VALUES (%s, %s, %s, %s) RETURNING *;
        """
        new_user = execute_query(query_insert, (user_id, username, first_name, last_name), fetch_one=True, commit=True)
        return dict(new_user) if new_user else None

# --- CRUD для Sessions ---
def create_session(user_id: int, initial_bank: float, base_bet: float, strategy_name: str = 'Адаптивный Щит') -> Optional[Dict[str, Any]]:
    """Создает новую игровую сессию."""
    query = """
    INSERT INTO sessions (user_id, initial_bank, current_bank, base_bet, strategy_name, is_active, start_time, last_update_time)
    VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
    RETURNING *;
    """
    session = execute_query(query, (user_id, initial_bank, initial_bank, base_bet, strategy_name), fetch_one=True, commit=True)
    return dict(session) if session else None

def get_active_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает активную сессию пользователя."""
    query = "SELECT * FROM sessions WHERE user_id = %s AND is_active = TRUE ORDER BY start_time DESC LIMIT 1;"
    session = execute_query(query, (user_id,), fetch_one=True)
    return dict(session) if session else None

def update_session(session_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Обновляет данные сессии."""
    if not updates:
        return get_session_by_id(session_id) # Возвращаем текущее состояние, если нет обновлений

    set_clauses = []
    params = []
    for key, value in updates.items():
        set_clauses.append(f"{key} = %s")
        params.append(value)
    
    params.append(session_id)
    query = f"UPDATE sessions SET {', '.join(set_clauses)}, last_update_time = NOW() WHERE session_id = %s RETURNING *;"
    
    updated_session = execute_query(query, tuple(params), fetch_one=True, commit=True)
    return dict(updated_session) if updated_session else None

def end_session(session_id: int) -> Optional[Dict[str, Any]]:
    """Завершает сессию."""
    return update_session(session_id, {"is_active": False, "end_time": datetime.now()})

def get_session_by_id(session_id: int) -> Optional[Dict[str, Any]]:
    """Получает сессию по ее ID."""
    query = "SELECT * FROM sessions WHERE session_id = %s;"
    session = execute_query(query, (session_id,), fetch_one=True)
    return dict(session) if session else None

# --- CRUD для Spins ---
def add_spin(session_id: int, spin_number: int, bet_amount: float, win_amount: float, bank_after_spin: float, 
             bet_type: Optional[str] = None, bet_target: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Добавляет новый спин в историю сессии."""
    query = """
    INSERT INTO spins (session_id, spin_number, bet_type, bet_target, bet_amount, win_amount, bank_after_spin, spin_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    RETURNING *;
    """
    spin = execute_query(query, (session_id, spin_number, bet_type, bet_target, bet_amount, win_amount, bank_after_spin), fetch_one=True, commit=True)
    # После добавления спина, обновить last_update_time сессии
    if spin:
        execute_query("UPDATE sessions SET last_update_time = NOW() WHERE session_id = %s;", (session_id,), commit=True)
    return dict(spin) if spin else None

def get_spins_for_session(session_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Получает историю спинов для сессии."""
    query = "SELECT * FROM spins WHERE session_id = %s ORDER BY spin_time ASC"
    params = [session_id]
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    
    spins = execute_query(query, tuple(params), fetch_all=True)
    return [dict(s) for s in spins] if spins else []

def get_last_n_spins_numbers(session_id: int, n: int) -> List[int]:
    """Получает последние N выпавших чисел для сессии."""
    query = "SELECT spin_number FROM spins WHERE session_id = %s ORDER BY spin_time DESC LIMIT %s;"
    spins_data = execute_query(query, (session_id, n), fetch_all=True)
    return [s["spin_number"] for s in spins_data] if spins_data else []

# --- Экспорт данных ---
def export_session_spins_to_csv(session_id: int, file_path: str) -> bool:
    """Экспортирует историю спинов сессии в CSV файл."""
    spins = get_spins_for_session(session_id)
    if not spins:
        logger.info(f"Нет спинов для экспорта для сессии {session_id}.")
        return False

    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            if not spins: # Дополнительная проверка, хотя выше уже есть
                 csvfile.write("No spins data for this session.\n")
                 return True
            
            fieldnames = spins[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for spin in spins:
                writer.writerow(spin)
        logger.info(f"История спинов для сессии {session_id} успешно экспортирована в {file_path}")
        return True
    except IOError as e:
        logger.error(f"Ошибка записи CSV файла {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при экспорте CSV для сессии {session_id}: {e}")
        return False

if __name__ == '__main__':
    # Для локального тестирования (требуется запущенная и настроенная БД)
    # Установите переменные окружения DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
    # или измените значения по умолчанию в начале файла.
    # Также необходим файл schema.sql для создания таблиц.
    print("Тестирование db_manager.py (требуется настроенная БД)")
    
    # Перед запуском тестов, убедитесь, что схема БД создана.
    # Можно выполнить schema.sql через psql или другую утилиту.

    # Пример: как создать таблицы, если их нет (очень упрощенно, лучше через psql)
    # try:
    #     with open('schema.sql', 'r') as f:
    #         schema_sql = f.read()
    #     execute_query(schema_sql, commit=True) # Это может не сработать для мульти-стейтмент SQL без доработок
    #     print("Схема БД (возможно) применена.")
    # except Exception as e:
    #     print(f"Ошибка применения схемы: {e}")

    # Тест get_or_create_user
    test_user_id = 12345
    user = get_or_create_user(test_user_id, "testuser", "Test", "User")
    print(f"Получен/создан пользователь: {user}")
    assert user and user["user_id"] == test_user_id

    # Тест create_session и get_active_session
    if user:
        active_session = get_active_session(user["user_id"])
        if active_session: # Завершим старую активную сессию, если есть
            print(f"Найдена активная сессия {active_session['session_id']}, завершаем ее для теста.")
            end_session(active_session['session_id'])

        session = create_session(user_id=user["user_id"], initial_bank=1000.0, base_bet=10.0)
        print(f"Создана сессия: {session}")
        assert session and session["user_id"] == user["user_id"] and session["is_active"]
        
        active_session_check = get_active_session(user["user_id"])
        print(f"Проверка активной сессии: {active_session_check}")
        assert active_session_check and active_session_check["session_id"] == session["session_id"]

        if session:
            # Тест add_spin
            spin1 = add_spin(session["session_id"], spin_number=10, bet_amount=10.0, win_amount=0.0, bank_after_spin=990.0, bet_type="red")
            print(f"Добавлен спин 1: {spin1}")
            assert spin1 and spin1["spin_number"] == 10

            spin2 = add_spin(session["session_id"], spin_number=25, bet_amount=20.0, win_amount=40.0, bank_after_spin=1010.0, bet_type="dozen_2")
            print(f"Добавлен спин 2: {spin2}")
            assert spin2 and spin2["spin_number"] == 25

            # Тест get_spins_for_session
            spins_history = get_spins_for_session(session["session_id"])
            print(f"История спинов для сессии {session['session_id']}: {spins_history}")
            assert len(spins_history) == 2

            # Тест get_last_n_spins_numbers
            last_spins = get_last_n_spins_numbers(session["session_id"], 5)
            print(f"Последние числа: {last_spins}") # Должно быть [25, 10]
            assert last_spins == [25, 10]

            # Тест update_session
            updated_s = update_session(session["session_id"], {"current_bank": 1050.0, "current_streak": 1})
            print(f"Обновленная сессия: {updated_s}")
            assert updated_s and updated_s["current_bank"] == 1050.0 and updated_s["current_streak"] == 1

            # Тест экспорта CSV
            csv_file_path = f"/home/ubuntu/session_{session['session_id']}_spins.csv"
            export_success = export_session_spins_to_csv(session["session_id"], csv_file_path)
            print(f"Экспорт сессии {session['session_id']} в CSV: {'Успешно' if export_success else 'Ошибка'}")
            assert export_success
            if export_success:
                print(f"CSV файл сохранен в: {csv_file_path}")
                # (В реальном сценарии файл нужно будет передать пользователю через Telegram)

            # Тест end_session
            ended_session = end_session(session["session_id"])
            print(f"Завершенная сессия: {ended_session}")
            assert ended_session and not ended_session["is_active"] and ended_session["end_time"] is not None
            
            active_session_after_end = get_active_session(user["user_id"])
            print(f"Проверка активной сессии после завершения: {active_session_after_end}")
            assert active_session_after_end is None
    else:
        print("Не удалось создать/получить пользователя, тесты сессий и спинов пропущены.")
    
    print("\nТестирование db_manager.py завершено (проверьте вывод и наличие CSV файла, если БД была доступна).")


