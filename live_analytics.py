# roulette_sentinel_core/live_analytics.py

"""
Модуль для аналитики в реальном времени: расчет вероятностей, анализ серий и распределений.
"""

from collections import Counter
from typing import List, Dict, Any, Tuple, Optional

# Определения для рулетки (Европейская рулетка)
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
ZERO_NUMBER = 0
ALL_NUMBERS = set(range(37)) # 0-36

DOZENS = {
    1: set(range(1, 13)),  # 1-12
    2: set(range(13, 25)), # 13-24
    3: set(range(25, 37))  # 25-36
}

COLUMNS = {
    1: {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}, # 1st column
    2: {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}, # 2nd column
    3: {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}  # 3rd column
}

EVEN_NUMBERS = {i for i in range(1, 37) if i % 2 == 0}
ODD_NUMBERS = {i for i in range(1, 37) if i % 2 != 0}
LOW_NUMBERS = set(range(1, 19)) # 1-18
HIGH_NUMBERS = set(range(19, 37)) # 19-36

THEORETICAL_PROBABILITIES = {
    "number": 1/37,
    "red": 18/37,
    "black": 18/37,
    "zero": 1/37,
    "even": 18/37,
    "odd": 18/37,
    "low": 18/37,
    "high": 18/37,
    "dozen": 12/37,
    "column": 12/37,
}

def get_number_properties(number: int) -> Dict[str, Any]:
    """Возвращает свойства выпавшего числа."""
    if number not in ALL_NUMBERS:
        raise ValueError(f"Некорректный номер рулетки: {number}")
    
    props = {
        "number": number,
        "is_zero": number == ZERO_NUMBER,
        "color": None,
        "parity": None, # even/odd
        "range": None, # low/high
        "dozen": None,
        "column": None
    }
    if number != ZERO_NUMBER:
        props["color"] = "red" if number in RED_NUMBERS else "black"
        props["parity"] = "even" if number in EVEN_NUMBERS else "odd"
        props["range"] = "low" if number in LOW_NUMBERS else "high"
        for d_num, d_set in DOZENS.items():
            if number in d_set:
                props["dozen"] = d_num
                break
        for c_num, c_set in COLUMNS.items():
            if number in c_set:
                props["column"] = c_num
                break
    return props

def calculate_non_event_streak(history: List[int], event_checker_func) -> int:
    """
    Рассчитывает текущую серию невыпадений определенного события.
    event_checker_func(number_properties) -> bool: должна возвращать True, если событие произошло.
    """
    streak = 0
    for spin_number in reversed(history):
        props = get_number_properties(spin_number)
        if event_checker_func(props):
            break
        streak += 1
    return streak

def analyze_zone_distribution(history: List[int], last_n_spins: Optional[int] = None) -> Dict[str, Dict[Any, int]]:
    """
    Анализирует распределение выпавших номеров по зонам (дюжины/колонны) 
    за сессию или последние N спинов.
    """
    if last_n_spins is not None and last_n_spins > 0:
        relevant_history = history[-last_n_spins:]
    else:
        relevant_history = history

    dozen_counts = Counter()
    column_counts = Counter()
    color_counts = Counter()
    parity_counts = Counter()
    range_counts = Counter()

    for spin_number in relevant_history:
        props = get_number_properties(spin_number)
        if props["dozen"]:
            dozen_counts[props["dozen"]] += 1
        if props["column"]:
            column_counts[props["column"]] += 1
        if props["color"]:
            color_counts[props["color"]] += 1
        if props["parity"]:
            parity_counts[props["parity"]] += 1
        if props["range"]:
            range_counts[props["range"]] += 1
            
    return {
        "dozens": dict(dozen_counts),
        "columns": dict(column_counts),
        "colors": dict(color_counts),
        "parity": dict(parity_counts),
        "ranges": dict(range_counts),
        "total_spins_analyzed": len(relevant_history)
    }

def calculate_deviation_from_theoretical(history: List[int]) -> Dict[str, Dict[Any, Dict[str, float]]]:
    """
    Рассчитывает отклонения фактических частот выпадения от теоретических вероятностей.
    """
    total_spins = len(history)
    if total_spins == 0:
        return {}

    distributions = analyze_zone_distribution(history)
    deviations = {}

    # Цвета
    deviations["colors"] = {}
    for color, count in distributions["colors"].items():
        actual_freq = count / total_spins
        theoretical_freq = THEORETICAL_PROBABILITIES.get(color.lower(), 0)
        deviations["colors"][color] = {
            "count": count,
            "actual_frequency": round(actual_freq, 4),
            "theoretical_frequency": round(theoretical_freq, 4),
            "deviation": round(actual_freq - theoretical_freq, 4)
        }
    # Zero
    zero_count = history.count(0)
    actual_freq_zero = zero_count / total_spins
    theoretical_freq_zero = THEORETICAL_PROBABILITIES["zero"]
    deviations["zero"] = {
        0: {
            "count": zero_count,
            "actual_frequency": round(actual_freq_zero, 4),
            "theoretical_frequency": round(theoretical_freq_zero, 4),
            "deviation": round(actual_freq_zero - theoretical_freq_zero, 4)
        }
    }

    # Дюжины
    deviations["dozens"] = {}
    for dozen, count in distributions["dozens"].items():
        actual_freq = count / total_spins
        theoretical_freq = THEORETICAL_PROBABILITIES["dozen"]
        deviations["dozens"][dozen] = {
            "count": count,
            "actual_frequency": round(actual_freq, 4),
            "theoretical_frequency": round(theoretical_freq, 4),
            "deviation": round(actual_freq - theoretical_freq, 4)
        }
    
    # Колонны
    deviations["columns"] = {}
    for column, count in distributions["columns"].items():
        actual_freq = count / total_spins
        theoretical_freq = THEORETICAL_PROBABILITIES["column"]
        deviations["columns"][column] = {
            "count": count,
            "actual_frequency": round(actual_freq, 4),
            "theoretical_frequency": round(theoretical_freq, 4),
            "deviation": round(actual_freq - theoretical_freq, 4)
        }
        
    # Чет/Нечет, Больше/Меньше - аналогично
    # ... (можно добавить по необходимости)

    return deviations

