import pytest

from banking.agents.central_bank import CentralBank
from banking.agents.bank import Bank
from banking.bank_interface import BankInterface
from banking.bank_accounting import Deposit, Withdraw
from agents.person import Person
from agents.corporation import Corporation


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


def test_lend_funds_corp():
    # TODO
    central_bank = CentralBank()
    bank = Bank(central_bank)
    corp = Corporation(bank=bank)
    corp.bank_interface = BankInterface(bank, corp)
