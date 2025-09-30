from banking.bank_interface import BankInterface
from banking.agents.bank import Bank
from typing import Union
from agents.corporation import Corporation, Good
from base_agent import BaseAgent
import random


class Person(BaseAgent):

    def __init__(self, bank: Union[Bank, None] = None) -> None:
        super().__init__("Person")  # Initialize BaseAgent with Person prefix
        self.bank_interface = BankInterface(bank, self) if bank else None
        self.bought_goods: list[Good] = []
        self.mpc: float = 0.5
        self.latest_spending: int = 0
        self.employed: bool = False
        self.latest_salary_id: str = ""

    def choose_corporations(self, corps: list[Corporation]):
        # return one corporation at random
        # with inverse price as weight
        corp = random.choices(
            corps, weights=[1 / corp.latest_price for corp in corps], k=1
        )[0]
        return corp

    def purchase_queue(self, corps: list[Corporation], budget: int):
        # Generate a list of to purchase goods from
        # as long as budget allows
        queue = []
        while budget > 0:
            # Check if any corporation has affordable goods
            if not any(corp.latest_price <= budget for corp in corps):
                break
            corp = self.choose_corporations(corps)
            if corp.latest_price <= budget:
                budget -= corp.latest_price
                corp.register_demand(1)
                queue.append(corp)

        return queue

    def buy_goods(self, corps: list[Corporation], budget: int) -> int:
        queue = self.purchase_queue(corps, budget)
        bought = 0
        for corp in queue:
            good = corp.sell_good(self.bank_interface)
            if good:
                bought += 1
                self.bought_goods.append(good)
                self.latest_spending += good.price

        return bought

    def spend(self, corps: list[Corporation], tid: Union[str, None] = None) -> int:
        # TODO: find a way to trigger sell good even if the corporation has no inventory
        # so that we can register demand
        if not tid:
            tid = self.latest_salary_id

        budget_ref = self.bank_interface.find_transaction(tid).amount
        balance = self.bank_interface.check_balance()

        if balance == 0:
            raise Exception("account balance is 0")
        elif balance < 0:
            raise Exception("account balance is negative")

        # How much should the customer spend?
        budget = budget_ref * self.mpc
        return self.buy_goods(corps=corps, budget=int(budget))

    def pay_loans(self) -> None:
        pass

    def apply_for_loan(self) -> None:
        pass

    def clean_up(self) -> None:
        # Calculations
        self.latest_spending = 0