if __name__ == "__main__":
    print("Тестирование live_analytics.py")
    sample_history = [10, 0, 25, 1, 14, 36, 10, 10, 2, 19, 0, 5, 23, 33, 1, 1, 10, 28, 17, 16]
    print(f"История спинов: {sample_history}")

    # Тест get_number_properties
    print(f"\nСвойства числа 10: {get_number_properties(10)}")
    print(f"Свойства числа 0: {get_number_properties(0)}")
    print(f"Свойства числа 36: {get_number_properties(36)}")

    # Тест calculate_non_event_streak
    def is_red(props): return props["color"] == "red"
    def is_zero(props): return props["is_zero"]
    
    non_red_streak = calculate_non_event_streak(sample_history, is_red)
    # History (rev): 16(R), 17(B), 28(B), 10(B), 1(R) -> streak for non-red before 1(R) is 3 (17,28,10)
    # No, it's how many non-reds from the end until a red. 16 is Red. So streak is 0.
    # Let's trace: 16 (R) -> is_red=T, break. streak=0.
    # If history = [10(B), 20(B), 30(R)]. Reversed: [30(R), 20(B), 10(B)]
    # Spin 30(R): is_red=T, break. streak=0.
    # If history = [10(B), 20(B), 5(B)]. Reversed: [5(B), 20(B), 10(B)]
    # Spin 5(B): is_red=F, streak=1
    # Spin 20(B): is_red=F, streak=2
    # Spin 10(B): is_red=F, streak=3. Returns 3.
    print(f"Серия невыпадения красного: {non_red_streak}") # sample_history[-1]=16 (RED) -> 0
    assert non_red_streak == 0

    non_zero_streak = calculate_non_event_streak(sample_history, is_zero)
    # History (rev): 16,17,28,10,1,1,33,23,5,0. Streak before 0 is 6 (16,17,28,10,1,1,33,23,5)
    # sample_history = [..., 19, 0, 5, ...]. Reversed: [..., 5, 0, 19, ...]
    # Spin 5: not zero, streak=1
    # Spin 0: is zero, break. Returns 1.
    print(f"Серия невыпадения нуля: {non_zero_streak}") # sample_history has 0 at index -9. So 8 spins after it. sample_history[-9] = 0. So 8 non-zeros. No, it's from the end. sample_history[-9] is 0. sample_history[-10] is 19. sample_history[-8] is 5. So before the last 0 (at index -9), there were 8 numbers. The last 0 is at index 10. Spins after it: 5,23,33,1,1,10,28,17,16 (9 spins). So streak is 9.
    # Let's re-verify. sample_history[10] = 0. Spins after it: sample_history[11:] = [5, 23, 33, 1, 1, 10, 28, 17, 16]. Length is 9.
    # All these are non-zero. So streak should be 9.
    assert non_zero_streak == 9 

    # Тест analyze_zone_distribution
    zone_dist = analyze_zone_distribution(sample_history, last_n_spins=10)
    print(f"\nРаспределение по зонам (последние 10 спинов: {sample_history[-10:]}):\n{zone_dist}")
    assert zone_dist["total_spins_analyzed"] == 10
    # Colors for last 10: [5(R), 23(R), 33(B), 1(R), 1(R), 10(B), 28(B), 17(B), 16(R)] + 0 (no color)
    # Last 10: [0, 5, 23, 33, 1, 1, 10, 28, 17, 16]
    # Colors: 0:None, 5:R, 23:R, 33:B, 1:R, 1:R, 10:B, 28:B, 17:B, 16:R
    # Red: 5, Black: 4. Total 9 colored.
    assert zone_dist["colors"] == {"red": 5, "black": 4} 

    # Тест calculate_deviation_from_theoretical
    deviations = calculate_deviation_from_theoretical(sample_history)
    print(f"\nОтклонения от теоретических вероятностей (все {len(sample_history)} спинов):\n{deviations}")
    assert "colors" in deviations
    assert "zero" in deviations
    assert deviations["zero"][0]["count"] == sample_history.count(0)

    print("\nВсе тесты для live_analytics.py (базовые) пройдены.")


