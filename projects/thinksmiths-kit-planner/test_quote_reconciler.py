from datetime import date, timedelta
from quote_reconciler import *

def run():
    today=date(2026,8,14)
    a=SupplierQuote("A",today-timedelta(days=2),300,50,1000,25)
    b=SupplierQuote("B",today-timedelta(days=1),290,55,2000,25)
    c=SupplierQuote("Old",today-timedelta(days=60),100,20,0,1)
    ranked=rank_quotes([a,b,c],50,as_of=today,max_age_days=30)
    assert [r["supplier"] for r in ranked] == ["A","B"]
    assert ranked[0]["landed_total_inr"] == 18500
    assert ranked[0]["landed_unit_inr"] == 370
    cov=funding_coverage(18000,[a,b,c],50,as_of=today,max_age_days=30)
    assert cov["fundable"] is False and cov["shortfall_inr"] == 500
    cov2=funding_coverage(19000,[a,b,c],50,as_of=today,max_age_days=30)
    assert cov2["fundable"] is True and cov2["best_supplier"] == "A"
    try:
        rank_quotes([a],10,as_of=today)
        assert False
    except Exception:
        pass
    print("5 tests passed")

if __name__=="__main__":
    run()
