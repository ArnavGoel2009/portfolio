from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass
class Plan:
    objective:str
    memory_context:str
    steps:list[str]

class MemoryAwarePlanner:
    """Injects retrieved, provenance-labelled memory into a planner callback."""
    def __init__(self,memory_store,planner:Callable[[str,str],list[str]],k=5):
        self.memory_store=memory_store;self.planner=planner;self.k=k
    def plan(self,objective,filters=None):
        context=self.memory_store.context(objective,self.k,filters)
        steps=self.planner(objective,context)
        if not isinstance(steps,list) or not all(isinstance(x,str) for x in steps):
            raise TypeError("planner must return list[str]")
        return Plan(objective,context,steps)
