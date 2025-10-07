import pytest
from agents.person import Person
from agents.corporation import Corporation, Good
from banking.agents.bank import Bank
from banking.agents.central_bank import CentralBank
from banking.bank_interface import BankInterface
from logging_config import get_logger
import numpy as np
import math

logger = get_logger(__name__)


def test_person_spend():
    person = Person()
    central_bank = CentralBank()
    bank = Bank(central_bank)
    bank_2 = Bank(central_bank)
    person.bank = bank
    person.bank_interface = BankInterface(bank, person)
    tid = person.bank_interface.deposit(100)

    corporation = Corporation()
    corporation.current_price = 10
    corporation.bank_interface = BankInterface(bank_2, corporation)
    for _ in range(10):
        corporation.goods.append(Good(price=10))

    bought = person.spend([corporation], tid)
    assert bought == 5

    assert len(person.bought_goods) == 5
    assert len(corporation.goods) == 5
    assert person.bank_interface.check_balance() == 50
    assert corporation.bank_interface.check_balance() == 50


def test_change_salary() -> None:
    corporation = Corporation()
    corporation.salary = 100
    corporation.change_salary(pct=0.03)
    assert corporation.salary == 103
    corporation.salary = 100
    corporation.change_salary(pct=-0.03)
    assert corporation.salary == 97


"""
@pytest.mark.parametrize(
    "sales, demand, start_price, expected_factor",
    [
        # Case 1: Price too high → no demand → lower price
        ({0: 0}, {0: 0}, 100, 0.9),
        # Case 2: Stock-out (more demand than sales) → raise price
        ({0: 80}, {0: 100}, 100, 1.05),
        # Case 3: Perfect balance → no change
        ({0: 100}, {0: 100}, 100, 1.0),
    ],
)
def test_adjust_price(sales, demand, start_price, expected_factor):
    corp = Corporation()
    corp.stats.sales = sales
    corp.stats.demand = demand
    corp.current_price = start_price

    new_price = corp.adjust_price()
    expected_price = start_price * expected_factor

    assert math.isclose(new_price, expected_price, rel_tol=1e-9)
"""


def test_produce_goods() -> None:
    corporation = Corporation()
    corporation.current_price = 10
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    corporation.bank_interface.deposit(1010)
    corporation.latest_demand = 100
    corporation.ppe = 3
    corporation.salary = 100

    for _ in range(10):
        person = Person()
        person.mpc = 0.5
        person.bank_interface = BankInterface(Bank(CentralBank()), person)
        corporation.add_employee(person)

    corporation.set_tick(1)
    corporation.initialize_tick_stats()
    corporation.produce_goods()
    corporation.pay_salaries()
    assert corporation.bank_interface.check_balance() == 10

    for person in corporation.employees:
        person.spend([corporation], person.latest_salary_id)

    stats = corporation.stats.get_latest()
    assert stats["sales"] == 30
    assert stats["demand"] == 50
    assert stats["production"] == 30
    assert stats["price"] == 10
    assert stats["salary"] == 100
    assert stats["hiring"] == True


def test_review_hiring() -> None:
    corporation = Corporation()
    corporation.ppe = 10
    corporation.latest_demand = 100
    corporation.reivew_hiring()
    assert corporation.hiring == True

    # generate some people
    for _ in range(9):
        corporation.add_employee(Person())
    corporation.reivew_hiring()
    assert corporation.hiring == True

    # Add one more person
    corporation.add_employee(Person())
    corporation.reivew_hiring()
    assert corporation.hiring == False


def test_pay_salary() -> None:
    corporation = Corporation()
    corporation.salary = 100
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    corporation.bank_interface.deposit(100)
    person = Person()
    person.bank_interface = BankInterface(Bank(CentralBank()), person)
    corporation.add_employee(person)
    wtid, dtid = corporation.pay_salary(person)
    assert person.latest_salary_id == dtid
    assert person.bank_interface.check_balance() == corporation.salary
    assert (
        corporation.bank_interface.find_transaction(wtid).amount == corporation.salary
    )


@pytest.mark.parametrize(
    "deposit, costs, revenue, sales, expected",
    [
        # We are making money and the trend is positive
        # Sales trend is positive
        (
            100,
            {0: 100, 1: 100, 2: 100, 3: 100},
            {0: 100, 1: 100, 2: 100, 3: 100},
            {0: 100, 1: 100, 2: 125, 3: 125},
            ("increase_price", 0),
        ),
        # We are making money and the trend is positive
        # Sales trend is negative
        (
            100,
            {0: 100, 1: 100, 2: 100, 3: 100},
            {0: 100, 1: 100, 2: 100, 3: 100},
            {0: 100, 1: 100, 2: 80, 3: 80},
            ("lower_price", 0),
        ),
        # We are making money but the trend is negative
        (
            100,
            {0: 50, 1: 50, 2: 50, 3: 50},
            {0: 100, 1: 95, 2: 80, 3: 80},
            {},
            ("lower_salary", 0),
        ),
        # We are losing money and the trend is positive
        (
            100,
            {0: 100, 1: 100, 2: 120, 3: 155},
            {0: 95, 1: 95, 2: 105, 3: 120},
            {},
            ("borrow_funds", 12.5),
        ),
        # We are losing money and the trend is negative and we have less than 3 months of runway
        (
            100,
            {0: 100, 1: 100, 2: 120, 3: 155},
            {0: 95, 1: 95, 2: 85, 3: 55},
            {},
            ("fire_employees", 42.5),
        ),
        # We are losing money and the trend is negative but we have more than 3 months of runway
        (
            5000,
            {0: 100, 1: 100, 2: 120, 3: 155},
            {0: 95, 1: 95, 2: 85, 3: 55},
            {},
            ("lower_salary", 0),
        ),
    ],
)
def test_finance_recommendation(deposit, costs, revenue, sales, expected) -> None:
    corporation = Corporation()
    corporation.set_tick(4)
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    corporation.bank_interface.deposit(deposit)
    corporation.stats.costs = costs
    corporation.stats.revenue = revenue
    corporation.stats.sales = sales
    recommendation = corporation.finance_recommendation(allow_borrow=True)
    assert recommendation == expected
