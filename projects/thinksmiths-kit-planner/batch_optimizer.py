"""Find the largest standard kit batch affordable under a cash ceiling.
Planning inputs only; no supplier-price claims.
"""
from funding_engine import FundingPlan

STANDARD_BATCHES=(25,50,100,250,500,1000)

def choose_batch(cash_inr, kit_unit_cost_inr, guide_unit_cost_inr=50,
                 logistics_rate=.08, contingency_rate=.07, fixed_cost_inr=0):
    plan=FundingPlan(cash_inr,kit_unit_cost_inr,guide_unit_cost_inr,
                     logistics_rate,contingency_rate,fixed_cost_inr).calculate()
    capacity=plan['deployable_kits']
    feasible=[n for n in STANDARD_BATCHES if n<=capacity]
    chosen=max(feasible) if feasible else 0
    return {'cash_inr':cash_inr,'capacity_kits':capacity,'standard_batch':chosen,
            'headroom_kits':capacity-chosen}

if __name__=='__main__':
    import json
    print(json.dumps([choose_batch(c,400) for c in (25000,50000,100000,250000)],indent=2))
