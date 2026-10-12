"""The floor screens' server side.

Every recording goes through record_stage() here. It asks the route engine whether the tyre is
due at that stage, writes the stage event and moves the Job Card on — so a tyre recorded from a
phone, from the desk or by the demo loader is moved by exactly the same rule.

Lists are read with get_list, so a login limited to one company sees only that company's tyres.
"""

import frappe
from frappe.utils import cint, get_datetime, now_datetime, time_diff_in_seconds

from fuse_retread import common, engine

# Outcomes that need a reason, and which list of reasons they draw from.
REASON_FOR = {"No": "Not Retreadable", "Reject": "Reject", "Redo": "Redo", "Repair": "Repair"}

JOB_FIELDS = [
	"name", "serial", "customer", "branch", "size", "brand", "photo", "route", "stage", "next_stages",
	"result", "status", "in_chamber", "redo_count", "last_event_at", "tread_pattern",
]


# ──────────────────────────────────────────────────────────────────────────────
# Recording
# ──────────────────────────────────────────────────────────────────────────────

def state_of(job):
	return {
		"route": job.route or "Retread",
		"position": cint(job.position),
		"next": common.split(job.next_stages),
		"result": job.result or "",
		"status": job.status or "In Progress",
		"redo_count": cint(job.redo_count),
		"repair_count": cint(job.repair_count),
		"in_chamber": cint(job.in_chamber),
	}


def record_stage(job, stage, outcome, operator=None, reason=None, route=None, tread_pattern=None,
		note=None, at=None, user=None, save=True, rows=None):
	"""Record one outcome at one stage on a Job Card. Refuses anything the route does not allow."""
	need = REASON_FOR.get(outcome)
	if need:
		if not reason:
			frappe.throw(f"Choose a reason: {outcome} needs one.", title="Reason needed")
		if frappe.db.get_value("FR Reason", reason, "outcome") != need:
			frappe.throw(f"{reason} is not a reason for {outcome}.", title="Wrong reason")
	try:
		new = engine.apply(rows or common.stages(), state_of(job), stage, outcome, route=route)
	except engine.RouteError as error:
		frappe.throw(str(error), title="Not due here")

	at = get_datetime(at) if at else now_datetime()
	job.route = new.get("route") or job.route
	job.position = new["position"]
	job.next_stages = "\n".join(new["next"])
	job.result = new.get("result") or ""
	job.status = new.get("status") or job.status
	job.redo_count = cint(new.get("redo_count"))
	job.repair_count = cint(new.get("repair_count"))
	job.in_chamber = cint(new.get("in_chamber"))
	job.stage = stage
	job.last_event_at = at
	if tread_pattern:
		job.tread_pattern = tread_pattern
	if outcome == "Delivered":
		job.delivered_on = at
	job.append(
		"events",
		{
			"stage": stage, "outcome": outcome, "reason": reason, "operator": operator, "at": at,
			"user": user or frappe.session.user, "note": note,
		},
	)
	if save:
		job.save()
	return job


def summary(job, rows=None):
	"""What a floor screen shows of one tyre."""
	rows = rows or common.stages()
	data = {field: job.get(field) for field in JOB_FIELDS}
	data["customer_name"] = frappe.db.get_value("Customer", job.customer, "customer_name") or job.customer
	data["next"] = common.split(job.next_stages)
	state = state_of(job)
	data["outcomes"] = {stage: engine.outcomes(rows, stage, state) for stage in data["next"]}
	return data


@frappe.whitelist()
def record(job, stage, outcome, operator=None, reason=None, route=None, tread_pattern=None, note=None):
	doc = frappe.get_doc("FR Job Card", job)
	doc.check_permission("write")
	record_stage(doc, stage, outcome, operator=operator or None, reason=reason or None, route=route or None,
		tread_pattern=tread_pattern or None, note=note or None)
	return summary(doc)


# ──────────────────────────────────────────────────────────────────────────────
# The home screen
# ──────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def bootstrap():
	rows = common.stages()
	waiting = _waiting_counts()
	return {
		"company": frappe.db.get_single_value("FR Settings", "company"),
		"own_prefix": common.own_prefix(),
		"screens": [
			{"stage": row["stage"], "screen": row["screen"], "suggested": cint(row["suggested"]),
				"waiting": waiting.get(row["stage"], 0)}
			for row in rows
			if row["screen"] not in ("None", "Office")
		],
		"sizes": frappe.get_all("FR Tyre Size", order_by="sort_order asc, name asc", pluck="name"),
		"brands": frappe.get_all("FR Tyre Brand", order_by="sort_order asc, name asc", pluck="name"),
		"patterns": frappe.get_all("FR Tread Pattern", fields=["name", "position"], order_by="name asc"),
		"branches": frappe.get_all("FR Branch", order_by="name asc", pluck="name"),
		"operators": frappe.get_all("FR Operator", filters={"disabled": 0}, order_by="name asc", pluck="name"),
		"reasons": _reasons(),
	}


