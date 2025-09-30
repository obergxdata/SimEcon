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
