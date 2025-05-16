# roulette_sentinel_core/simulator.py

import random
import time
from datetime import datetime

# Corrected imports for direct script execution from roulette_sentinel_core directory
from adaptive_shield_engine import calculate_bet
from risk_monitor import RiskMonitor
from live_analytics import get_number_properties # Для определения зеро

# Константы для рулетки (Европейская)
EUROPEAN_ROULETTE_NUMBERS = list(range(37)) # 0-36

class RouletteSimulator:
    """
    Симулятор для проверки стратегии «Адаптивный Щит».
    """
    def __init__(self, initial_bank, base_bet, strategy_engine, risk_monitor_instance):
        self.initial_bank = initial_bank
        self.base_bet = base_bet
        self.strategy_engine = strategy_engine # Функция calculate_bet
        self.risk_monitor = risk_monitor_instance
        
        self.current_bank = initial_bank
        self.spin_history = [] # Список выпавших чисел
        self.bet_history = []  # Список сделанных ставок и результатов
        self.session_stats = {
            "total_spins": 0,
            "wins": 0,
            "losses": 0,
            "zeros_hit": 0,
            "max_streak_loss": 0,
            "max_drawdown": 0,
            "current_drawdown": 0,
            "bank_history": [initial_bank],
            "stop_triggers": {k: 0 for k in self.risk_monitor.stop_conditions_met.keys()},
            "final_bank": initial_bank,
            "profit_loss": 0,
            "roi": 0,
            "zero_buffer_accumulated": 0,
            "zero_buffer_spent": 0
        }

    def _spin_wheel(self):
        """Имитирует один спин рулетки."""
        return random.choice(EUROPEAN_ROULETTE_NUMBERS)

    def _place_bet_and_determine_outcome(self, bet_amount, spin_result):
        """
        Имитирует ставку (например, на красное/черное или другое простое событие).
        Для упрощения симуляции, предположим, что бот всегда ставит на "красное".
        Выигрыш 1:1.
        """
        if bet_amount <= 0: # Не ставим, если ставка нулевая или отрицательная
            return 0, False # win_amount, is_zero

        props = get_number_properties(spin_result)
        is_zero_result = props["is_zero"]
        
        # Упрощенная логика ставки: всегда на красное
        # Можно расширить для других типов ставок, если потребуется
        if not is_zero_result and props["color"] == "red":
            win_amount = bet_amount # Выигрыш 1:1
        else:
            win_amount = 0 # Проигрыш
            
        return win_amount, is_zero_result

    def run_simulation(self, num_spins):
        """Запускает симуляцию на N спинов."""
        print(f"--- Starting Simulation: {num_spins} spins, Initial Bank: {self.initial_bank}, Base Bet: {self.base_bet} ---")
        start_time = time.time()

        for spin_count in range(1, num_spins + 1):
            self.session_stats["total_spins"] = spin_count

            # 1. Проверить условия автостопа ПЕРЕД ставкой
            if self.risk_monitor.is_stop_suggested():
                print(f"Stop condition met at spin {spin_count} BEFORE betting. Bank: {self.current_bank:.2f}")
                for k, v in self.risk_monitor.stop_conditions_met.items():
                    if v: self.session_stats["stop_triggers"][k] += 1
                break

            # 2. Рассчитать ставку
            bet_amount = self.strategy_engine(
                base_bet=self.base_bet,
                current_streak=self.risk_monitor.current_streak,
                z_count_last_50=self.risk_monitor.z_count_last_50
            )
            
            bet_amount = round(bet_amount, 2) # Округляем до копеек
            bet_amount = min(bet_amount, self.current_bank) # Ставка не может быть больше текущего банка

            if bet_amount <= 0: 
                actual_spin_result = self._spin_wheel()
                self.spin_history.append(actual_spin_result)
                self.risk_monitor.update_state(spin_result=actual_spin_result, bet_amount=0, win_amount=0, is_zero_result=get_number_properties(actual_spin_result)["is_zero"], is_simulation=True)
                self.bet_history.append({
                    "spin": spin_count,
                    "result": actual_spin_result,
                    "bet_amount": 0,
                    "win_amount_from_bet": 0,
                    "bank_before_bet": self.current_bank,
                    "bank_after_spin": self.current_bank,
                    "streak_before_bet": self.risk_monitor.current_streak,
                    "z_count_before_bet": self.risk_monitor.z_count_last_50,
                    "risk_index": 1 + (self.risk_monitor.current_streak / 15),
                    "buffer_factor": 1 - (self.risk_monitor.z_count_last_50 / 50)
                })
                # print(f"Spin {spin_count}: No bet placed (strategy result: {bet_amount:.2f}). Bank: {self.current_bank:.2f}")
                continue

            # 3. Сделать спин
            actual_spin_result = self._spin_wheel()
            self.spin_history.append(actual_spin_result)

            # 4. Определить исход ставки
            bank_before_bet_for_this_spin = self.current_bank
            
            win_amount, is_zero_result = self._place_bet_and_determine_outcome(bet_amount, actual_spin_result)
            
            # 5. Обновить состояние риск-монитора и банка
            initial_zero_buffer_before_update = self.risk_monitor.zero_buffer
            
            self.risk_monitor.update_state(
                spin_result=actual_spin_result, 
                bet_amount=bet_amount, 
                win_amount=win_amount, 
                is_zero_result=is_zero_result,
                current_bank_override=bank_before_bet_for_this_spin, # Передаем банк до вычета ставки
                is_simulation=True
            )
            self.current_bank = self.risk_monitor.current_bank
            
            if self.risk_monitor.zero_buffer > initial_zero_buffer_before_update:
                self.session_stats["zero_buffer_accumulated"] += round(self.risk_monitor.zero_buffer - initial_zero_buffer_before_update, 2)
            elif self.risk_monitor.zero_buffer < initial_zero_buffer_before_update:
                 self.session_stats["zero_buffer_spent"] += round(initial_zero_buffer_before_update - self.risk_monitor.zero_buffer, 2)

            # 6. Записать статистику спина
            # Streak и Z_count для записи - это те, что были *до* этого спина
            streak_before_this_spin = self.risk_monitor.current_streak
            z_count_before_this_spin = self.risk_monitor.z_count_last_50
            if win_amount == 0 and not is_zero_result: # Если это был проигрыш не на зеро, то current_streak уже увеличен
                streak_before_this_spin -=1
            if is_zero_result: # Если это был зеро, то z_count_last_50 уже увеличен
                 z_count_before_this_spin -=1
            streak_before_this_spin = max(0, streak_before_this_spin) # не может быть отрицательным
            z_count_before_this_spin = max(0, z_count_before_this_spin) # не может быть отрицательным

            self.bet_history.append({
                "spin": spin_count,
                "result": actual_spin_result,
                "bet_amount": bet_amount,
                "win_amount_from_bet": win_amount, 
                "bank_before_bet": bank_before_bet_for_this_spin,
                "bank_after_spin": self.current_bank,
                "streak_before_bet": streak_before_this_spin,
                "z_count_before_bet": z_count_before_this_spin,
                "risk_index": round(1 + (streak_before_this_spin / 15), 4),
                "buffer_factor": round(1 - (z_count_before_this_spin / 50), 4)
            })
            self.session_stats["bank_history"].append(self.current_bank)

            if win_amount > 0:
                self.session_stats["wins"] += 1
            else:
                self.session_stats["losses"] += 1
            
            if is_zero_result:
                self.session_stats["zeros_hit"] += 1

            self.session_stats["max_streak_loss"] = max(self.session_stats["max_streak_loss"], self.risk_monitor.current_streak)
            
            current_drawdown_val = self.initial_bank - self.current_bank
            if current_drawdown_val > 0:
                 self.session_stats["max_drawdown"] = max(self.session_stats["max_drawdown"], current_drawdown_val)
            self.session_stats["current_drawdown"] = current_drawdown_val

            # print(f"Spin {spin_count:4}: Result={actual_spin_result:2}, Bet={bet_amount:8.2f}, Win={win_amount:8.2f}, Bank={self.current_bank:10.2f}, Streak={self.risk_monitor.current_streak}, Zeros(50)={self.risk_monitor.z_count_last_50}, ZB={self.risk_monitor.zero_buffer:.2f}")

            # 7. Проверить условия автостопа ПОСЛЕ ставки и обновления состояния
            if self.risk_monitor.is_stop_suggested():
                print(f"Stop condition met at spin {spin_count} AFTER betting. Bank: {self.current_bank:.2f}")
                for k, v in self.risk_monitor.stop_conditions_met.items():
                    if v: self.session_stats["stop_triggers"][k] += 1
                break
            
            if self.current_bank <= 0:
                print(f"Bankrupt at spin {spin_count}. Bank: {self.current_bank:.2f}")
                break
        
        self.session_stats["final_bank"] = self.current_bank
        self.session_stats["profit_loss"] = self.current_bank - self.initial_bank
        if self.initial_bank > 0:
            self.session_stats["roi"] = (self.session_stats["profit_loss"] / self.initial_bank) * 100
        else:
            self.session_stats["roi"] = 0
        
        end_time = time.time()
        print(f"--- Simulation Ended. Duration: {end_time - start_time:.2f} seconds ---")
        self.print_summary()
        return self.session_stats

    def print_summary(self):
        print("\n--- Simulation Summary ---")
        print(f"Total Spins: {self.session_stats['total_spins']}")
        print(f"Initial Bank: {self.initial_bank:.2f}")
        print(f"Final Bank: {self.session_stats['final_bank']:.2f}")
        print(f"Profit/Loss: {self.session_stats['profit_loss']:.2f}")
        print(f"ROI: {self.session_stats['roi']:.2f}%")
        print(f"Wins: {self.session_stats['wins']}, Losses: {self.session_stats['losses']}")
        print(f"Zeros Hit: {self.session_stats['zeros_hit']}")
        print(f"Max Loss Streak: {self.session_stats['max_streak_loss']}")
        print(f"Max Drawdown Amount: {self.session_stats['max_drawdown']:.2f} ({(self.session_stats['max_drawdown']/self.initial_bank*100 if self.initial_bank > 0 else 0):.2f}% of initial bank)")
        print(f"Zero Buffer Accumulated: {self.session_stats['zero_buffer_accumulated']:.2f}")
        print(f"Zero Buffer Spent on Compensation: {self.session_stats['zero_buffer_spent']:.2f}")
        print("Stop Conditions Triggered:")
        for trigger, count in self.session_stats["stop_triggers"].items():
            if count > 0:
                print(f"  - {trigger}: {count} time(s)")
        if self.current_bank <= 0 and self.session_stats['total_spins'] > 0 and not any(st > 0 for st in self.session_stats["stop_triggers"].values()):
             print(f"  - Bankrupt: 1 time(s)")
        print("------------------------\n")

if __name__ == "__main__":
    sim_initial_bank = 10000
    sim_base_bet = 10
    
    # Create a new RiskMonitor instance for each simulation run or reset it.
    risk_monitor_sim = RiskMonitor(initial_bank=sim_initial_bank, base_bet=sim_base_bet)
    
    simulator = RouletteSimulator(
        initial_bank=sim_initial_bank, 
        base_bet=sim_base_bet, 
        strategy_engine=calculate_bet, 
        risk_monitor_instance=risk_monitor_sim
    )
    simulation_results = simulator.run_simulation(num_spins=1000)

    # Example of running another simulation with a reset monitor
    # print("\nRunning second simulation with reset monitor...")
    # sim_initial_bank_2 = 5000
    # sim_base_bet_2 = 5
    # risk_monitor_sim.reset_state(new_initial_bank=sim_initial_bank_2, new_base_bet=sim_base_bet_2)
    # simulator_2 = RouletteSimulator(
    #     initial_bank=sim_initial_bank_2, 
    #     base_bet=sim_base_bet_2, 
    #     strategy_engine=calculate_bet, 
    #     risk_monitor_instance=risk_monitor_sim # Reusing the reset monitor
    # )
    # simulator_2.run_simulation(num_spins=500)

