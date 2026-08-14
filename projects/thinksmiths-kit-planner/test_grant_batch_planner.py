from grant_batch_planner import *

def run():
    s=[CostScenario(300,50,0,0), CostScenario(400,50,0,0), CostScenario(500,50,0,0)]
    assert abs(CostScenario(300,50,0.1,0.1).total_cost(10)-4235)<1e-9
    assert affordability_probability(4500,10,s) == 2/3
    rec=robust_batch_recommendation(4500,[5,10,15],s,min_confidence=2/3)
    assert rec["chosen_batch"] == 10
    assert rec["fail_closed"] is False
    rec2=robust_batch_recommendation(1000,[5,10],s,min_confidence=0.9)
    assert rec2["chosen_batch"] == 0 and rec2["fail_closed"] is True
    assert minimum_cash_for_batch(10,s,min_confidence=2/3,tolerance_inr=1) == 4500
    a=generate_scenarios(iterations=10,seed=7,kit_cost_range=(300,500),guide_cost_range=(40,60),logistics_rate_range=(0.05,0.12),contingency_rate_range=(0.05,0.10))
    b=generate_scenarios(iterations=10,seed=7,kit_cost_range=(300,500),guide_cost_range=(40,60),logistics_rate_range=(0.05,0.12),contingency_rate_range=(0.05,0.10))
    assert a == b
    try:
        robust_batch_recommendation(1000,[],s)
        raise AssertionError("empty batch list should fail")
    except ValueError:
        pass
    print("7 tests passed")

if __name__=="__main__":
    run()
