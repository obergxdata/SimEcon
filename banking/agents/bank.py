from banking.bank_accounting import Deposit, Withdraw, Loan
from typing import TYPE_CHECKING, Union, Tuple
import uuid

if TYPE_CHECKING:
    from banking.bank_interface import BankInterface
    from agents.corporation import Corporation


class Bank:

    def __init__(self, central_bank: "CentralBank") -> None:
        self.deposits: dict["BankInterface", list[Deposit]] = {}
        self.withdraws: dict["BankInterface", list[Withdraw]] = {}
        self.loans: dict["BankInterface", list[Loan]] = {}
        self.Ledger: dict["BankInterface", float] = {}
        self.central_bank = central_bank
        self.central_bank.register_bank(self)
        self.interest_rate = 0.01
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
        self.loans[bank_interface] = []
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
            raise ValueError(f"Amount must be positive, got {amount}")

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

    def issue_loan(
        self, amount: float, corp: "Corporation", bank_interface: "BankInterface"
    ) -> str:
        # Check credit
        credit_amount = self.corp_credit_check(amount, corp, bank_interface)
        if credit_amount == 0:
            return 0
        # issue loan
        tid = self.generate_uid()
        loan = Loan(
            tid=tid,
            amount=credit_amount,
            issued_by=self,
            issued_to=bank_interface,
            interest_rate=self.interest_rate,
        )
        # Update ledger
        self._update_ledger(bank_interface, credit_amount)

        # Add loan to loans ledger
        self.loans[bank_interface].append(loan)
        return loan

    def corp_credit_check(
        self, amount: float, corp: "Corporation", bank_interface: "BankInterface"
    ) -> float:
        # Financial indicators
        balance = self.get_ledger(bank_interface)
        runway, burn, net_margin = corp.forecast()
        trend = corp.revenue_trend()

        # --- Risk assessment ---
        # If company is losing money and has <3 months runway → too risky
        if runway < 3 and net_margin < 0:
            return 0  # deny loan

        # If negative trend and losing money → high risk
        if trend < 0 and net_margin < 0:
            return 0

        # --- Lending capacity ---
        base_amount = 0.5 * balance  # safe default = 50% of balance

        # Reward strong trend or profitability
        if trend > 0.2:
            base_amount *= 1.5  # growing business → more confidence
        elif trend < -0.2:
            base_amount *= 0.5  # declining → more conservative

        if net_margin > 0:
            base_amount += 0.2 * net_margin  # bonus for profit

        # Ensure it doesn’t exceed total deposits or cash safety ratio
        max_amount = min(base_amount, 0.75 * balance)

        return min(max_amount, amount)

    def find_transaction(
        self, tid: str, bank_interface: "BankInterface"
    ) -> Union[Deposit, Withdraw]:

        # check that tid is string
        if not isinstance(tid, str) or tid == "":
            raise ValueError(f"Transaction id {tid} is not a string or is empty")

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
