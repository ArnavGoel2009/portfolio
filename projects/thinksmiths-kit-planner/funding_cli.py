import argparse, json
from grant_batch_planner import generate_scenarios, robust_batch_recommendation, minimum_cash_for_batch

def main():
    p=argparse.ArgumentParser(description="Fail-closed ThinkSmiths funding/batch planner")
    p.add_argument("--cash", type=float, required=True)
    p.add_argument("--batches", default="25,50,100,250")
    p.add_argument("--confidence", type=float, default=0.90)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--iterations", type=int, default=5000)
    p.add_argument("--kit-min", type=float, default=300)
    p.add_argument("--kit-max", type=float, default=500)
    p.add_argument("--guide-min", type=float, default=40)
    p.add_argument("--guide-max", type=float, default=60)
    args=p.parse_args()
    scenarios=generate_scenarios(iterations=args.iterations, seed=args.seed, kit_cost_range=(args.kit_min,args.kit_max), guide_cost_range=(args.guide_min,args.guide_max), logistics_rate_range=(0.05,0.12), contingency_rate_range=(0.05,0.10))
    batches=[int(x) for x in args.batches.split(",") if x.strip()]
    rec=robust_batch_recommendation(args.cash,batches,scenarios,min_confidence=args.confidence)
    if rec["chosen_batch"]:
        rec["minimum_cash_for_chosen_batch"]=minimum_cash_for_batch(rec["chosen_batch"], scenarios, min_confidence=args.confidence, tolerance_inr=100)
    print(json.dumps(rec,indent=2))
    raise SystemExit(2 if rec["fail_closed"] else 0)

if __name__=="__main__":
    main()
