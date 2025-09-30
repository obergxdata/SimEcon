from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bank import Bank, CentralBank
    from .bank_interface import BankInterface


@dataclass
class Loan:
    tid: str
    amount: float
    issued_by: "Bank"
    issued_to: "BankInterface"
    interest_rate: float


@dataclass
class Deposit:
    tid: str
    amount: float
    deposited_by: "BankInterface"
    deposited_to: "Bank"


@dataclass
class Withdraw:
    tid: str
    amount: float
    withdrawn_by: "BankInterface"
    withdrawn_from: "Bank"


@dataclass
class Reserve:
    tid: str
    amount: float
    reserved_by: "CentralBank"
    reserved_to: "Bank"
