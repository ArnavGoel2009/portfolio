import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from jarvis_core.postgres_state import PostgresTaskStore


class FakeResult:
    def __init__(self,row): self.row=row
    def fetchone(self): return self.row

class FakeConn:
    def __init__(self,rows): self.rows=list(rows); self.calls=[]
    def execute(self,q,p=()):
        self.calls.append((q,p))
        return FakeResult(self.rows.pop(0) if self.rows else None)


class PostgresStateTests(unittest.TestCase):
    def test_claim_mapping(self):
        c=FakeConn([("00000000-0000-0000-0000-000000000001","task","jarvis",7.2,["python"],2,"2026-08-19T04:00:00Z",{"x":1})])
        t=PostgresTaskStore(c).claim_next("codex",["python"])
        self.assertEqual(t.title,"task")
        self.assertEqual(t.attempts,2)
        self.assertEqual(t.payload,{"x":1})

    def test_complete_requires_evidence(self):
        with self.assertRaises(ValueError): PostgresTaskStore(FakeConn([])).complete("id","codex",[])

    def test_enqueue_uses_json_payload(self):
        c=FakeConn([("abc",)])
        out=PostgresTaskStore(c).enqueue(title="x",lane="jarvis",impact=9,urgency=8,confidence=9,effort=4,payload={"a":1})
        self.assertEqual(out,"abc")
        self.assertEqual(json.loads(c.calls[0][1][-1]),{"a":1})

    def test_migration_contract(self):
        sql=(Path(__file__).parents[1]/"migrations/001_postgres_state.sql").read_text().lower()
        self.assertIn("for update skip locked",sql)
        self.assertIn("completion requires evidence",sql)
        self.assertIn("every evidence entry requires type and ref",sql)
        self.assertIn("unique index",sql)
        self.assertIn("jarvis_audit",sql)
        self.assertIn("unique_violation",sql)

    def test_twenty_workers_one_task_one_owner_model(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"q.db"
            con=sqlite3.connect(db)
            con.execute("create table q(id integer primary key,status text,owner text)")
            con.execute("insert into q values(1,'READY',null)")
            con.commit();con.close()
            won=[];lock=threading.Lock();barrier=threading.Barrier(20)
            def worker(i):
                c=sqlite3.connect(db,timeout=5,isolation_level=None)
                barrier.wait();c.execute("begin immediate")
                row=c.execute("select id from q where status='READY' limit 1").fetchone()
                if row:
                    c.execute("update q set status='CLAIMED',owner=? where id=? and status='READY'",(f"w{i}",row[0]))
                    if c.total_changes:
                        with lock: won.append(i)
                c.commit();c.close()
            threads=[threading.Thread(target=worker,args=(i,)) for i in range(20)]
            [t.start() for t in threads];[t.join() for t in threads]
            self.assertEqual(len(won),1)

if __name__=='__main__': unittest.main()
