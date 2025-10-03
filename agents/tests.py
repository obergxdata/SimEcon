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
    corporation.latest_price = 10
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
    corp.latest_price = start_price

    new_price = corp.adjust_price()
    expected_price = start_price * expected_factor

    assert math.isclose(new_price, expected_price, rel_tol=1e-9)


def test_produce_goods() -> None:
    corporation = Corporation()
    corporation.latest_price = 10
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
    "revenue, months, expected",
    [
        # Not enough data → 0.0
        ({0: 100}, 3, 0.0),
        # Increasing
        # last 3 months: [200, 300, 400]
        # first_half = 200, second_half = 350 → (350-200)/200 = 0.75
        ({0: 100, 1: 200, 2: 300, 3: 400}, 3, 0.75),
        # Decreasing
        # last 3 months: [300, 200, 100]
        # first_half = 300, second_half = 150 → (150-300)/300 = -0.5
        ({0: 400, 1: 300, 2: 200, 3: 100}, 3, -0.5),
        # Flat → 0
        ({0: 100, 1: 100, 2: 100, 3: 100}, 3, 0.0),
        # Divide by zero in first_half → 0
        ({0: 0, 1: 0, 2: 0, 3: 100}, 3, 0.0),
        # Your example: [200, 150, 100] → (125-200)/200 = -0.375
        ({0: 100, 1: 200, 2: 150, 3: 100}, 3, -0.375),
    ],
)
def test_revenue_trend(revenue, months, expected):
    corp = Corporation()
    corp.stats.revenue = revenue
    result = corp.revenue_trend(months=months)
    assert np.isclose(result, expected)


@pytest.mark.parametrize(
    "balance, costs, revenue, expected",
    [
        # Case 1: Profitable (revenue > costs)
        # burn=0, net_margin=300-200=100, runway=inf
        (1000, {0: 100, 1: 100}, {0: 100, 1: 200}, (float("inf"), 0, 100)),
        # Case 2: Loss-making, positive runway
        # costs=300, revenue=150 → burn=150, net_margin=-150
        # runway=600/150=4
        (600, {0: 100, 1: 200}, {0: 50, 1: 100}, (4.0, 150, -150)),
        # Case 3: Break-even
        # costs=200, revenue=200 → burn=0, net_margin=0 → runway=inf
        (500, {0: 100, 1: 100}, {0: 150, 1: 50}, (float("inf"), 0, 0)),
        # Case 4: High burn, short runway
        # costs=500, revenue=200 → burn=300, net_margin=-300
        # runway=900/300=3
        (900, {0: 200, 1: 300}, {0: 100, 1: 100}, (3.0, 300, -300)),
    ],
)
def test_forecast(balance, costs, revenue, expected):
    corp = Corporation()
    corp.bank_interface = BankInterface(Bank(CentralBank()), corp)
    corp.bank_interface.deposit(balance)
    corp.stats.costs = costs
    corp.stats.revenue = revenue

    runway, burn, net_margin = corp.forecast()

    exp_runway, exp_burn, exp_margin = expected

    if exp_runway == float("inf"):
        assert runway == float("inf")
    else:
        assert np.isclose(runway, exp_runway)

    assert burn == exp_burn
    assert net_margin == exp_margin


@pytest.mark.parametrize(
    "balance, costs, revenue, expected",
    [
        # Case 1: Profitable (revenue > costs)
        # burn=0, net_margin=300-200=100, runway=inf
        (1000, {0: 100, 1: 100}, {0: 100, 1: 200}, (float("inf"), 0, 100)),
        # Case 2: Loss-making, positive runway
        # costs=300, revenue=150 → burn=150, net_margin=-150
        # runway=600/150=4
        (600, {0: 100, 1: 200}, {0: 50, 1: 100}, (4.0, 150, -150)),
        # Case 3: Break-even
        # costs=200, revenue=200 → burn=0, net_margin=0 → runway=inf
        (500, {0: 100, 1: 100}, {0: 150, 1: 50}, (float("inf"), 0, 0)),
        # Case 4: High burn, short runway
        # costs=500, revenue=200 → burn=300, net_margin=-300
        # runway=900/300=3
        (900, {0: 200, 1: 300}, {0: 100, 1: 100}, (3.0, 300, -300)),
    ],
)
def test_forecast(balance, costs, revenue, expected):
    corp = Corporation()
    corp.bank_interface = BankInterface(Bank(CentralBank()), corp)
    corp.bank_interface.deposit(balance)
    corp.stats.costs = costs
    corp.stats.revenue = revenue

    runway, burn, net_margin = corp.forecast()

    exp_runway, exp_burn, exp_margin = expected

    if exp_runway == float("inf"):
        assert runway == float("inf")
    else:
        assert np.isclose(runway, exp_runway)

    assert burn == exp_burn
    assert net_margin == exp_margin


@pytest.mark.parametrize(
    "balance, costs, revenue, expected",
    [
        # Case 1: Profitable → Healthy
        # costs=200, revenue=400 → net_margin=+200
        (1000, {0: 100, 1: 100}, {0: 200, 1: 200}, "healthy"),
        # Case 2: Loss, runway < 3, trend > 0 → take_loan
        # costs=1000, revenue=900 → burn=100, runway=200/100=2 (<3)
        (
            200,
            {0: 400, 1: 600},  # costs = 1000
            {0: 100, 1: 150, 2: 200, 3: 250, 4: 300, 5: 350},  # increasing 6 months
            "borrow_funds",
        ),
        # Case 3: Loss, runway < 3, trend <= 0 → cost_savings
        # costs=1000, revenue=900 → burn=100, runway=200/100=2 (<3)
        (
            200,
            {0: 400, 1: 600},
            {0: 400, 1: 300, 2: 200, 3: 100},  # decreasing → trend <0
            "cost_savings",
        ),
        # Case 4: Loss, runway between 3 and 6 → monitor
        # costs=600, revenue=300 → burn=300, runway=1200/300=4
        (1200, {0: 200, 1: 200, 2: 200}, {0: 100, 1: 100, 2: 100}, "monitor"),
        # Case 5: Loss, runway ≥6 → monitor
        # costs=600, revenue=300 → burn=300, runway=3000/300=10
        (3000, {0: 200, 1: 200, 2: 200}, {0: 100, 1: 100, 2: 100}, "monitor"),
    ],
)
def test_review_finance(balance, costs, revenue, expected):
    corp = Corporation()
    corp.bank_interface = BankInterface(Bank(CentralBank()), corp)

    # Set bank balance
    corp.bank_interface.deposit(balance)

    # Set stats
    corp.stats.costs = costs
    corp.stats.revenue = revenue

    assert corp.review_finance() == expected