def _reasons():
	grouped = {}
	for row in frappe.get_all(
		"FR Reason", filters={"disabled": 0}, fields=["name", "outcome", "icon"], order_by="sort_order asc, name asc"
	):
		grouped.setdefault(row.outcome, []).append({"reason": row.name, "icon": row.icon or "alert"})
	return grouped


def _active(filters=None, fields=None, limit=0, order_by="last_event_at asc"):
	"""Tyres not yet back with their owner, as this login may see them."""
	return frappe.get_list(
		"FR Job Card", filters=[["status", "!=", "Delivered"]] + (filters or []), fields=fields or JOB_FIELDS,
		order_by=order_by, limit_page_length=limit,
	)


def _waiting_counts():
	counts = {}
	for job in _active(fields=["next_stages"]):
		for stage in common.split(job.next_stages):
			counts[stage] = counts.get(stage, 0) + 1
	return counts


# ──────────────────────────────────────────────────────────────────────────────
# Finding a tyre
# ──────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def find(stage, digits):
	"""Tyres whose number ends with what was typed, the ones due at `stage` first."""
	digits = common.normalise(digits)
	if len(digits) < 2:
		return []
	rows = common.stages()
	jobs = _active([["serial", "like", f"%{digits}"]], fields=["name"], limit=20, order_by="last_event_at desc")
	if not jobs:
		jobs = _active([["serial", "like", f"%{digits}%"]], fields=["name"], limit=20, order_by="last_event_at desc")
	found = []
	for job in jobs:
		item = summary(frappe.get_doc("FR Job Card", job.name), rows)
		item["due"] = stage in item["next"]
		found.append(item)
	found.sort(key=lambda item: (not item["due"], item["serial"] or ""))
	return found


@frappe.whitelist()
def lookup(serial):
	"""Everything known about one tyre number, for Receive at Branch."""
	serial = common.normalise(serial)
	if not serial:
		return None
	if not frappe.db.exists("FR Casing", serial):
		return {"serial": serial, "known": False, "own_number": common.is_own_number(serial)}
	casing = frappe.get_doc("FR Casing", serial)
	casing.check_permission("read")
	from fuse_retread.office import casing_history

	history = casing_history(serial)
	open_job = next((job for job in history if job["status"] != "Delivered"), None)
	return {
		"serial": serial,
		"known": True,
		"customer": casing.customer,
		"customer_name": frappe.db.get_value("Customer", casing.customer, "customer_name") if casing.customer else "",
		"size": casing.size,
		"brand": casing.brand,
		"photo": casing.photo,
		"open_job": open_job["name"] if open_job else None,
		"history": history,
	}


@frappe.whitelist()
def customers(txt=""):
	"""Customers this login may book tyres in for, by name."""
	return frappe.get_list(
		"Customer",
		filters={"disabled": 0},
		or_filters=[["customer_name", "like", f"%{txt}%"], ["name", "like", f"%{txt}%"]] if txt else None,
		fields=["name", "customer_name"],
		order_by="customer_name asc",
		limit_page_length=30,
	)


# ──────────────────────────────────────────────────────────────────────────────
# Receive at Branch
# ──────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def issue_number():
	"""The next number the factory issues, taken once and never re-used.

	Read under a row lock so two branches booking in at the same moment cannot both get it.
	A number issued and then not used leaves a gap; that is cheaper than a duplicate.
	"""
	frappe.has_permission("FR Casing", "create", throw=True)
	prefix = common.own_prefix()
	frappe.db.sql(
		"select value from `tabSingles` where doctype='FR Settings' and field='next_own_number' for update"
	)
	number = cint(frappe.db.get_single_value("FR Settings", "next_own_number")) or 10001
	while frappe.db.exists("FR Casing", f"{prefix}{number}"):
		number += 1
	frappe.db.set_single_value("FR Settings", "next_own_number", number + 1)
	frappe.db.commit()
	return f"{prefix}{number}"


