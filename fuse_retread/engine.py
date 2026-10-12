"""Where a tyre may go next, and what each recording does to it.

Pure Python — no frappe — so the route rules can be tested on their own (tests/test_engine.py).

The route is the client's own stage list (FR Stage), read in order. A stage with a screen is a
recording point; one without is a physical step the tyre passes through with nothing captured.
A Job Card keeps three things that this module moves:

  position  the order number of the last stage the tyre reached
  next      the recording points it may reach next — the floor screens refuse any other
  result    Passed, Rejected or Not Retreadable, once an inspection has said so

Everything else about the line comes from the stage list, so a second retreader with a
different line is configuration, not code.
"""

ROUTE_FIELDS = {"Retread": "on_retread", "Repair Only": "on_repair"}

# The line as the client drew it: (stage, order, screen, on retread, on repair-only, optional on
# retread, suggested). install.py seeds FR Stage from this once; after that the site's own list
# rules, and the client may rename, reorder or add stages.
DEFAULT_STAGES = [
	("Collection from Customer", 10, "None", 1, 1, 0, 0),
	("Receive at Branch", 20, "Receive", 1, 1, 0, 0),
	("Receiving", 30, "None", 1, 1, 0, 0),
	("1st Inspection", 40, "Inspection", 1, 1, 0, 0),
	("NDI", 50, "None", 1, 0, 0, 0),
	("Buffing", 60, "None", 1, 0, 0, 0),
	("Skiving", 70, "None", 1, 1, 0, 0),
	("Repairs", 80, "Number Pad", 1, 1, 1, 0),
	("Cementing", 90, "None", 1, 0, 0, 0),
	("Filling", 100, "None", 1, 0, 0, 0),
	("Building", 110, "Number Pad", 1, 0, 0, 0),
	("Chambers", 120, "Chambers", 1, 1, 0, 1),
	("Final Inspection", 130, "Inspection", 1, 1, 0, 0),
	("Dispatch", 140, "Dispatch", 1, 1, 0, 0),
	("Return to Branch", 150, "None", 1, 1, 0, 0),
	("Invoice", 160, "Office", 1, 1, 0, 0),
	("Deliver to Customer", 170, "Deliver", 1, 1, 0, 1),
]


def default_stage_rows():
	"""DEFAULT_STAGES as the dicts FR Stage rows read as."""
	keys = ("stage", "sequence", "screen", "on_retread", "on_repair", "optional_on_retread", "suggested")
	return [dict(zip(keys, row, strict=True)) for row in DEFAULT_STAGES]


# What each kind of screen may record. The two inspections share a screen but not a vocabulary:
# the first decides whether the casing can be worked at all, the last whether the work passed.
ENTRY_OUTCOMES = ("Yes", "No")
FINAL_OUTCOMES = ("Pass", "Reject", "Redo", "Repair")
SCREEN_OUTCOMES = {
	"Receive": ("Received",),
	"Number Pad": ("Done",),
	"Chambers": ("Into Chamber", "Cured"),
	"Dispatch": ("Dispatched",),
	"Office": ("Invoiced",),
	"Deliver": ("Delivered",),
}


class RouteError(ValueError):
	"""A recording the route does not allow. The message is written for the person on the floor."""


def is_capture(stage):
	return (stage.get("screen") or "None") != "None"


def ordered(stages):
	return sorted(stages, key=lambda s: int(s.get("sequence") or 0))


def on_route(stages, route):
	field = ROUTE_FIELDS.get(route)
	if not field:
		raise RouteError(f"Unknown route: {route}")
	return [s for s in ordered(stages) if s.get(field)]


def by_name(stages, name):
	for stage in stages:
		if stage["stage"] == name:
			return stage
	raise RouteError(f"There is no stage called {name}.")


def inspections(stages):
	return [s for s in ordered(stages) if s.get("screen") == "Inspection"]


def entry_inspection(stages):
	found = inspections(stages)
	return found[0] if found else None


def final_inspection(stages):
	found = inspections(stages)
	return found[-1] if len(found) > 1 else None


def next_captures(stages, route, position):
	"""The recording points a tyre at `position` may reach next on its route.

	Normally one. A point marked optional on the retread route (Repairs, for a tyre that needs
	none) is offered alongside the first point after it that is not optional.
	"""
	found = []
	for stage in on_route(stages, route):
		if int(stage.get("sequence") or 0) <= position or not is_capture(stage):
			continue
		found.append(stage["stage"])
		if not (route == "Retread" and stage.get("optional_on_retread")):
			break
	return found


