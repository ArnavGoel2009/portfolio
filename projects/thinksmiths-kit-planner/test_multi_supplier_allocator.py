from multi_supplier_allocator import SupplierOffer, optimize_allocation, funding_feasibility


def run():
    a = SupplierOffer("A", 300, 50, 1000, 25, 100)
    b = SupplierOffer("B", 280, 50, 2500, 50, 200)
    c = SupplierOffer("C", 260, 55, 5000, 100, 300)

    r = optimize_allocation([a, b, c], 50)
    assert r["feasible"] is True
    assert r["allocation"] == {"A": 50}
    assert r["total_cost_inr"] == 18500

    r2 = optimize_allocation([a, b, c], 150)
    assert r2["feasible"] is True
    assert sum(r2["allocation"].values()) == 150
    # B wins at this volume despite higher fixed shipping than A.
    assert r2["allocation"] == {"B": 150}
    assert r2["total_cost_inr"] == 52000

    # Capacity forces a split and the optimizer must still hit the exact target.
    d = SupplierOffer("D", 200, 40, 500, 20, 60)
    e = SupplierOffer("E", 220, 40, 500, 20, 60)
    r3 = optimize_allocation([d, e], 100)
    assert r3["feasible"] is True
    assert r3["allocation"] == {"D": 60, "E": 40}
    assert r3["total_cost_inr"] == 25800

    # MOQ/capacity can make an exact target infeasible.
    f = SupplierOffer("F", 100, 0, 0, 50, 50)
    g = SupplierOffer("G", 100, 0, 0, 50, 50)
    r4 = optimize_allocation([f, g], 75)
    assert r4["feasible"] is False

    cov = funding_feasibility(25000, [d, e], 100)
    assert cov["fundable"] is False and cov["shortfall_inr"] == 800
    cov2 = funding_feasibility(27000, [d, e], 100)
    assert cov2["fundable"] is True and cov2["headroom_inr"] == 1200

    try:
        optimize_allocation([], 100)
        assert False
    except ValueError:
        pass

    print("7 tests passed")


if __name__ == "__main__":
    run()