@frappe.whitelist()
def receive(customer, branch, serial, source="Manufacturer", size=None, brand=None, operator=None,
		dot_code=None, photo=None, promised_date=None):
	serial = common.normalise(serial)
	if not serial:
		frappe.throw("Enter the tyre number, or issue one.", title="No tyre number")
	if not customer:
		frappe.throw("Choose the customer the tyre belongs to.", title="No customer")
	company = common.company()
	rows = common.stages()
	receive_stage = common.stage_for_screen("Receive", rows)

	if frappe.db.exists("FR Casing", serial):
		open_job = frappe.db.get_value("FR Job Card", {"casing": serial, "status": ["!=", "Delivered"]}, "name")
		if open_job:
			frappe.throw(
				f"Tyre {serial} is already in, on {open_job}. It has to go back to its owner before it "
				"can be booked in again.",
				title="Already in",
			)
		casing = frappe.get_doc("FR Casing", serial)
		casing.customer = customer
		for field, value in (("size", size), ("brand", brand), ("photo", photo), ("dot_code", dot_code)):
			if value:
				casing.set(field, value)
		casing.save()
	else:
		casing = frappe.get_doc(
			{
				"doctype": "FR Casing", "serial": serial, "serial_source": source or "Manufacturer",
				"customer": customer, "company": company, "size": size, "brand": brand,
				"dot_code": dot_code, "photo": photo,
			}
		).insert()

	job = new_job(casing.name, customer, branch, company, receive_stage, promised_date=promised_date)
	record_stage(job, receive_stage, "Received", operator=operator or None, rows=rows)
	touch_casing(casing.name)
	return summary(job, rows)


def new_job(casing, customer, branch, company, receive_stage, promised_date=None, at=None):
	job = frappe.get_doc(
		{
			"doctype": "FR Job Card", "casing": casing, "customer": customer, "branch": branch,
			"company": company, "flow": "Customer Retread", "route": "Retread",
			"received_on": get_datetime(at) if at else now_datetime(), "promised_date": promised_date,
			"position": 0, "next_stages": receive_stage, "status": "In Progress",
		}
	)
	job.insert()
	return job


def touch_casing(casing):
	jobs = frappe.get_all("FR Job Card", filters={"casing": casing}, order_by="received_on desc", pluck="name")
	frappe.db.set_value("FR Casing", casing, {"visits": len(jobs), "last_job": jobs[0] if jobs else None},
		update_modified=False)


def _save(doc):
	if doc.is_new():
		doc.insert()
	else:
		doc.save()


# ──────────────────────────────────────────────────────────────────────────────
# Chambers
# ──────────────────────────────────────────────────────────────────────────────

def _open_load(chamber):
	return frappe.db.get_value(
		"FR Chamber Load", {"chamber": chamber, "status": ["in", ["Loading", "Curing"]]}, "name",
		order_by="creation desc",
	)


@frappe.whitelist()
def chamber_board():
	rows = common.stages()
	chambers_stage = common.stage_for_screen("Chambers", rows)
	board = []
	loaded = set()
	for chamber in frappe.get_all("FR Chamber", fields=["name", "capacity", "cure_minutes"], order_by="name asc"):
		name = _open_load(chamber.name)
		entry = {
			"chamber": chamber.name, "capacity": cint(chamber.capacity), "cure_minutes": cint(chamber.cure_minutes),
			"load": None, "status": "Idle", "tyres": [], "minutes_left": None,
		}
		if name:
			load = frappe.get_doc("FR Chamber Load", name)
			entry.update({
				"load": load.name, "status": load.status,
				"tyres": [{"job_card": t.job_card, "serial": t.serial, "customer": t.customer} for t in load.tyres],
			})
			loaded.update(t.job_card for t in load.tyres)
			if load.status == "Curing" and load.started_at:
				elapsed = time_diff_in_seconds(now_datetime(), load.started_at) / 60
				entry["minutes_left"] = max(0, round(cint(chamber.cure_minutes) - elapsed))
		board.append(entry)
	waiting = [
		{"job_card": job.name, "serial": job.serial, "customer": job.customer, "size": job.size}
		for job in _active([["next_stages", "like", f"%{chambers_stage}%"], ["in_chamber", "=", 0]])
		if job.name not in loaded and chambers_stage in common.split(job.next_stages)
	]
	return {"stage": chambers_stage, "chambers": board, "waiting": waiting}