def first_repair_point(stages, route):
	"""Where C Repair sends a tyre back to: the first recording point after the entry inspection."""
	entry = entry_inspection(stages)
	after = int(entry.get("sequence") or 0) if entry else 0
	for stage in on_route(stages, route):
		if int(stage.get("sequence") or 0) > after and is_capture(stage):
			return stage
	raise RouteError("The route has no recording point after the first inspection.")


def outcomes(stages, stage_name, state):
	"""What may be recorded at this stage for this tyre, in the order the buttons appear."""
	stage = by_name(stages, stage_name)
	screen = stage.get("screen")
	if screen == "Inspection":
		if stage["stage"] == entry_inspection(stages)["stage"]:
			return list(ENTRY_OUTCOMES)
		# A casing that failed the first inspection is only ever confirmed as a reject.
		if state.get("result") == "Not Retreadable":
			return ["Reject"]
		return list(FINAL_OUTCOMES)
	return list(SCREEN_OUTCOMES.get(screen, ()))


def apply(stages, state, stage_name, outcome, route=None):
	"""Record `outcome` at `stage_name` and return the job's new state.

	`state` holds route, position, next, result, status, redo_count, repair_count and
	in_chamber. It is not changed; a new dict comes back. A recording the route does not allow
	raises RouteError.
	"""
	stage = by_name(stages, stage_name)
	new = dict(state)
	new["next"] = list(state.get("next") or [])
	waiting = new["next"]

	if stage_name not in waiting:
		if waiting:
			raise RouteError(f"This tyre is not due at {stage_name}. Next for it: {' or '.join(waiting)}.")
		raise RouteError(f"This tyre is not due at {stage_name}. It has nowhere further to go.")
	if outcome not in outcomes(stages, stage_name, state):
		raise RouteError(f"{outcome} cannot be recorded at {stage_name}.")

	sequence = int(stage.get("sequence") or 0)
	screen = stage.get("screen")

	if screen == "Inspection" and outcome in ENTRY_OUTCOMES:
		if outcome == "Yes":
			chosen = route or state.get("route") or "Retread"
			on_route(stages, chosen)  # refuses an unknown route
			new["route"] = chosen
			new["position"] = sequence
			new["next"] = next_captures(stages, chosen, sequence)
		else:
			final = final_inspection(stages)
			new["result"] = "Not Retreadable"
			new["position"] = sequence
			new["next"] = [final["stage"]] if final else []
		return new

	if screen == "Inspection":
		route_now = new.get("route") or "Retread"
		if outcome == "Pass":
			new["result"] = "Passed"
		elif outcome == "Reject":
			new["result"] = "Rejected"
		elif outcome == "Redo":
			# B: back to the start of the line. The next recording points are the ones a tyre
			# meets after the first inspection — Repairs or Building on a retread.
			new["redo_count"] = int(new.get("redo_count") or 0) + 1
			entry = entry_inspection(stages)
			new["position"] = int(entry.get("sequence") or 0)
			new["next"] = next_captures(stages, route_now, new["position"])
			return new
		elif outcome == "Repair":
			# C: back to the repair bay, and only there.
			new["repair_count"] = int(new.get("repair_count") or 0) + 1
			repair = first_repair_point(stages, route_now)
			new["position"] = int(repair.get("sequence") or 0) - 1
			new["next"] = [repair["stage"]]
			return new
		new["position"] = sequence
		new["next"] = next_captures(stages, route_now, sequence)
		return new

	if screen == "Chambers" and outcome == "Into Chamber" and state.get("in_chamber"):
		raise RouteError("This tyre is already in a chamber.")
	if screen == "Chambers" and outcome == "Cured" and not state.get("in_chamber"):
		raise RouteError("This tyre has not been put into a chamber.")
	if screen == "Chambers" and outcome == "Into Chamber":
		# In a chamber the tyre cannot be recorded anywhere until the cure ends.
		new["next"] = [stage_name]
		new["in_chamber"] = 1
		return new
	if screen == "Chambers":
		new["in_chamber"] = 0

	route_now = new.get("route") or "Retread"
	new["position"] = sequence
	new["next"] = next_captures(stages, route_now, sequence)
	if screen == "Dispatch":
		new["status"] = "Dispatched"
	elif screen == "Office":
		new["status"] = "Invoiced"
	elif screen == "Deliver":
		new["status"] = "Delivered"
		new["next"] = []
	return new
