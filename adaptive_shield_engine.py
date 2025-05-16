# roulette_sentinel_core/adaptive_shield_engine.py

"""
Модуль для расчета ставок по стратегии «Адаптивный Щит».
"""

FIBONACCI_CACHE = {}

def get_fib_for_streak(streak: int) -> int:
    """
    Рассчитывает число Фибоначчи для текущей серии проигрышей (streak).
    Последовательность Fib_k (где k = streak):
    Fib_0 = 1 (базовый случай для отсутствия проигрышей)
    Fib_1 = 1
    Fib_2 = 1 
    Fib_3 = 2
    Fib_4 = 3
    Fib_5 = 5
    ...
    Fib_12 = 144 (согласно примеру в ТЗ)
    """
    if not isinstance(streak, int) or streak < 0:
        raise ValueError("Серия проигрышей (streak) должна быть неотрицательным целым числом.")

    if streak in FIBONACCI_CACHE:
        return FIBONACCI_CACHE[streak]

    if streak == 0:
        result = 1
    elif streak == 1:
        result = 1
    elif streak == 2: # F_2 = 1, to match F_12 = 144 from 1,1,2,3,5... sequence where F_1=1, F_2=1
        result = 1
    else: # streak >= 3. Calculate F_k = F_{k-1} + F_{k-2}
        val_minus_1 = get_fib_for_streak(streak - 1)
        val_minus_2 = get_fib_for_streak(streak - 2)
        result = val_minus_1 + val_minus_2
        
    FIBONACCI_CACHE[streak] = result
    return result

def calculate_bet(base_bet: float, current_streak: int, z_count_last_50: int) -> float:
    """
    Рассчитывает размер ставки по формуле v3.1 «Адаптивный Щит».
    Симулятор передает current_streak, поэтому используем его в сигнатуре.

    Betₖ = (Base × Fibₖ × BufferFactor) / RiskIndex

    Args:
        base_bet: Базовая ставка (например, 10.0).
        current_streak: Текущая серия проигрышей (целое число, >= 0).
        z_count_last_50: Количество нулей за последние 50 спинов (целое число, >= 0).

    Returns:
        Размер рассчитанной ставки (округленный до 2 знаков).
        Возвращает 0.0, если ставка не может быть сделана.
    """
    streak = current_streak # Используем внутреннее имя streak для совместимости с get_fib_for_streak

    if base_bet <= 0:
        return 0.0 
    if streak < 0:
        return 0.0
    if not (0 <= z_count_last_50 <= 50):
        return 0.0

    fib_k = get_fib_for_streak(streak)
    
    buffer_factor = 1.0 - (z_count_last_50 / 50.0)
    if buffer_factor <= 0: 
        return 0.0
        
    risk_index = 1.0 + (streak / 15.0)
    if risk_index <= 0: 
        return 0.0

    bet_amount = (base_bet * fib_k * buffer_factor) / risk_index
    
    return round(bet_amount, 2)

if __name__ == '__main__':
    print("Тестирование adaptive_shield_engine.py")
    
    print("Тест чисел Фибоначчи (Fib_k для streak k):")
    expected_fibs = {
        0: 1, 1: 1, 2: 1, 3: 2, 4: 3, 5: 5, 6: 8, 7: 13, 8: 21, 9: 34, 10: 55, 11: 89, 12: 144
    }
    for i in range(13):
        calculated_fib = get_fib_for_streak(i)
        print(f"Streak {i}: Fib = {calculated_fib}, Ожидалось: {expected_fibs[i]}, Совпадение: {calculated_fib == expected_fibs[i]}")
        assert calculated_fib == expected_fibs[i]

    print("\nТест расчета ставки (пример из ТЗ):")
    base = 10.0
    z_count = 3
    streak_val = 12 # Это current_streak для функции calculate_bet
    expected_bet = 752.00
    
    calculated_bet_val = calculate_bet(base_bet=base, current_streak=streak_val, z_count_last_50=z_count)
    print(f"Base={base}, current_streak={streak_val}, z_count_last_50={z_count}")
    print(f"Рассчитанная ставка: {calculated_bet_val}, Ожидаемая: {expected_bet}")
    assert abs(calculated_bet_val - expected_bet) < 0.01, f"Ошибка в расчете: {calculated_bet_val} != {expected_bet}"
    print("Тест примера из ТЗ пройден.")

    print("\nДополнительные тесты расчета ставки:")
    bet_s0 = calculate_bet(base_bet=10.0, current_streak=0, z_count_last_50=3)
    print(f"current_streak 0: Bet = {bet_s0}, Ожидалось: 9.4")
    assert abs(bet_s0 - 9.4) < 0.01

    bet_bf0 = calculate_bet(base_bet=10.0, current_streak=5, z_count_last_50=50)
    print(f"BufferFactor=0: Bet = {bet_bf0}, Ожидалось: 0.0")
    assert abs(bet_bf0 - 0.0) < 0.01

    bet_bf_neg = calculate_bet(base_bet=10.0, current_streak=5, z_count_last_50=60)
    print(f"z_count_last_50 > 50: Bet = {bet_bf_neg}, Ожидалось: 0.0")
    assert abs(bet_bf_neg - 0.0) < 0.01

    print("\nВсе тесты для adaptive_shield_engine.py пройдены.")