@frappe.whitelist()
def load_tyre(chamber, job):
	chambers_stage = common.stage_for_screen("Chambers")
	doc = frappe.get_doc("FR Job Card", job)
	doc.check_permission("write")
	if chambers_stage not in common.split(doc.next_stages) or cint(doc.in_chamber):
		frappe.throw(
			f"Tyre {doc.serial} is not due for a chamber. Next for it: "
			f"{' or '.join(common.split(doc.next_stages)) or 'nothing'}.",
			title="Not due here",
		)
	for other in frappe.get_all("FR Chamber Load Tyre", filters={"job_card": job}, pluck="parent"):
		if frappe.db.get_value("FR Chamber Load", other, "status") == "Loading":
			chamber_name = frappe.db.get_value("FR Chamber Load", other, "chamber")
			frappe.throw(f"Tyre {doc.serial} is already loaded, in {chamber_name}.", title="Already loaded")
	name = _open_load(chamber)
	if name and frappe.db.get_value("FR Chamber Load", name, "status") == "Curing":
		frappe.throw(f"{chamber} is curing. Use another chamber, or wait for this cure to end.", title="Chamber busy")
	load = frappe.get_doc("FR Chamber Load", name) if name else frappe.get_doc(
		{"doctype": "FR Chamber Load", "chamber": chamber, "status": "Loading", "company": common.company()}
	)
	capacity = cint(frappe.db.get_value("FR Chamber", chamber, "capacity"))
	if capacity and len(load.tyres) >= capacity:
		frappe.throw(f"{chamber} is full ({capacity} tyres).", title="Chamber full")
	load.append("tyres", {"job_card": job, "serial": doc.serial, "customer": doc.customer})
	_save(load)
	return chamber_board()


@frappe.whitelist()
def unload_tyre(load, job):
	doc = frappe.get_doc("FR Chamber Load", load)
	doc.check_permission("write")
	if doc.status != "Loading":
		frappe.throw("Tyres can only come out of a chamber before the cure starts.")
	doc.tyres = [row for row in doc.tyres if row.job_card != job]
	doc.save()
	return chamber_board()


@frappe.whitelist()
def start_cure(load, operator=None, at=None):
	doc = frappe.get_doc("FR Chamber Load", load)
	doc.check_permission("write")
	if doc.status != "Loading" or not doc.tyres:
		frappe.throw("Only a loading chamber with tyres in it can start a cure.")
	rows = common.stages()
	stage = common.stage_for_screen("Chambers", rows)
	for row in doc.tyres:
		job = frappe.get_doc("FR Job Card", row.job_card)
		record_stage(job, stage, "Into Chamber", operator=operator or None, at=at, save=False, rows=rows)
		job.chamber_load = doc.name
		job.save()
	doc.status = "Curing"
	doc.started_at = get_datetime(at) if at else now_datetime()
	doc.operator = operator or doc.operator
	doc.save()
	return chamber_board()


@frappe.whitelist()
def end_cure(load, operator=None, at=None):
	doc = frappe.get_doc("FR Chamber Load", load)
	doc.check_permission("write")
	if doc.status != "Curing":
		frappe.throw("This chamber is not curing.")
	rows = common.stages()
	stage = common.stage_for_screen("Chambers", rows)
	for row in doc.tyres:
		job = frappe.get_doc("FR Job Card", row.job_card)
		record_stage(job, stage, "Cured", operator=operator or None, at=at, rows=rows)
	doc.status = "Done"
	doc.ended_at = get_datetime(at) if at else now_datetime()
	doc.save()
	return chamber_board()


# ──────────────────────────────────────────────────────────────────────────────
# Dispatch
# ──────────────────────────────────────────────────────────────────────────────

def _open_dispatch(branch):
	return frappe.db.get_value("FR Dispatch", {"branch": branch, "status": "Open"}, "name", order_by="creation desc")


@frappe.whitelist()
def dispatch_board(branch):
	stage = common.stage_for_screen("Dispatch")
	name = _open_dispatch(branch)
	load = frappe.get_doc("FR Dispatch", name) if name else None
	on_load = {row.job_card for row in load.tyres} if load else set()
	ready = [
		{"job_card": job.name, "serial": job.serial, "customer": job.customer, "result": job.result, "size": job.size}
		for job in _active([["branch", "=", branch], ["next_stages", "like", f"%{stage}%"]])
		if job.name not in on_load and stage in common.split(job.next_stages)
	]
	return {
		"stage": stage,
		"branch": branch,
		"dispatch": load.name if load else None,
		"tyres": [
			{"job_card": r.job_card, "serial": r.serial, "customer": r.customer, "result": r.result}
			for r in (load.tyres if load else [])
		],
		"ready": ready,
	}


