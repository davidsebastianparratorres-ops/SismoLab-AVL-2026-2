from datetime import timedelta
from src.models.SimulationClock import SimulationClock, parse_iso_utc
from src.models.SimulationParameters import SimulationParameters
from src.controllers.Scenery import Scenery

clock = SimulationClock(parse_iso_utc("2026-09-07T10:00:00Z"))
params = SimulationParameters()
scenery = Scenery(zones=[], stations={}, simulation_clock=clock, tree=None, undo_stack=None, parameters=params)

r1 = scenery.advance_clock(timedelta(hours=2))
print(r1.success, r1.message, clock.to_dict())

r2 = scenery.update_parameters(w=10)
print(r2.success, r2.message, params.to_dict())

r3 = scenery.update_parameters(l=-1)
print(r3.success, r3.message)