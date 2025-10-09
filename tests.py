import pytest
from simulation import Simulation, SimulationSettings
import random
from logging_config import get_logger
import math

logger = get_logger(__name__)


def test_ticks():

    sim = Simulation()
    sim.sim_settings.number_of_banks = 2
    sim.sim_settings.number_of_people = 750
    sim.sim_settings.number_of_corporations = 4
    sim.sim_settings.benefit = 40
    sim.corporation_seed.price = 15
    sim.corporation_seed.demand = 50
    sim.corporation_seed.ppe = 8
    sim.corporation_seed.salary = 100
    sim.corporation_seed.balance = 50000
    sim.person_seed.mpc = 0.5

    sim.validate_settings()

    sim.init_banks()
    sim.init_people()
    sim.init_corporations()

    # Validate initialization
    assert len(sim.people) == sim.sim_settings.number_of_people
    assert random.choice(sim.people).bank_interface.check_balance() == 0
    assert random.choice(sim.people).latest_spending == 0
    assert random.choice(sim.corporations).latest_sales == 0
    assert random.choice(sim.corporations).latest_demand == sim.corporation_seed.demand
    assert len(sim.corporations) == sim.sim_settings.number_of_corporations
    assert len(sim.banks) == sim.sim_settings.number_of_banks

    for _ in range(80):
        sim.one_tick()

    sim.stats.plot(
        columns=[
            "goods_demanded",
            "goods_produced",
            "goods_sold",
            "goods_overstock",
        ],
        folder="goods",
        filename="goods_stats",
    )

    sim.stats.plot(
        columns=[
            "company_avg_revenue",
            "company_avg_costs",
            "company_avg_profit",
            "company_total_loans",
        ],
        folder="corporation",
        filename="company_finance",
    )

    sim.stats.plot(
        columns=[
            "persons_employed",
        ],
        folder="corporation",
        filename="company_employees",
    )

    sim.stats.plot(
        columns=[
            "person_avg_salary",
            "person_avg_spending",
        ],
        folder="person",
        filename="person_avg_salary",
    )

    sim.stats.plot(
        columns=[
            "person_total_budget",
            "person_avg_money_in_banks",
        ],
        folder="person",
        filename="person_total_budget",
    )

    sim.stats.plot(
        columns=[
            "goods_avg_price",
            "goods_min_price",
            "goods_max_price",
        ],
        folder="goods",
        filename="goods_price",
    )
