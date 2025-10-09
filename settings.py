from dataclasses import dataclass


@dataclass
class CorporationSeed:
    price: float = 0
    demand: int = 0
    salary: float = 0
    ppe: int = 0
    salery_review: int = 0
    salary: float = 0
    balance: float = 0


@dataclass
class PersonSeed:
    mpc: float = 0


@dataclass
class SimulationSettings:
    number_of_ticks: int = 0
    number_of_corporations: int = 0
    number_of_people: int = 0
    number_of_banks: int = 0
    benefit: float = 0
