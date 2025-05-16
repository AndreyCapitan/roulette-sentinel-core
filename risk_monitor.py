# roulette_sentinel_core/risk_monitor.py

"""
Модуль для управления рисками: автостоп и zero-буфер.
"""

# Константы для риск-менеджмента, согласно ТЗ
MAX_CONSECUTIVE_LOSSES_LIMIT = 15
MAX_ZEROS_IN_50_SPINS_LIMIT = 4 # ТЗ: 4+ нулей, значит >= 4
DRAWDOWN_LIMIT_PERCENTAGE = 0.20 # 20%
ZERO_BUFFER_CONTRIBUTION_RATE = 0.05 # 5% от выигрыша
ZERO_LOSS_COMPENSATION_RATE = 0.50 # 50% от убытка при '0'
MAX_HISTORY_FOR_ZERO_COUNT = 50

class RiskMonitor:
    """
    Класс для управления состоянием рисков, автостопами и Zero-буфером.
    """
    def __init__(self, initial_bank: float, base_bet: float):
        self.initial_bank = initial_bank
        self.base_bet = base_bet # Может быть полезен для некоторых проверок, хотя напрямую не используется в ТЗ для стопов
        self.reset_state(initial_bank, base_bet) # Инициализируем все переменные состояния

    def reset_state(self, new_initial_bank: float, new_base_bet: float):
        """Сбрасывает состояние монитора к начальным значениям."""
        self.initial_bank = new_initial_bank
        self.current_bank = new_initial_bank
        self.base_bet = new_base_bet
        self.current_streak = 0  # Текущая серия проигрышей
        self.z_count_last_50 = 0 # Количество нулей за последние 50 спинов
        self.zero_buffer = 0.0   # Накопленный Zero-буфер
        self.spin_history_for_zero_count = [] # Хранит результаты последних спинов (0 или 1) для подсчета Z_count
        self.stop_conditions_met = {
            "loss_streak_limit": False,
            "zero_count_limit": False,
            "drawdown_limit": False
        }

    def update_z_count(self):
        """Обновляет z_count_last_50 на основе spin_history_for_zero_count."""
        self.z_count_last_50 = sum(self.spin_history_for_zero_count)

    def check_stop_conditions(self):
        """Проверяет и обновляет флаги автостопа."""
        self.stop_conditions_met["loss_streak_limit"] = self.current_streak >= MAX_CONSECUTIVE_LOSSES_LIMIT
        self.stop_conditions_met["zero_count_limit"] = self.z_count_last_50 >= MAX_ZEROS_IN_50_SPINS_LIMIT
        
        if self.initial_bank > 0:
            drawdown = (self.initial_bank - self.current_bank) / self.initial_bank
            self.stop_conditions_met["drawdown_limit"] = drawdown >= DRAWDOWN_LIMIT_PERCENTAGE
        elif self.current_bank < 0: # Если начальный банк был 0 или меньше
            self.stop_conditions_met["drawdown_limit"] = True # Считаем это как просадку
        else:
            self.stop_conditions_met["drawdown_limit"] = False
        return self.is_stop_suggested()

    def is_stop_suggested(self) -> bool:
        """Возвращает True, если хотя бы одно условие автостопа выполнено."""
        return any(self.stop_conditions_met.values())

    def update_state(self, spin_result: int, bet_amount: float, win_amount: float, is_zero_result: bool, current_bank_override: float = None, is_simulation: bool = False):
        """
        Обновляет состояние риск-монитора после спина.

        Args:
            spin_result: Выпавшее число.
            bet_amount: Сумма сделанной ставки.
            win_amount: Сумма чистого выигрыша от ставки (0 если проигрыш).
            is_zero_result: True, если выпал ноль.
            current_bank_override: (Для симулятора) Позволяет передать текущий банк до обработки этим методом.
            is_simulation: Флаг, указывающий, что вызов идет из симулятора (для логирования или спец. обработки).
        """
        if current_bank_override is not None:
            self.current_bank = current_bank_override
        
        # 1. Обновляем историю для подсчета нулей
        self.spin_history_for_zero_count.append(1 if is_zero_result else 0)
        if len(self.spin_history_for_zero_count) > MAX_HISTORY_FOR_ZERO_COUNT:
            self.spin_history_for_zero_count.pop(0)
        self.update_z_count()

        # 2. Обработка банка и серии проигрышей
        if win_amount > 0: # Выигрыш
            self.current_bank += win_amount # Чистый выигрыш уже учтен, добавляем его к банку (ставка уже вычтена ранее)
            self.current_streak = 0
            # Пополняем zero-буфер
            contribution = win_amount * ZERO_BUFFER_CONTRIBUTION_RATE
            self.zero_buffer = round(self.zero_buffer + contribution, 2)
        else: # Проигрыш (win_amount == 0)
            self.current_bank -= bet_amount # Ставка проиграна
            self.current_streak += 1
            if is_zero_result:
                # Компенсация из zero-буфера
                potential_compensation = bet_amount * ZERO_LOSS_COMPENSATION_RATE
                actual_compensation = min(potential_compensation, self.zero_buffer)
                actual_compensation = round(actual_compensation, 2)
                
                self.current_bank += actual_compensation # Возвращаем часть проигрыша
                self.zero_buffer = round(self.zero_buffer - actual_compensation, 2)
        
        self.current_bank = round(self.current_bank, 2)

        # 3. Проверяем условия автостопа
        self.check_stop_conditions()

