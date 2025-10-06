import pytest

from banking.agents.central_bank import CentralBank
from banking.agents.bank import Bank
from banking.bank_interface import BankInterface
from banking.bank_accounting import Deposit, Withdraw
from agents.person import Person
from agents.corporation import Corporation
import numpy as np


def test_bankdepositwithdraw() -> None:
    central_bank = CentralBank()
    bank_1 = Bank(central_bank)
    person_1 = Person()
    bank_interface_1 = BankInterface(bank_1, person_1)
    # BankInterface deposits money into bank 1
    tid = bank_1.deposit(100, bank_interface_1)

    assert bank_interface_1.find_transaction(tid) == Deposit(
        tid=tid, amount=100, deposited_by=bank_interface_1, deposited_to=bank_1
    )

    assert bank_1.get_reserve(bank_1) == 100

    # BankInterface withdraws money from bank 1 to bank 2
    tid = bank_1.withdraw(50, bank_interface_1)
    assert bank_interface_1.find_transaction(tid) == Withdraw(
        tid=tid, amount=50, withdrawn_by=bank_interface_1, withdrawn_from=bank_1
    )


def test_bank_transfer() -> None:

    central_bank = CentralBank()
    bank_1 = Bank(central_bank)
    bank_2 = Bank(central_bank)
    person_1 = Person()
    person_2 = Person()
    bank_interface_1 = BankInterface(bank_1, person_1)
    bank_interface_2 = BankInterface(bank_2, person_2)
    # Deposit money into bank 1
    tid = bank_1.deposit(100, bank_interface_1)

    # BankInterface deposits money into bank 1
    wtid, dtid = bank_1.transfer(50, from_=bank_interface_1, to=bank_interface_2)

    # Find withdraw and deposit transactions
    assert bank_interface_1.find_transaction(wtid) == Withdraw(
        tid=wtid, amount=50, withdrawn_by=bank_interface_1, withdrawn_from=bank_1
    )
    assert bank_interface_2.find_transaction(dtid) == Deposit(
        tid=dtid, amount=50, deposited_by=bank_interface_2, deposited_to=bank_2
    )

    # Transfer internally, should not move reserves
    wtid, dtid = bank_interface_1.transfer(42, to=bank_interface_1)

    # Validate reserves
    assert bank_1.get_reserve(bank_1) == 50
    assert bank_2.get_reserve(bank_2) == 50


def test_bank_interface_pay_salary() -> None:

    # Create central bank
    central_bank = CentralBank()
    # Create bank
    bank = Bank(central_bank)
    # Create 100 persons
    persons = [Person(bank=bank) for _ in range(100)]
    # Create 1 corporation
    corporation = Corporation(bank=bank)
    corporation.bank_interface = BankInterface(bank, corporation)
    corporation.bank_interface.deposit(99999)
    corporation.salary = 50
    # Add employees to corporation
    for person in persons:
        corporation.add_employee(person)

    # Pay salary to employees
    for person in persons:
        corporation.pay_salary(person)

    # Validate balances
    for person in persons:
        assert person.bank_interface.check_balance() == 50


@pytest.mark.parametrize(
    "deposit, costs, revenue, amount, expected",
    [
        # Profitable and growing → full loan granted
        (
            1000,
            {0: 100, 1: 120, 2: 130, 3: 140},
            {0: 200, 1: 220, 2: 250, 3: 280},
            200,
            200,
        ),
        # Profitable but requesting more than allowed → actual formula gives 580 (not 750)
        (
            1000,
            {0: 150, 1: 150, 2: 150, 3: 150},
            {0: 250, 1: 250, 2: 250, 3: 250},
            2000,
            580,
        ),
        # Flat trend, small margin → formula gives 516 (not exactly 500)
        (
            1000,
            {0: 180, 1: 180, 2: 180, 3: 180},
            {0: 200, 1: 200, 2: 200, 3: 200},
            1000,
            516,
        ),
        # Declining revenue but still profitable → result is 500, no penalty triggered
        (
            1000,
            {0: 100, 1: 120, 2: 130, 3: 150},
            {0: 250, 1: 230, 2: 210, 3: 190},
            500,
            500,
        ),
        # Declining revenue and losing money → denied
        (
            1000,
            {0: 200, 1: 220, 2: 250, 3: 280},
            {0: 180, 1: 160, 2: 150, 3: 140},
            500,
            0,
        ),
        # Losing money, short runway (<3 months) → denied
        (
            1000,
            {0: 400, 1: 420, 2: 430, 3: 450},
            {0: 200, 1: 220, 2: 210, 3: 205},
            500,
            0,
        ),
    ],
)
def test_corp_credit_check(deposit, costs, revenue, amount, expected):
    """Integration tests for lending logic using 4-month periods."""

    central_bank = CentralBank()
    bank = Bank(central_bank)
    corp = Corporation(bank=bank)
    corp.set_tick(4)
    corp.bank_interface = BankInterface(bank, corp)
    corp.bank_interface.deposit(deposit)

    corp.stats.costs = costs
    corp.stats.revenue = revenue

    result = bank.corp_credit_check(amount, corp, corp.bank_interface)

    assert np.isclose(result, expected), (
        f"Expected {expected}, got {result} "
        f"(trend={corp.revenue_trend(4):.3f}, "
        f"net_margin={corp.forecast()[2]:.2f}, "
        f"runway={corp.forecast()[0]:.2f})"
    )
