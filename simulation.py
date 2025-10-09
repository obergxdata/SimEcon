import settings
from agents.corporation import Corporation
from agents.person import Person
from base_agent import BaseStats
from banking.agents.bank import Bank
from banking.agents.central_bank import CentralBank
import random
from logging_config import get_logger
from settings import CorporationSeed, PersonSeed, SimulationSettings
from dataclasses import dataclass, field
import time

logger = get_logger(__name__)


@dataclass
class SimStats(BaseStats):
    persons_employed: dict[int, int] = field(default_factory=dict)
    goods_produced: dict[int, int] = field(default_factory=dict)
    goods_sold: dict[int, int] = field(default_factory=dict)
    goods_demanded: dict[int, int] = field(default_factory=dict)
    goods_owned: dict[int, int] = field(default_factory=dict)
    goods_avg_price: dict[int, float] = field(default_factory=dict)
    goods_min_price: dict[int, float] = field(default_factory=dict)
    goods_max_price: dict[int, float] = field(default_factory=dict)
    goods_overstock: dict[int, int] = field(default_factory=dict)
    person_total_budget: dict[int, int] = field(default_factory=dict)
    person_avg_spending: dict[int, int] = field(default_factory=dict)
    person_avg_money_in_banks: dict[int, int] = field(default_factory=dict)
    person_total_queue_size: dict[int, int] = field(default_factory=dict)
    company_money_in_banks: dict[int, int] = field(default_factory=dict)
    person_avg_salary: dict[int, float] = field(default_factory=dict)
    company_revenue: dict[int, float] = field(default_factory=dict)
    company_avg_revenue: dict[int, float] = field(default_factory=dict)
    company_avg_costs: dict[int, float] = field(default_factory=dict)
    company_avg_profit: dict[int, float] = field(default_factory=dict)
    company_total_loans: dict[int, int] = field(default_factory=dict)


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
            if corp.alive:
                corp.one_tick(self.tick)

    def goverment_tick(self):
        # Get unemployed people
        unemployed_people = [p for p in self.people if not p.employed]
        # Give them money
        for person in unemployed_people:
            ltid = person.latest_salary_id
            if ltid:
                amount = person.bank_interface.find_transaction(ltid).amount
            else:
                amount = self.sim_settings.benefit

            tid = person.bank_interface.deposit(amount * 0.6)
            person.latest_salary_id = tid

    def people_tick(self):
        # We always need to reset demand and sales
        if not self.corporations or not self.people:
            raise Exception("corporations and people must be initialized")

        for person in self.people:
            person.set_tick(self.tick)
            if person.bank_interface.check_balance() > 0:
                person.spend(self.corporations)

    def one_tick(self):
        self.tick += 1
        self.stats.set_tick(self.tick)
        # self.goverment_tick()
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

        alive_corporations = [c for c in self.corporations if c.alive]
        # Population stats
        persons_employed = len([1 for p in self.people if p.employed])
        goods_owned = sum([len(p.bought_goods) for p in self.people])
        goods_demanded = sum([c.stats.demand[self.tick] for c in alive_corporations])
        goods_produced = sum(
            [c.stats.production[self.tick] for c in alive_corporations]
        )
        goods_sold = sum([c.stats.sales[self.tick] for c in alive_corporations])
        goods_overstock = sum(
            [c.stats.overstock[self.tick] for c in alive_corporations]
        )
        goods_avg_price = sum(
            [c.stats.price[self.tick] for c in alive_corporations]
        ) / len(alive_corporations)
        goods_min_price = min([c.stats.price[self.tick] for c in alive_corporations])
        goods_max_price = max([c.stats.price[self.tick] for c in alive_corporations])
        person_total_budget = sum([p.latest_budget for p in self.people])
        person_avg_spending = sum([p.latest_spending for p in self.people]) / len(
            self.people
        )
        person_avg_money_in_banks = sum(
            [p.bank_interface.check_balance() for p in self.people]
        ) / len(self.people)
        person_total_queue_size = sum([p.latest_queue_size for p in self.people])
        company_money_in_banks = sum(
            [c.bank_interface.check_balance() for c in alive_corporations]
        )
        company_revenue = sum([c.stats.revenue[self.tick] for c in alive_corporations])
        company_avg_revenue = sum(
            [c.stats.revenue[self.tick] for c in alive_corporations]
        ) / len(alive_corporations)
        company_avg_costs = sum(
            [c.stats.costs[self.tick] for c in alive_corporations]
        ) / len(alive_corporations)
        company_avg_profit = sum(
            [c.stats.profit[self.tick] for c in alive_corporations]
        ) / len(alive_corporations)
        company_total_loans = sum(
            [sum([l.amount for l in c.loans]) for c in alive_corporations]
        )
        person_avg_salary = sum([c.salary for c in alive_corporations]) / len(
            alive_corporations
        )

        self.stats.record(
            self.tick,
            persons_employed=persons_employed,
            goods_owned=goods_owned,
            goods_demanded=goods_demanded,
            goods_produced=goods_produced,
            goods_sold=goods_sold,
            goods_overstock=goods_overstock,
            goods_avg_price=round(goods_avg_price, 2),
            goods_min_price=round(goods_min_price, 2),
            goods_max_price=round(goods_max_price, 2),
            person_total_budget=round(person_total_budget, 2),
            person_avg_spending=round(person_avg_spending, 2),
            person_avg_money_in_banks=round(person_avg_money_in_banks, 2),
            person_total_queue_size=round(person_total_queue_size, 2),
            company_money_in_banks=round(company_money_in_banks, 2),
            company_revenue=round(company_revenue, 2),
            company_avg_revenue=round(company_avg_revenue, 2),
            company_avg_profit=round(company_avg_profit, 2),
            company_avg_costs=round(company_avg_costs, 2),
            company_total_loans=company_total_loans,
            person_avg_salary=round(person_avg_salary, 2),
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
            corp.current_price = self.corporation_seed.price
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

    def validate_settings(self):
        # Calculate employees needed for demand
        emp_needed_per_corp = self.corporation_seed.demand // self.corporation_seed.ppe
        emp_needed_total = (
            emp_needed_per_corp * self.sim_settings.number_of_corporations
        )
        total_salary = self.corporation_seed.salary * emp_needed_total
        total_possible_revenue = total_salary * self.person_seed.mpc

        if emp_needed_total > self.sim_settings.number_of_people:
            logger.warning(
                "Not enough people to meet demand. "
                f"Needed {emp_needed_total}, have {self.sim_settings.number_of_people}"
            )

        unit_cost = round(self.corporation_seed.salary / self.corporation_seed.ppe, 2)
        if unit_cost > self.corporation_seed.price:
            logger.warning(
                "Unit cost exceeds price. "
                f"Cost: {unit_cost}, Price: {self.corporation_seed.price}"
            )

        missing = total_salary - total_possible_revenue
        missing_percentage = missing / total_salary
        if missing > 0:
            logger.warning(
                "Revenue insufficient to cover salaries. "
                f"Revenue: {total_possible_revenue}, Salaries: {total_salary}. "
                f"Need {missing_percentage:.1%} cost reduction"
            )

        time.sleep(3)


if __name__ == "__main__":
    sim = Simulation()
    sim.initialize()
    sim.run()