# Функции-хелперы, если они нужны где-то еще отдельно, 
# но основная логика теперь в классе RiskMonitor.
# Для совместимости с предыдущими тестами, если они вызывали эти функции напрямую,
# можно их оставить, но лучше рефакторить тесты под использование методов класса.

def check_autostop_conditions_func(streak: int, z_count_last_50: int, initial_bank: float, current_bank: float) -> list[str]:
    reasons = []
    if streak >= MAX_CONSECUTIVE_LOSSES_LIMIT:
        reasons.append(f"Достигнут лимит проигрышей подряд: {streak} >= {MAX_CONSECUTIVE_LOSSES_LIMIT}.")
    if z_count_last_50 >= MAX_ZEROS_IN_50_SPINS_LIMIT:
        reasons.append(f"Достигнут лимит нулей за последние 50 спинов: {z_count_last_50} >= {MAX_ZEROS_IN_50_SPINS_LIMIT}.")
    if initial_bank > 0:
        drawdown = (initial_bank - current_bank) / initial_bank
        if drawdown >= DRAWDOWN_LIMIT_PERCENTAGE:
            reasons.append(f"Достигнут лимит просадки банка: {drawdown*100:.2f}% >= {DRAWDOWN_LIMIT_PERCENTAGE*100}% (Начальный: {initial_bank}, Текущий: {current_bank}).")
    elif current_bank < 0:
        reasons.append(f"Отрицательный текущий банк: {current_bank} при начальном банке {initial_bank}.")
    return reasons

if __name__ == '__main__':
    print("Тестирование RiskMonitor класса")
    monitor = RiskMonitor(initial_bank=1000, base_bet=10)
    print(f"Initial state: bank={monitor.current_bank}, streak={monitor.current_streak}, z_count={monitor.z_count_last_50}, buffer={monitor.zero_buffer}")

    # Пример выигрыша
    monitor.update_state(spin_result=1, bet_amount=10, win_amount=10, is_zero_result=False) # Ставка 10, выигрыш 10 (чистый)
    print(f"After win: bank={monitor.current_bank}, streak={monitor.current_streak}, z_count={monitor.z_count_last_50}, buffer={monitor.zero_buffer}")
    # Ожидаемый банк: 1000 (начальный) - 0 (т.к. ставка была 10, выигрыш 10, то банк не меняется от ставки, но +10 от выигрыша)
    # Ой, логика update_state в симуляторе и тут должна быть согласована.
    # Если win_amount - это чистый выигрыш, то банк должен быть current_bank_override (который до вычета ставки) - bet_amount + bet_amount (возврат) + win_amount.
    # Или current_bank_override + win_amount.
    # В RiskMonitor.update_state: self.current_bank += win_amount (если выиграл), self.current_bank -= bet_amount (если проиграл)
    # Это значит, что current_bank_override должен быть банком *до* вычета ставки.
    # Симулятор: self.current_bank -= bet_amount; ... self.risk_monitor.update_state(..., current_bank_override=bank_before_bet_for_this_spin ...)
    # В RiskMonitor: self.current_bank = current_bank_override; ... self.current_bank += win_amount (если выиграл)
    # Это правильно. Банк после выигрыша 10 (чистыми) при ставке 10: 1000 + 10 = 1010. Буфер: 10 * 0.05 = 0.5
    assert abs(monitor.current_bank - 1010) < 0.01
    assert abs(monitor.zero_buffer - 0.5) < 0.01

    # Пример проигрыша
    monitor.reset_state(1000, 10)
    monitor.update_state(spin_result=2, bet_amount=10, win_amount=0, is_zero_result=False, current_bank_override=1000)
    print(f"After loss: bank={monitor.current_bank}, streak={monitor.current_streak}, z_count={monitor.z_count_last_50}, buffer={monitor.zero_buffer}")
    # Банк: 1000 - 10 = 990. Streak 1.
    assert abs(monitor.current_bank - 990) < 0.01
    assert monitor.current_streak == 1

    # Пример проигрыша на зеро с компенсацией
    monitor.reset_state(1000, 10)
    monitor.zero_buffer = 20 # Предзаполненный буфер
    monitor.update_state(spin_result=0, bet_amount=10, win_amount=0, is_zero_result=True, current_bank_override=1000)
    print(f"After zero loss with buffer: bank={monitor.current_bank}, streak={monitor.current_streak}, z_count={monitor.z_count_last_50}, buffer={monitor.zero_buffer}")
    # Убыток 10. Компенсация 50% = 5. Банк: 1000 - 10 + 5 = 995. Буфер: 20 - 5 = 15. Streak 1. Z_count 1.
    assert abs(monitor.current_bank - 995) < 0.01
    assert abs(monitor.zero_buffer - 15) < 0.01
    assert monitor.current_streak == 1
    assert monitor.z_count_last_50 == 1

    print("\nТесты класса RiskMonitor пройдены.")

