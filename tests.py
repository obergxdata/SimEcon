import pytest
from simulation import Simulation, SimulationSettings
import random
from logging_config import get_logger
import math

logger = get_logger(__name__)


def test_ticks():

    sim = Simulation()
    sim.sim_settings.number_of_banks = 2
    sim.sim_settings.number_of_people = 500
    sim.sim_settings.number_of_corporations = 3
    sim.sim_settings.min_wage = 0
    sim.corporation_seed.price = 10
    sim.corporation_seed.demand = 100
    sim.corporation_seed.ppe = 3.0
    sim.corporation_seed.salary = 100
    sim.corporation_seed.balance = 50000
    sim.person_seed.mpc = 0.5

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

    sim.one_tick()

    stats_1 = sim.stats.get_latest()

    s1_emplyees_per_corp = min(
        sim.sim_settings.number_of_people // sim.sim_settings.number_of_corporations,
        math.ceil(sim.corporation_seed.demand / sim.corporation_seed.ppe),
    )
    s1_total_employees = s1_emplyees_per_corp * sim.sim_settings.number_of_corporations

    s1_products_per_person = (
        sim.corporation_seed.salary * sim.person_seed.mpc
    ) // sim.corporation_seed.price

    # Only employees will buy goods
    s1_demand = s1_products_per_person * s1_total_employees
    s1_produced_goods = s1_total_employees * sim.corporation_seed.ppe
    s1_stock_left = max(0, s1_produced_goods - s1_demand)

    assert s1_produced_goods == pytest.approx(stats_1["goods_produced"], rel=0.05)

    assert pytest.approx(stats_1["goods_demanded"], rel=0.05) == s1_demand

    # Stock left should be less then 95% of demand
    stats_1["goods_stock_left"] < 0.05 * s1_demand

    # goods owned should be produced goods minus stock left
    assert stats_1["goods_owned"] == pytest.approx(
        s1_produced_goods - s1_stock_left, rel=0.05
    )

    # goods sold should be equal to goods owned
    assert stats_1["goods_sold"] == stats_1["goods_owned"]

    # People should have spent money as goods sold times price
    expected = (s1_produced_goods - s1_stock_left) * sim.corporation_seed.price
    assert stats_1["person_money_spent"] == pytest.approx(expected, rel=0.05)

    for _ in range(20):
        sim.one_tick()

    sim.stats.plot(
        columns=["goods_demanded", "goods_produced", "goods_sold", "goods_stock_left"],
        folder="goods",
        filename="goods_stats",
    )

    sim.stats.plot(
        columns=[
            "company_avg_revenue",
            "company_avg_costs",
            "company_avg_profit",
        ],
        folder="corporation",
        filename="company_finance",
    )

    # Market plots
    sim.stats.plot(
        columns=["persons_employed", "person_avg_salary", "person_avg_money_in_banks"],
        folder="market",
        filename="market_stats",
        log_scale=True,
    )