@frappe.whitelist()
def add_to_dispatch(branch, job):
	stage = common.stage_for_screen("Dispatch")
	doc = frappe.get_doc("FR Job Card", job)
	doc.check_permission("write")
	if stage not in common.split(doc.next_stages):
		frappe.throw(
			f"Tyre {doc.serial} is not ready to dispatch. Next for it: "
			f"{' or '.join(common.split(doc.next_stages)) or 'nothing'}.",
			title="Not ready",
		)
	if doc.branch and doc.branch != branch:
		frappe.throw(f"Tyre {doc.serial} came in at {doc.branch}. It goes back on {doc.branch}'s load.",
			title="Wrong branch")
	name = _open_dispatch(branch)
	load = frappe.get_doc("FR Dispatch", name) if name else frappe.get_doc(
		{"doctype": "FR Dispatch", "branch": branch, "status": "Open", "company": common.company()}
	)
	if not any(row.job_card == job for row in load.tyres):
		load.append("tyres", {"job_card": job, "serial": doc.serial, "customer": doc.customer, "result": doc.result})
		_save(load)
	return dispatch_board(branch)


@frappe.whitelist()
def remove_from_dispatch(dispatch, job):
	doc = frappe.get_doc("FR Dispatch", dispatch)
	doc.check_permission("write")
	if doc.status != "Open":
		frappe.throw("This load has already gone.")
	doc.tyres = [row for row in doc.tyres if row.job_card != job]
	doc.save()
	return dispatch_board(doc.branch)


@frappe.whitelist()
def send_dispatch(dispatch, operator=None, at=None):
	doc = frappe.get_doc("FR Dispatch", dispatch)
	doc.check_permission("write")
	if doc.status != "Open" or not doc.tyres:
		frappe.throw("Only an open load with tyres on it can be sent.")
	rows = common.stages()
	stage = common.stage_for_screen("Dispatch", rows)
	for row in doc.tyres:
		job = frappe.get_doc("FR Job Card", row.job_card)
		record_stage(job, stage, "Dispatched", operator=operator or None, at=at, save=False, rows=rows)
		job.dispatch = doc.name
		job.save()
	doc.status = "Sent"
	doc.sent_at = get_datetime(at) if at else now_datetime()
	doc.operator = operator or doc.operator
	doc.save()
	return dispatch_board(doc.branch)


# ──────────────────────────────────────────────────────────────────────────────
# Deliver to Customer
# ──────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def delivery_list(customer):
	stage = common.stage_for_screen("Deliver")
	jobs = _active([["customer", "=", customer], ["status", "in", ["Dispatched", "Invoiced"]]], order_by="serial asc")
	return {
		"stage": stage,
		"customer": customer,
		"customer_name": frappe.db.get_value("Customer", customer, "customer_name") or customer,
		"tyres": [
			{
				"job_card": job.name, "serial": job.serial, "size": job.size, "brand": job.brand, "photo": job.photo,
				"result": job.result, "status": job.status, "due": stage in common.split(job.next_stages),
			}
			for job in jobs
		],
	}


@frappe.whitelist()
def check_delivery(customer, digits):
	"""The tyre a number points at, for this customer — or the refusal if it is someone else's."""
	digits = common.normalise(digits)
	if len(digits) < 2:
		return {"matches": []}
	jobs = _active([["serial", "like", f"%{digits}"], ["status", "in", ["Dispatched", "Invoiced"]]])
	theirs = [job for job in jobs if job.customer == customer]
	if theirs:
		return {"matches": [job.name for job in theirs]}
	if jobs:
		owner = frappe.db.get_value("Customer", jobs[0].customer, "customer_name") or jobs[0].customer
		name = frappe.db.get_value("Customer", customer, "customer_name") or customer
		return {"matches": [], "refused": f"Tyre {jobs[0].serial} belongs to {owner}. It cannot go to {name}."}
	return {"matches": []}


@frappe.whitelist()
def deliver(customer, jobs, operator=None):
	jobs = frappe.parse_json(jobs) if isinstance(jobs, str) else jobs
	if not jobs:
		frappe.throw("Tick the tyres going back to the customer first.")
	rows = common.stages()
	stage = common.stage_for_screen("Deliver", rows)
	# Every tyre is checked before any is recorded, so a wrong tyre in the batch stops the lot.
	docs = [frappe.get_doc("FR Job Card", name) for name in jobs]
	for job in docs:
		job.check_permission("write")
		if job.customer != customer:
			frappe.throw(f"Tyre {job.serial} is not this customer's. Nothing was delivered.", title="Wrong customer")
		if stage not in common.split(job.next_stages):
			frappe.throw(f"Tyre {job.serial} has not been invoiced yet. Nothing was delivered.", title="Not invoiced")
	for job in docs:
		record_stage(job, stage, "Delivered", operator=operator or None, rows=rows)
	return {"delivered": [job.serial for job in docs], "list": delivery_list(customer)}
