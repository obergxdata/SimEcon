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


@dataclass
class CorpStats(BaseStats):
    sales: dict[int, float] = field(default_factory=dict)
    revenue: dict[int, float] = field(default_factory=dict)
    profit: dict[int, float] = field(default_factory=dict)
    costs: dict[int, float] = field(default_factory=dict)
    demand: dict[int, float] = field(default_factory=dict)
    production: dict[int, float] = field(default_factory=dict)
    price: dict[int, float] = field(default_factory=dict)
    salary: dict[int, float] = field(default_factory=dict)
    hiring: dict[int, bool] = field(default_factory=dict)
    ppe: dict[int, int] = field(default_factory=dict)


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

    def review_salary(self, min_wage: float = 0) -> None:
        # Increase salary by the average sales increase/decrease
        # for the last 6 sales values

        # Take all sales except last one
        sales = list(self.stats.sales.values())[:-1]
        last_6_sales = sales[-6:]

        if len(last_6_sales) < 2:
            return  # Need at least 2 data points to calculate change

        # Calculate the differences between consecutive periods
        changes = []
        for i in range(1, len(last_6_sales)):
            change = last_6_sales[i] - last_6_sales[i - 1]
            changes.append(change)

        # Average change across the periods
        average_change = sum(changes) / len(changes)

        # Ensure salary is at least the minimum wage
        if self.salary + average_change < min_wage:
            self.salary = min_wage
        else:
            self.salary += average_change

        if self.salary <= 0:
            raise Exception(last_6_sales)

        self.stats.record(self.tick, salary=self.salary)

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

    def revenue_trend(self) -> float:
        revenue = list(self.stats.revenue.values())[-4:]
        if len(revenue) < 4:
            return 0.0  # not enough data

        recent = revenue[-4:]
        first_half = np.mean(recent[: 4 // 2])
        second_half = np.mean(recent[4 // 2 :])

        if first_half == 0:
            return 0.0

        return (second_half - first_half) / first_half

    def review_finance(self):
        result = self.recommend_finance_action()
        if result["status"] == "borrow_funds":
            loan = self.bank_interface.borrow_funds(result["amount"])
            self.loans.append(loan)
        elif result["status"] == "cost_savings":
            self.cost_savings(result["amount"])

    def recommend_finance_action(self, target_runway: float = 6) -> dict:

        if self.tick < 4:
            raise Exception("Not enough data to review finance")

        runway, burn, net_margin = self.forecast()
        trend = self.revenue_trend()
        balance = self.bank_interface.check_balance()

        monthly_burn = burn / 4 if burn > 0 else 0

        result = {"status": "monitor", "amount": None}

        if net_margin > 0:
            result["status"] = "healthy"
            return result

        if monthly_burn > 0:
            if runway < 3:
                if trend > 0:
                    result["status"] = "borrow_funds"
                    # Borrow enough to reach target runway
                    result["amount"] = round((target_runway - runway) * monthly_burn, 2)
                else:
                    result["status"] = "cost_savings"
                    # Calculate how much monthly burn to reduce
                    new_burn = balance / target_runway
                    result["amount"] = round(monthly_burn - (new_burn / 4), 2)
            elif runway < target_runway:
                result["status"] = "monitor"

        return result

    def forecast(self):

        if self.tick < 4:
            raise Exception("Not enough data to forecast")

        balance = self.bank_interface.check_balance()
        costs = list(self.stats.costs.values())[-4:]
        revenue = list(self.stats.revenue.values())[-4:]

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

    def cost_savings(self, save):
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
        sales = list(self.stats.sales.values())[:-1]
        demand = list(self.stats.demand.values())[:-1]

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

    def one_tick(self, tick: int, min_wage: float):

        self.set_tick(tick)
        self.initialize_tick_stats()
        self.produce_goods()
        self.pay_salaries()
        if self.tick > 1:
            self.adjust_price()
            self.review_salary(min_wage)
        if self.tick > 4:
            self.review_finance()

    def clean_up(self) -> None:
        self.stats.record(self.tick, profit=self.latest_revenue - self.latest_costs)
        self.latest_sales = 0
        self.latest_costs = 0
        self.latest_revenue = 0

    def initialize_tick_stats(self):
        """Ensure all stats have entries for the current tick with default values"""
        defaults = {
            "sales": None,
            "demand": None,
            "production": 0,
            "price": self.current_price,
            "salary": self.salary,
            "hiring": self.hiring,
            "ppe": self.ppe,
            "revenue": self.latest_revenue,
            "costs": self.latest_costs,
            "profit": self.latest_revenue - self.latest_costs,
        }

        for stat_name, default_value in defaults.items():
            if self.tick not in getattr(self.stats, stat_name):
                getattr(self.stats, stat_name)[self.tick] = default_value
