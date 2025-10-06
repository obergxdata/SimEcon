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


def test_review_salary() -> None:
    # Test flat sales - no change
    # corporation = Corporation()
    # corporation.salary = 100
    # corporation.stats.sales = {0: 100, 1: 100, 2: 100, 3: 100, 4: 100, 5: 100}
    # corporation.review_salary()
    # assert corporation.salary == 100

    # Test with increasing then decreasing sales
    # Changes: [200-100, 150-200] = [100, -50], average = 25
    corporation = Corporation()
    corporation.salary = 100
    corporation.stats.sales = {0: 100, 1: 200, 2: 150}
    corporation.review_salary()
    assert corporation.salary == 125

    # Test with more data points
    # Changes: [200-100, 150-200, 100-150] = [100, -50, -50], average = 0
    corporation = Corporation()
    corporation.salary = 100
    corporation.stats.sales = {0: 100, 1: 200, 2: 150, 3: 100}
    corporation.review_salary()
    assert corporation.salary == 100

    # Test with decreasing sales
    # Changes: [150-200, 100-150] = [-50, -50], average = 50
    corporation = Corporation()
    corporation.salary = 100
    corporation.stats.sales = {0: 200, 1: 150, 2: 100}
    corporation.review_salary()
    assert corporation.salary == 50


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
    "revenues, expected",
    [
        # Increasing
        ([100, 150, 200, 250], 0.8),
        # Decreasing
        ([250, 200, 150, 100], -0.4444444444444444),
        # Flat
        ([100, 100, 100, 100], 0.0),
        # Slight increase
        ([100, 110, 120, 130], 0.19047619047619047),
        # Slight decrease
        ([130, 120, 110, 100], -0.16),
        # Not enough data (<4) → 0.0
        ([100, 200, 300], 0.0),
        # First half mean is zero → 0.0 by function guard
        ([0, 0, 10, 10], 0.0),
    ],
)
def test_revenue_trend(revenues, expected) -> None:
    corporation = Corporation()
    corporation.set_tick(4)
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    corporation.bank_interface.deposit(100)

    corporation.stats.revenue = {i: v for i, v in enumerate(revenues)}

    result = corporation.revenue_trend()
    assert result == pytest.approx(expected, rel=1e-9, abs=1e-9)


@pytest.mark.parametrize(
    "deposit, costs, revenue, expected_runway, expected_burn, expected_net_margin",
    [
        # 1) Profitable → burn = 0, runway = inf
        (1000, [100, 100, 100, 100], [200, 200, 200, 200], math.inf, 0, 400),
        # 2) Breakeven → burn = 0, runway = inf
        (1000, [200, 200, 200, 200], [200, 200, 200, 200], math.inf, 0, 0),
        # 3) Loss → finite runway = balance / burn
        (
            1000,
            [300, 300, 300, 300],
            [200, 200, 200, 200],
            pytest.approx(2.5, rel=1e-12),
            400,
            -400,
        ),
        # 4) Loss with non-round numbers
        (
            500,
            [150, 200, 250, 300],
            [100, 150, 200, 220],
            pytest.approx(500 / 230, rel=1e-12),
            230,
            -230,
        ),
        # 5) Loss, zero balance → runway = 0
        (0, [100, 100, 100, 100], [50, 50, 50, 50], 0.0, 200, -200),
        # 6) Fewer than 4 months → uses whatever is present
        (1000, [300, 100], [100, 200], pytest.approx(10.0, rel=1e-12), 100, -100),
    ],
)
def test_forecast(
    deposit, costs, revenue, expected_runway, expected_burn, expected_net_margin
):
    corporation = Corporation()
    corporation.set_tick(4)
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    corporation.bank_interface.deposit(deposit)

    corporation.stats.costs = {i: v for i, v in enumerate(costs)}
    corporation.stats.revenue = {i: v for i, v in enumerate(revenue)}

    runway, burn, net_margin = corporation.forecast()

    assert runway == expected_runway
    assert burn == expected_burn
    assert net_margin == expected_net_margin


import pytest


@pytest.mark.parametrize(
    "deposit, costs, revenue, expected_status, expected_amount",
    [
        # 1) Profitable → "healthy"
        (1000, [100, 100, 100, 100], [200, 200, 200, 200], "healthy", None),
        # 2) Losing money, short runway (<3), positive trend → "borrow_funds"
        # burn = (1200 - 700) = 500 over 4m → monthly_burn = 125
        # runway = 200 / 500 = 0.4
        # amount = (6 - 0.4) * 125 = 700.00
        (
            200,
            [300, 300, 300, 300],
            [100, 150, 200, 250],
            "borrow_funds",
            pytest.approx(700.00, rel=1e-12, abs=1e-12),
        ),
        # 3) Losing money, short runway (<3), non-positive trend → "cost_savings"
        # same burn as above → monthly_burn = 125, runway = 0.4
        # new_burn = balance / target_runway = 200 / 6 = 33.333...
        # amount = monthly_burn - (new_burn / 4) = 125 - 8.333... = 116.67
        (
            200,
            [300, 300, 300, 300],
            [250, 200, 150, 100],
            "cost_savings",
            pytest.approx(116.67, rel=1e-12, abs=1e-12),
        ),
        # 4) Losing money, runway between 3 and 6 → "monitor"
        # burn = 1200 - 1000 = 200; runway = 700 / 200 = 3.5
        (700, [300, 300, 300, 300], [250, 250, 250, 250], "monitor", None),
        # 5) Breakeven (burn = 0) → "monitor"
        (1000, [200, 200, 200, 200], [200, 200, 200, 200], "monitor", None),
        # 6) Losing money but long runway (>= target_runway) → "monitor"
        # burn = 200; runway = 2000 / 200 = 10
        (2000, [300, 300, 300, 300], [250, 250, 250, 250], "monitor", None),
    ],
)
def test_recommend_finance_action(
    deposit, costs, revenue, expected_status, expected_amount
):
    corp = Corporation()
    corp.set_tick(4)
    corp.bank_interface = BankInterface(Bank(CentralBank()), corp)
    corp.bank_interface.deposit(deposit)

    corp.stats.costs = {i: v for i, v in enumerate(costs)}
    corp.stats.revenue = {i: v for i, v in enumerate(revenue)}

    result = corp.recommend_finance_action()  # target_runway defaults to 6

    assert result["status"] == expected_status
    assert result["amount"] == expected_amount
