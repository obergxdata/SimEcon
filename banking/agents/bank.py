from banking.bank_accounting import Deposit, Withdraw
from typing import TYPE_CHECKING, Union, Tuple
import uuid

if TYPE_CHECKING:
    from .bank_interface import BankInterface


class Bank:

    def __init__(self, central_bank: "CentralBank") -> None:
        self.deposits: dict["BankInterface", list[Deposit]] = {}
        self.withdraws: dict["BankInterface", list[Withdraw]] = {}
        self.Ledger: dict["BankInterface", float] = {}
        self.central_bank = central_bank
        self.central_bank.register_bank(self)
        self.tick = 0

    @staticmethod
    def generate_uid() -> str:
        return str(uuid.uuid4())

    def _update_ledger(self, bank_interface: "BankInterface", amount: float) -> None:
        self.Ledger[bank_interface] += amount

    def get_ledger(self, bank_interface: "BankInterface") -> float:
        return self.Ledger[bank_interface]

    def register_BankInterface(self, bank_interface: "BankInterface") -> None:
        self.deposits[bank_interface] = []
        self.withdraws[bank_interface] = []
        self.Ledger[bank_interface] = 0

    def transfer(
        self,
        amount: float,
        from_: "BankInterface",
        to: "BankInterface",
    ) -> Tuple[str, str]:
        """
        Transfer money from one bank customer to another bank customer
        using both deposits and withdraws
        """

        if amount < 0:
            raise ValueError("Amount must be positive")

        if from_ not in self.Ledger:
            raise ValueError(f"BankInterface {from_} not found in bank {self}")

        # Withdraw from self
        wtid = self.withdraw(amount, from_)
        # Deposit to bank
        dtid = to.bank.deposit(amount, to)
        return wtid, dtid

    def withdraw(self, amount: float, bank_interface: "BankInterface") -> str:

        if amount > self.get_ledger(bank_interface):
            raise ValueError(
                f"Amount {amount} is greater than bank balance {self.get_ledger(bank_interface)}"
            )

        # Update ledger
        self._update_ledger(bank_interface, -amount)

        # Generate transaction id
        tid = self.generate_uid()
        # Generate withdraw object
        withdraw = Withdraw(
            tid=tid, amount=amount, withdrawn_by=bank_interface, withdrawn_from=self
        )
        # Add withdraw to withdraws ledger
        self.withdraws[bank_interface].append(withdraw)
        # Remove reserve from central bank
        self.central_bank.remove_reserve(amount, self)

        return tid

    def deposit(self, amount: float, bank_interface: "BankInterface") -> str:

        # Update ledger
        self._update_ledger(bank_interface, amount)

        # Generate transaction id
        tid = self.generate_uid()
        # Generate deposit object
        deposit = Deposit(
            tid=tid, amount=amount, deposited_by=bank_interface, deposited_to=self
        )
        # Add deposit to deposits ledger
        self.deposits[bank_interface].append(deposit)
        # Add reserve to central bank
        self.central_bank.add_reserve(amount, self)

        return tid

    def get_reserve(self, bank: "Bank") -> float:
        return self.central_bank.get_reserve(bank)

    def find_transaction(
        self, tid: str, bank_interface: "BankInterface"
    ) -> Union[Deposit, Withdraw]:

        for deposit in self.deposits[bank_interface]:
            if deposit.tid == tid:
                return deposit
        for withdraw in self.withdraws[bank_interface]:
            if withdraw.tid == tid:
                return withdraw

        raise ValueError(
            f"Transaction {tid} not found for BankInterface {bank_interface}"
        )

    def check_balance(self, bank_interface: "BankInterface") -> float:
        deposits = self.deposits[bank_interface]
        withdraws = self.withdraws[bank_interface]
        total = sum(deposit.amount for deposit in deposits) - sum(
            withdraw.amount for withdraw in withdraws
        )
        raise Exception(total)

        return total


class CentralBank:

    def __init__(self) -> None:
        self.reserves: dict["Bank", float] = {}

    def register_bank(self, bank: "Bank") -> None:
        self.reserves[bank] = 0

    def remove_reserve(self, amount: float, bank: "Bank") -> None:
        self.reserves[bank] -= amount

    def add_reserve(self, amount: float, bank: "Bank") -> None:
        self.reserves[bank] += amount

    def get_reserve(self, bank: "Bank") -> float:
        return self.reserves[bank]
