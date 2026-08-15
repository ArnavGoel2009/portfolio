from outreach_integrity import canonical_org, subject_tokens, is_direct_money_ask, audit_rows, summary
from queue_reconciler import reconcile
from funding_route_ranker import score_route

def test_canonical_org():
    assert canonical_org("The DLF Foundation") == "dlf"
    assert canonical_org("Samsung India Pvt Ltd") == "samsung"

def test_subject_tokens():
    assert subject_tokens("[READY] CSR funding request")
    assert subject_tokens("Normal human subject") == []

def test_money_ask():
    body="We ran proof workshops. We now seek CSR funding to underwrite 250 STEM kits and guides."
    assert is_direct_money_ask("Funding request",body)
    assert not is_direct_money_ask("STEM partnership","We seek a partnership to distribute kits.")

def test_audit_duplicates_and_route():
    rows=[
        {"draft_id":"d1","organisation":"DLF Foundation","subject":"CSR funding request",
         "body":"Proof phase completed. We seek CSR funding to underwrite 250 kits.",
         "verification_source":"https://official.example/csr","route_role":"CSR Foundation"},
        {"draft_id":"d2","organisation":"NewCo Foundation","subject":"[READY] Funding",
         "body":"We seek CSR funding to underwrite kits.",
         "verification_source":"","route_role":"Customer Support"},
    ]
    fs=audit_rows(rows, prior_orgs=["DLF"])
    assert fs[0].status=="HOLD" and "DUPLICATE_ORGANISATION_PRIOR" in fs[0].reasons
    assert fs[1].status=="HOLD"
    assert any(x.startswith("INTERNAL_SUBJECT_TOKEN") for x in fs[1].reasons)
    assert "MISSING_VERIFICATION_SOURCE" in fs[1].reasons
    assert "ROUTE_ROLE_NOT_FUNDING_APPROPRIATE" in fs[1].reasons
    assert summary(fs)=={"total":2,"ready":0,"hold":2}

def test_reconcile():
    t=[{"draft_id":"d1","recipient":"a@x.com","subject":"Funding"}]
    g=[{"draft_id":"d1","recipient":"a@x.com","subject":"Funding"},
       {"draft_id":"d2","recipient":"b@y.com","subject":"Other"}]
    r=reconcile(t,g)
    assert r[0].state=="MATCH"
    assert r[1].state=="UNTRACKED_GMAIL_DRAFT"

def test_route_score():
    a=score_route({"source_type":"first_party","role":"Head CSR","named_person":True,"current":True,"explicit_inbound_funding_route":True})
    assert a.decision=="READY_ROUTE" and a.score>=70
    b=score_route({"source_type":"first_party","role":"Customer Support","named_person":False,"current":True,"explicit_inbound_funding_route":False})
    assert b.decision=="HOLD_ROUTE"

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
