from typing import TYPE_CHECKING, Set, Union
from banking.bank_interface import BankInterface
from dataclasses import dataclass, field
from base_agent import BaseAgent, BaseStats
import math
import numpy as np

if TYPE_CHECKING:
    from .person import Person
    from banking.agents.bank import Bank
    from banking.bank_interface import BankInterface
    from banking.bank_accounting import Loan


class CorpStats(BaseStats):
    def __init__(self):
        super().__init__()  # Initializes self.tick = 0
        self.sales: dict[int, float] = {}
        self.revenue: dict[int, float] = {}
        self.profit: dict[int, float] = {}
        self.costs: dict[int, float] = {}
        self.demand: dict[int, float] = {}
        self.production: dict[int, float] = {}
        self.price: dict[int, float] = {}
        self.salary: dict[int, float] = {}
        self.hiring: dict[int, bool] = {}
        self.ppe: dict[int, int] = {}
        self.overstock: dict[int, int] = {}

    def trend(self, stat_name: str, lookback: int = 4) -> float:

        if self.tick < lookback:
            raise Exception(f"Not enough data to calculate {stat_name} trend")

        # Get the stat dictionary
        stat_dict = getattr(self, stat_name)

        # Get the last 'lookback' values, excluding the current tick
        values = list(stat_dict.values())[:-1][-lookback:]

        # Calculate means of first and second halves
        first_half = np.mean(values[: lookback // 2])
        second_half = np.mean(values[lookback // 2 :])

        if first_half == 0:
            return 0.0

        return (second_half - first_half) / first_half


@dataclass
class Good:
    price: float


class Corporation(BaseAgent):

    def __init__(self, bank: Union["Bank", None] = None) -> None:
        super().__init__("Corp")  # Initialize BaseAgent with Corp prefix
        self.employees: Set["Person"] = set()
        self.bank_interface = BankInterface(bank, self) if bank else None
        self.stats = CorpStats()
        self.goods: list[Good] = []
        self.salary: float = 0
        self.latest_sales: int = 0
        self.latest_demand: int = 0
        self.current_price: float = 0
        self.latest_revenue: float = 0
        self.latest_costs: float = 0
        self.hiring: bool = True
        self.ppe: int = 0
        self.alive = True
        self.loans: list[Loan] = []

    def add_employee(self, employee: "Person") -> None:
        employee.employed = True
        employee.salary = self.salary
        self.employees.add(employee)
        self.reivew_hiring()

    def pay_salaries(self) -> None:
        for employee in self.employees:
            self.pay_salary(employee)

    def pay_salary(self, employee: "Person") -> None:

        if self.bank_interface.check_balance() < self.salary:
            raise Exception(f"Failing to pay salary on tick {self.tick}")

        wtid, dtid = self.bank_interface.transfer(
            self.salary, to=employee.bank_interface
        )
        self.latest_costs += self.salary
        self.stats.record(self.tick, costs=self.latest_costs)

        employee.latest_salary_id = dtid
        return wtid, dtid

    def change_salary(self, pct: float) -> float:
        old_salary = self.salary
        self.salary = self.salary * (1 + pct)
        self.stats.record(self.tick, salary=self.salary)
        return len(self.employees) * (old_salary - self.salary)

    def revenue_trend(self) -> float:
        return self.stats.trend("revenue")

    def sales_trend(self) -> float:
        return self.stats.trend("sales")

    def overstock_trend(self) -> float:
        return self.stats.trend("overstock")

    def pay_interest(self) -> None:
        pass

    def finance_action(self, allow_borrow: bool = True) -> tuple[str, float]:
        recommendation = self.finance_recommendation(allow_borrow)
        action, amount = recommendation
        self._log(f"action: {action}, amount: {amount}", level="warning")
        if action == "borrow_funds" and allow_borrow:
            loan = self.bank_interface.borrow_funds(amount)
            if loan:
                self.loans.append(loan)
            else:
                self.finance_action(allow_borrow=False)
        elif action == "fire_employees":
            self.remove_employees(amount)
        elif action == "lower_salary":
            self.change_salary(-0.05)
        elif action == "decrease_price":
            self.hiring = False
            self.current_price *= 0.95
        elif action == "increase_price":
            self.hiring = True
            self.current_price *= 1.05
        elif action == "ok":
            pass

        return action, amount

    def finance_recommendation(self, allow_borrow: bool = True) -> tuple[str, float]:
        # We need atleast 4 months of data to review finance
        if self.tick < 4:
            raise Exception(f"Not enough data to review finance on tick {self.tick}")
        # Burn = costs - revenue (how money we are losing or making)
        # Runway = balance / burn (how many months we can survive)
        # Trend = if revenue is increasing or decreasing
        runway, burn, net_margin = self.forecast()
        revenue_trend = self.revenue_trend()
        sales_trend = self.sales_trend()
        overstock_trend = self.overstock_trend()
        # We want to atleast have 6 months of runway
        target_runway = 6
        monthly_burn = burn / 4 if burn > 0 else 0
        missing = (target_runway - runway) * monthly_burn
        # We are losing money
        self._log(
            f"Runway: {runway}, Burn: {burn}, Net margin: {net_margin}, monthly burn: {monthly_burn}",
            level="warning",
        )
        if missing > 0:
            # Is the trend positive?
            if revenue_trend >= 0 and allow_borrow:
                # We are losing money but the trend is positive
                # We should borrow money
                return "borrow_funds", missing
            else:
                # We are losing money and the trend is negative
                # We should reduce costs
                # is runway less than 3?
                if runway < 3:
                    # We should fire employees
                    return "fire_employees", missing
                else:
                    # We should lower salary
                    return "lower_salary", 0

        else:
            # We are making money
            if revenue_trend >= 0:
                return "increase_price", 0
            else:
                return "decrease_price", 0

    def forecast(self):

        if self.tick < 4:
            raise Exception("Not enough data to forecast")

        balance = self.bank_interface.check_balance()
        costs = list(self.stats.costs.values())[:-1][-4:]
        revenue = list(self.stats.revenue.values())[:-1][-4:]

        # totals
        total_costs = sum(costs)
        total_revenue = sum(revenue)

        net_margin = total_revenue - total_costs

        burn = max(0, total_costs - total_revenue)

        if burn > 0:
            runway = balance / burn
        else:
            runway = float("inf")

        return runway, burn, net_margin

    def remove_employees(self, save):
        num_to_fire = math.ceil(save / self.salary)
        self._log(f"Firing {num_to_fire} employees to save {save}", level="warning")
        saved = 0
        for _ in range(num_to_fire):
            employee = self.employees.pop()
            employee.employed = False
            tid = employee.bank_interface.deposit(employee.salary)
            employee.latest_salary_id = tid
            saved += self.salary

        return saved

    def check_inventory(self) -> bool:
        return len(self.goods) > 0

    def register_demand(self, demand: int) -> None:
        self.latest_demand += demand
        self.stats.record(self.tick, demand=self.latest_demand)

    def sell_good(self, bank_interface: "BankInterface") -> Good | None:

        if self.check_inventory():
            bank_interface.transfer(self.current_price, to=self.bank_interface)
            good = self.goods.pop(0)
            self.latest_sales += 1
            self.latest_revenue += self.current_price
            self.stats.record(self.tick, sales=self.latest_sales)
            self.stats.record(self.tick, revenue=self.latest_revenue)
            return good
        else:
            return False

    def adjust_price(self):
        # Take all sales except last one
        sales = list(self.stats.sales.values())[:-1][-4:]
        demand = list(self.stats.demand.values())[:-1][-4:]

        sum_sales = sum(sales)
        sum_demand = sum(demand)

        if sum_demand == 0:
            # Nobody wanted to buy → price too high
            self.current_price *= 0.9  # lower 10%
        elif sum_sales < sum_demand:
            # More demand than sales → stock-out
            self.current_price *= 1.05  # raise 5%
        else:
            # sales == demand → balanced
            pass

        return self.current_price

    def reivew_hiring(self) -> None:
        employees = len(self.employees)
        # Calculate maximum production
        max_production = employees * self.ppe
        # Check if max production is greater than demand
        if max_production >= self.latest_demand:
            self.hiring = False
        else:
            self.hiring = True

    def produce_goods(self) -> None:

        # TODO: production should cost money!
        # but for now lets just use salary!

        fulfill = self.latest_demand - len(self.goods)
        capacity = self.ppe * len(self.employees)

        actual_produce = math.ceil(min(fulfill, capacity))

        produced = 0
        for _ in range(actual_produce):
            self.goods.append(Good(price=self.current_price))
            produced += 1

        # Reseet demand for next tick
        self.latest_demand = 0
        self.stats.record(self.tick, production=produced)

    def one_tick(self, tick: int):

        self.set_tick(tick)
        self.initialize_tick_stats()
        self.produce_goods()
        self.pay_salaries()
        if self.tick > 4:
            self.finance_action()

    def clean_up(self) -> None:
        self.stats.record(self.tick, profit=self.latest_revenue - self.latest_costs)
        self.latest_sales = 0
        self.latest_costs = 0
        self.latest_revenue = 0

    def initialize_tick_stats(self):

        self.stats.set_tick(self.tick)

        defaults = {
            "sales": 0,
            "demand": 0,
            "production": 0,
            "price": self.current_price,
            "salary": self.salary,
            "hiring": self.hiring,
            "ppe": self.ppe,
            "revenue": 0,
            "costs": self.latest_costs,
            "profit": 0,
            "overstock": len(self.goods),
        }

        for stat_name, default_value in defaults.items():
            if self.tick not in getattr(self.stats, stat_name):
                getattr(self.stats, stat_name)[self.tick] = default_value  #
