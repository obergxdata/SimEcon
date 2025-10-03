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


@dataclass
class CorpStats(BaseStats):
    sales: dict[int, float] = field(default_factory=dict)
    revenue: dict[int, float] = field(default_factory=dict)
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
        self.latest_price: float = 0
        self.latest_revenue: float = 0
        self.latest_costs: float = 0
        self.hiring: bool = True
        self.ppe: int = 0
        self.alive = True

    def review_salary(self, min_wage: float = 0) -> None:
        # Increase salary by the average sales increase/decrease
        # for the last 6 sales values
        last_6_sales = list(self.stats.sales.values())[-6:]

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
            self._log(
                f"Salary is below minimum wage, setting to {min_wage}", level="warning"
            )
            self.salary = min_wage
        else:
            self.salary += average_change

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
        wtid, dtid = self.bank_interface.transfer(
            self.salary, to=employee.bank_interface
        )
        self.latest_costs += self.salary
        self.stats.record(self.tick, costs=self.latest_costs)

        employee.latest_salary_id = dtid
        return wtid, dtid

    def revenue_trend(self, months: int = 6) -> float:
        revenue = list(self.stats.revenue.values())[-months:]
        if len(revenue) < months:
            return 0.0  # not enough data

        recent = revenue[-months:]
        first_half = np.mean(recent[: months // 2])
        second_half = np.mean(recent[months // 2 :])

        if first_half == 0:
            return 0.0

        return (second_half - first_half) / first_half

    def apply_finance_decision(self, decision: str):
        pass

    def review_finance(self):
        runway, burn, net_margin = self.forecast()
        trend = self.revenue_trend(months=6)
        if net_margin > 0:
            return "healthy"
        elif burn > 0 and runway < 3:
            if trend > 0:
                return "borrow_funds"
            else:
                return "cost_savings"
        elif burn > 0 and runway < 6:
            return "monitor"
        else:
            return "monitor"

    def forecast(self):
        balance = self.bank_interface.check_balance()
        costs = list(self.stats.costs.values())[-3:]
        revenue = list(self.stats.revenue.values())[-3:]

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
            bank_interface.transfer(self.latest_price, to=self.bank_interface)
            good = self.goods.pop(0)
            self.latest_sales += 1
            self.latest_revenue += self.latest_price
            self.stats.record(self.tick, sales=self.latest_sales)
            self.stats.record(self.tick, revenue=self.latest_revenue)
            return good
        else:
            return False

    def adjust_price(self):
        sales = sum(self.stats.sales.values())
        demand = sum(self.stats.demand.values())

        if demand == 0:
            # Nobody wanted to buy → price too high
            self.latest_price *= 0.9  # lower 10%
        elif sales < demand:
            # More demand than sales → stock-out
            self.latest_price *= 1.05  # raise 5%
        else:
            # sales == demand → balanced
            pass

        return self.latest_price

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

        produce = self.latest_demand - len(self.goods)
        capacity = self.ppe * len(self.employees)

        produced = 0
        for _ in range(produce):
            if produced >= capacity or produced == produce:
                break
            self.goods.append(Good(price=self.latest_price))
            produced += 1

        self._log(f"Produced {produced} goods for {self.name}")

        # Reseet demand for next tick
        self.latest_demand = 0
        self.stats.record(self.tick, production=produced)

    def clean_up(self) -> None:
        self.latest_sales = 0

    def initialize_tick_stats(self):
        """Ensure all stats have entries for the current tick with default values"""
        defaults = {
            "sales": 0,
            "demand": 0,
            "production": 0,
            "price": self.latest_price,
            "salary": self.salary,
            "hiring": self.hiring,
            "ppe": self.ppe,
        }

        for stat_name, default_value in defaults.items():
            if self.tick not in getattr(self.stats, stat_name):
                getattr(self.stats, stat_name)[self.tick] = default_value
