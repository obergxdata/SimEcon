from typing import TYPE_CHECKING, Tuple, Union
from .bank_accounting import Deposit, Withdraw

if TYPE_CHECKING:
    from banking.agents.bank import Bank
    from agents.person import Person
    from agents.corporation import Corporation
    from banking.bank_accounting import Deposit, Withdraw


class BankInterface:

    def __init__(
        self, bank: "Bank", entity: Union["Person", "Corporation"] = None
    ) -> None:
        self.bank = bank
        self.entity = entity
        self.bank.register_BankInterface(self)

    def check_balance(self) -> float:
        return self.bank.get_ledger(self)

    def deposit(self, amount: float) -> str:
        return self.bank.deposit(amount, self)

    def transfer(self, amount: float, to: "BankInterface") -> Tuple[str, str]:
        return self.bank.transfer(amount, self, to)

    def find_transaction(self, tid: str) -> Union[Deposit, Withdraw]:
        return self.bank.find_transaction(tid, self)

    def take_loan(self, amount: float, maximum: bool = False) -> str:
        # TODO: implement loan taking
        # If maximum is True, and intial amount is denied
        # get the maximum amount from the bank
        return False
