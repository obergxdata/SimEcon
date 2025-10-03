import settings
from agents.corporation import Corporation
from agents.person import Person
from base_agent import BaseStats
from banking.agents.bank import Bank
from banking.agents.central_bank import CentralBank
import random
from logging_config import get_logger
from settings import CorporationSeed, PersonSeed, SimulationSettings
from dataclasses import dataclass, field, asdict

logger = get_logger(__name__)


@dataclass
class SimStats(BaseStats):
    persons_employed: dict[int, int] = field(default_factory=dict)
    goods_produced: dict[int, int] = field(default_factory=dict)
    goods_sold: dict[int, int] = field(default_factory=dict)
    goods_demanded: dict[int, int] = field(default_factory=dict)
    goods_owned: dict[int, int] = field(default_factory=dict)
    goods_stock_left: dict[int, int] = field(default_factory=dict)
    person_money_spent: dict[int, int] = field(default_factory=dict)
    person_money_in_banks: dict[int, int] = field(default_factory=dict)
    avg_salary: dict[int, float] = field(default_factory=dict)
    goods_avg_price: dict[int, float] = field(default_factory=dict)


class Simulation:
    def __init__(self):
        self.corporations: list[Corporation] = []
        self.people: list[Person] = []
        self.banks: list[Bank] = []
        self.central_bank: CentralBank | None = None
        self.tick = 0
        self.sim_settings = SimulationSettings()
        self.corporation_seed = CorporationSeed()
        self.person_seed = PersonSeed()
        self.stats = SimStats()

    def corporations_tick(self):
        # Check for salary review
        for corp in self.corporations:
            corp.set_tick(self.tick)
            corp.initialize_tick_stats()
            corp.review_finance()
            corp.produce_goods()
            corp.pay_salaries()
            # If corp is dead, remove it and pay employees
            if not corp.alive:
                logger.info(f"Corporation {corp.name} is dead, step {self.tick}")
                self.corporations.remove(corp)
            if self.tick > 1:
                corp.review_price()
                corp.review_salary(self.sim_settings.min_wage)

    def people_tick(self):
        # We always need to reset demand and sales
        if not self.corporations or not self.people:
            raise Exception("corporations and people must be initialized")

        broke = 0
        for person in self.people:
            person.set_tick(self.tick)
            if person.bank_interface.check_balance() > 0:
                spent = person.spend(self.corporations)
                if spent > 0:
                    self.stats.record(self.tick, person_money_spent=spent)
            else:
                broke += 1

    def one_tick(self):
        self.tick += 1
        self.stats.set_tick(self.tick)
        self.corporations_tick()
        self.people_tick()
        self.clean_up()
        self.gen_stats()

    def clean_up(self):
        for corp in self.corporations:
            corp.clean_up()
        for person in self.people:
            person.clean_up()

    def run(self):
        logger.info("Starting simulation run for %d ticks", settings.NUMBER_OF_TICKS)
        for tick in range(settings.NUMBER_OF_TICKS):
            pass

    def gen_stats(self):
        # Population stats
        persons_employed = len([1 for p in self.people if p.employed])
        goods_owned = sum([len(p.bought_goods) for p in self.people])
        goods_demanded = sum([c.stats.demand[self.tick] for c in self.corporations])
        goods_produced = sum([c.stats.production[self.tick] for c in self.corporations])
        goods_sold = sum([c.stats.sales[self.tick] for c in self.corporations])
        goods_stock_left = sum([len(c.goods) for c in self.corporations])
        goods_avg_price = sum(
            [c.stats.price[self.tick] for c in self.corporations]
        ) / len(self.corporations)
        person_money_spent = sum([g.price for p in self.people for g in p.bought_goods])
        person_money_in_banks = sum(
            [p.bank_interface.check_balance() for p in self.people]
        )
        avg_salary = sum([c.salary for c in self.corporations]) / len(self.corporations)
        self.stats.record(
            self.tick,
            persons_employed=persons_employed,
            goods_owned=goods_owned,
            goods_demanded=goods_demanded,
            goods_produced=goods_produced,
            goods_sold=goods_sold,
            goods_stock_left=goods_stock_left,
            goods_avg_price=goods_avg_price,
            person_money_spent=person_money_spent,
            person_money_in_banks=person_money_in_banks,
            avg_salary=avg_salary,
        )

        return self.stats

    def init_banks(self):
        self.central_bank = CentralBank()
        for _ in range(self.sim_settings.number_of_banks):
            self.banks.append(Bank(self.central_bank))

    def choose_job(self):
        # TODO create labor market class
        # return a random corp weighted by the salary
        hiring_corps = [c for c in self.corporations if c.hiring]
        if not hiring_corps:
            return None
        return random.choices(hiring_corps, weights=[c.salary for c in hiring_corps])[0]

    def labor_market(self):
        unemployed_people = [p for p in self.people if not p.employed]
        random.shuffle(unemployed_people)
        employee_count = 0
        for person in unemployed_people:
            corp = self.choose_job()
            if corp:
                corp.add_employee(person)
                employee_count += 1

        return employee_count

    def init_corporations(self):
        if not self.people or not self.banks:
            raise Exception("people and banks must be initialized")

        # Create corporations
        for _ in range(self.sim_settings.number_of_corporations):
            self.corporations.append(Corporation(random.choice(self.banks)))

        # Add settings to corporations
        for corp in self.corporations:
            corp.ppe = self.corporation_seed.ppe
            corp.salary = self.corporation_seed.salary
            corp.latest_demand = self.corporation_seed.demand
            corp.latest_price = self.corporation_seed.price
            corp.salary = self.corporation_seed.salary
            corp.bank_interface.deposit(self.corporation_seed.balance)

        # Start labor market
        employee_count = self.labor_market()

        logger.info(
            "added %d employees to %d corporations",
            employee_count,
            self.sim_settings.number_of_corporations,
        )

    def init_people(self):
        if not self.banks:
            raise Exception("banks must be initialized")

        for _ in range(self.sim_settings.number_of_people):
            # Select random bank
            bank = random.choice(self.banks)
            person = Person(bank=bank)
            person.mpc = self.person_seed.mpc
            self.people.append(person)


if __name__ == "__main__":
    sim = Simulation()
    sim.initialize()
    sim.run()
