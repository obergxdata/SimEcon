from typing import TYPE_CHECKING, Set, Union
from banking.bank_interface import BankInterface
from dataclasses import dataclass, field
from base_agent import BaseAgent, BaseStats


if TYPE_CHECKING:
    from .person import Person
    from banking.agents.bank import Bank
    from banking.bank_interface import BankInterface


@dataclass
class CorpStats(BaseStats):
    sales: dict[int, float] = field(default_factory=dict)
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
        self.hiring: bool = True
        self.ppe: int = 0

    def review_salary(self) -> None:
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
        self.salary += average_change
        self.stats.record(self.tick, salary=self.salary)

    def add_employee(self, employee: "Person") -> None:
        employee.employed = True
        employee.salary = self.salary
        self.employees.add(employee)
        self.reivew_hiring()

    def remove_employee(self, employee: "Person") -> None:
        self.employees.remove(employee)

    def pay_salary(self, employee: "Person") -> None:
        wtid, dtid = self.bank_interface.transfer(
            self.salary, to=employee.bank_interface
        )
        employee.latest_salary_id = dtid
        return wtid, dtid

    def pay_salaries(self) -> None:
        total_salaries = 0
        pay_count = 0
        for employee in self.employees:
            if employee.bank_interface.check_balance() > 0:
                self.pay_salary(employee)
                total_salaries += self.salary
                pay_count += 1
            else:
                # If credit denied from bank, use goverment salary guarantee!
                pass  # TODO: Take loan? Also salary guarantee!

        self._log(
            f"Paid {total_salaries} to {pay_count} employees, left {self.bank_interface.check_balance()}"
        )

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
            self.stats.record(self.tick, sales=self.latest_sales)
            return good
        else:
            return False

    def review_price(self) -> None:

        if self.tick < 1:
            raise Exception("Tick is less than 1")

        latest_sales = self.stats.sales[self.tick - 1]
        latest_demand = self.stats.demand[self.tick - 1]

        if latest_sales == 0 or latest_demand == 0:
            return
        # Increase or decrease price by the difference between demand and sales
        price_change = (latest_demand - latest_sales) / latest_sales
        self.latest_price += price_change * self.latest_price
        self.stats.record(self.tick, price=self.latest_price)

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
