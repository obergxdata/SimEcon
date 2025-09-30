import pytest
from agents.person import Person
from agents.corporation import Corporation, Good
from banking.agents.bank import Bank
from banking.agents.central_bank import CentralBank
from banking.bank_interface import BankInterface
from logging_config import get_logger

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


def test_review_price() -> None:
    # NOTE price changes are based on the previous tick
    # 3 = current tick, 2 = previous tick
    # Demand > sales
    corporation = Corporation()
    corporation.set_tick(3)
    corporation.latest_price = 100
    corporation.stats.sales = {0: 100, 1: 100, 2: 125, 3: 0}
    corporation.stats.demand = {0: 100, 1: 150, 2: 150, 3: 0}
    corporation.review_price()
    assert corporation.latest_price == 120

    # Demand < sales
    corporation = Corporation()
    corporation.set_tick(3)
    corporation.latest_price = 100
    corporation.stats.sales = {0: 100, 1: 100, 2: 125, 3: 0}
    corporation.stats.demand = {0: 100, 1: 150, 2: 100, 3: 0}
    corporation.review_price()
    assert corporation.latest_price == 80

    # Demand = sales
    corporation = Corporation()
    corporation.set_tick(3)
    corporation.latest_price = 100
    corporation.stats.sales = {0: 100, 1: 100, 2: 125, 3: 0}
    corporation.stats.demand = {0: 100, 1: 150, 2: 125, 3: 0}
    corporation.review_price()
    assert corporation.latest_price == 100


def test_produce_goods() -> None:
    corporation = Corporation()
    corporation.latest_price = 10
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
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
    corporation.bank_interface = BankInterface(Bank(CentralBank()), corporation)
    person = Person()
    person.bank_interface = BankInterface(Bank(CentralBank()), person)
    corporation.add_employee(person)
    wtid, dtid = corporation.pay_salary(person)
    assert person.latest_salary_id == dtid
    assert person.bank_interface.check_balance() == corporation.salary
    assert (
        corporation.bank_interface.find_transaction(wtid).amount == corporation.salary
    )
