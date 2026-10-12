"""The retread demo profile: a retread factory already running, with tyres at every stage.

Demo setup, not product. Run on the Fuse demo site from the Job Card list (menu: Load Retread
Demo). Every name is fictitious — no prospect's name appears anywhere. Nothing is read from or
written to Intacct.

What it makes:
  * its own company, "Retreading", beside the manufacturing and construction ones, with a
    customer group of the same name;
  * six transport customers, three branches, sizes with prices, brands, tread patterns, the
    reject / redo / repair reasons, the floor operators and three curing chambers;
  * the presenter profile: Role Profile and Module Profile "Retread Presenter", which show only
    the retread tiles, and the retread tiles hidden from every other presenter profile. Given a
    presenter login that already exists, that login is put on them and limited to the company;
  * about 160 tyres moved through the real route engine with back-dated history: a week of
    finished work, then today's line — tyres waiting at every stage, a chamber curing, one
    loading, loads at the branches, two redos this morning, a casing that failed inspection;
  * a returning tyre, first retreaded seven months ago, for the claims story.

"Start again" deletes every retread tyre, job, chamber load and dispatch first and rebuilds the
line around the current time, so the morning of a demo shows a morning's work.
"""

import random
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import cint, get_datetime, now_datetime

from fuse_retread import common, floor, registry

COMPANY = "Retreading"
COMPANY_ABBR = "RTR"
GROUP = "Retreading"
PROFILE = "Retread Presenter"
PRESENTER_ROLES = ["Retread Floor", "Retread Office", "Sales User"]
BLOCK_MODULES = ["Manufacturing", "Fuse Manufacturing", "Quality Management", "Fuse Construction", "Projects"]

CUSTOMERS = {
	# customer: the branches its tyres come in at
	"Karoo Freight Lines (Pty) Ltd": ["Bellville Branch", "George Branch"],
	"Cape Coastal Transport (Pty) Ltd": ["Bellville Branch"],
	"Boland Bulk Haulers (Pty) Ltd": ["Paarl Branch"],
	"Highveld Tippers (Pty) Ltd": ["Bellville Branch"],
	"Garden Route Logistics (Pty) Ltd": ["George Branch"],
	"Winelands Fresh Distribution (Pty) Ltd": ["Paarl Branch"],
}
BRANCHES = [("Bellville Branch", "Bellville"), ("Paarl Branch", "Paarl"), ("George Branch", "George")]
# (size, retread price, repair price, order, share of the work)
SIZES = [
	("315/80R22.5", 3450, 650, 10, 40),
	("385/65R22.5", 3890, 700, 20, 20),
	("295/80R22.5", 3250, 620, 30, 15),
	("12R22.5", 3150, 600, 40, 10),
	("11R22.5", 2950, 580, 50, 10),
	("275/70R22.5", 2850, 560, 60, 5),
]
BRANDS = {"Bridgestone": "BS", "Michelin": "MC", "Continental": "CT", "Goodyear": "GY", "Dunlop": "DL",
	"Firestone": "FS", "Hankook": "HK"}
PATTERNS = [("Drive D-Grip", "Drive"), ("Steer S-Line", "Steer"), ("Trailer T-Rib", "Trailer"),
	("Mixed M-Block", "All Position")]
REASONS = [
	("Casing too old (DOT)", "Not Retreadable", "clock"),
	("Bead damage", "Not Retreadable", "circle"),
	("Sidewall cut", "Not Retreadable", "cut"),
	("Ply separation", "Not Retreadable", "layers"),
	("Separation after cure", "Reject", "layers"),
	("Casing damage found", "Reject", "alert"),
	("Blister or trapped air", "Redo", "droplet"),
	("Tread not centred", "Redo", "ruler"),
	("Poor bond", "Redo", "flame"),
	("Spot repair needed", "Repair", "wrench"),
	("Nail hole found", "Repair", "nail"),
	("Small cut in tread", "Repair", "cut"),
]
OPERATORS = {
	"Receive at Branch": {"Bellville Branch": "Marlene Petersen", "Paarl Branch": "Johan Visser", "George Branch": "Zanele Mthembu"},
	"1st Inspection": ["Thabo Mokoena", "Gert Fourie"],
	"Repairs": ["Ruan Jacobs"],
	"Building": ["Annelie Steyn", "Sizwe Ndlovu"],
	"Chambers": ["Lindiwe Zulu"],
	"Final Inspection": ["Gert Fourie", "Thabo Mokoena"],
	"Dispatch": ["Naledi Khumalo"],
}
CHAMBERS = [("Chamber 1", 12, 180), ("Chamber 2", 12, 180), ("Chamber 3", 16, 200)]

# The tyre that has been in before: first retreaded seven months ago, booked in live in the demo.
RETURNING = {"serial": "MC5821946", "brand": "Michelin", "size": "315/80R22.5",
	"customer": "Karoo Freight Lines (Pty) Ltd", "branch": "Bellville Branch"}

DAY_START = time(7, 0)
DAY_END = time(16, 30)
CURE_HOURS = 3.0

# Working hours before each step, as a (low, high) range.
GAP = {
	"1st Inspection": (3, 18), "Repairs": (1, 6), "Building": (1, 9), "Into Chamber": (0.3, 3),
	"Cured": (CURE_HOURS, CURE_HOURS), "Final Inspection": (0.3, 4), "Dispatched": (1, 14),
	"Invoiced": (2, 12), "Delivered": (3, 24),
}


def is_demo_site():
	"""Only a site whose config sets `fuse_demo_site` is a demo site. A client's never is."""
	return bool(frappe.conf.get("fuse_demo_site"))


def boot(bootinfo):
	bootinfo.fuse_demo_site = is_demo_site()


@frappe.whitelist()
def load(presenter=None, reset=0):
	frappe.only_for("System Manager")
	if not is_demo_site():
		frappe.throw(
			"The retread demo loads only on the Fuse demo site — set fuse_demo_site in that site's config. "
			"It never loads on a client's site."
		)
	from fuse_retread.install import after_install

	after_install()
	_company()
	_masters()
	_settings()
	profiles = _presenter_profiles()
	who = _presenter(presenter) if presenter else None

	if cint(reset):
		_clear()
	if frappe.db.count("FR Job Card", {"company": COMPANY}):
		frappe.db.commit()
		return {"summary": "The retread demo is already loaded. Tick <b>Start again</b> to rebuild it around the "
			f"current time.<br>Presenter profiles: {profiles}." + (f"<br>Presenter: {who}." if who else "")}

	built = _build_line(random.Random(20261012))
	frappe.db.commit()
	return {"summary": _summary(built, profiles, who)}


# ──────────────────────────────────────────────────────────────────────────────
# Masters
# ──────────────────────────────────────────────────────────────────────────────

def _company():
	if not frappe.db.exists("Company", COMPANY):
		frappe.get_doc({
			"doctype": "Company", "company_name": COMPANY, "abbr": COMPANY_ABBR, "country": "South Africa",
			"default_currency": "ZAR", "create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
		}).insert(ignore_permissions=True)


def _ensure(doctype, name, values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc(dict({"doctype": doctype}, **values)).insert(ignore_permissions=True)


def _masters():
	if not frappe.db.exists("Customer Group", GROUP):
		root = frappe.db.get_value("Customer Group", {"is_group": 1, "parent_customer_group": ("is", "not set")}, "name")
		frappe.get_doc({"doctype": "Customer Group", "customer_group_name": GROUP, "parent_customer_group": root,
			"is_group": 0}).insert(ignore_permissions=True)
	territory = "South Africa" if frappe.db.exists("Territory", "South Africa") else frappe.get_all(
		"Territory", filters={"is_group": 0}, pluck="name", limit=1)[0]
	for customer in CUSTOMERS:
		if not frappe.db.get_value("Customer", {"customer_name": customer}):
			frappe.get_doc({"doctype": "Customer", "customer_name": customer, "customer_group": GROUP,
				"territory": territory, "customer_type": "Company"}).insert(ignore_permissions=True)
	for branch, town in BRANCHES:
		_ensure("FR Branch", branch, {"branch_name": branch, "town": town})
	for size, retread, repair, order, _share in SIZES:
		_ensure("FR Tyre Size", size, {"size": size, "retread_price": retread, "repair_price": repair, "sort_order": order})
	for i, brand in enumerate(BRANDS):
		_ensure("FR Tyre Brand", brand, {"brand": brand, "sort_order": i + 1})
	for pattern, position in PATTERNS:
		_ensure("FR Tread Pattern", pattern, {"pattern": pattern, "position": position})
	for i, (reason, outcome, icon) in enumerate(REASONS):
		_ensure("FR Reason", reason, {"reason": reason, "outcome": outcome, "icon": icon, "sort_order": i + 1})
	names = {name for stage, people in OPERATORS.items() for name in (people.values() if isinstance(people, dict) else people)}
	for name in sorted(names):
		_ensure("FR Operator", name, {"operator_name": name})
	for chamber, capacity, minutes in CHAMBERS:
		_ensure("FR Chamber", chamber, {"chamber_name": chamber, "capacity": capacity, "cure_minutes": minutes})


def _settings():
	settings = frappe.get_single("FR Settings")
	settings.company = COMPANY
	settings.daily_target = 20
	settings.vat_percent = settings.vat_percent or 15
	settings.own_prefix = settings.own_prefix or "P"
	settings.next_own_number = cint(settings.next_own_number) or 10001
	settings.invoice_item = settings.invoice_item or "RETREAD"
	settings.repair_item = settings.repair_item or "REPAIR"
	settings.save(ignore_permissions=True)


def _customer(name):
	return frappe.db.get_value("Customer", {"customer_name": name}) or name


# ──────────────────────────────────────────────────────────────────────────────
# The presenter
# ──────────────────────────────────────────────────────────────────────────────

def _other_keys():
	"""Every Fuse Home key on this site except this app's and Support, for the presenter to hide."""
	keys = set()
	try:
		from fuse_core import modules

		keys.update(module["key"] for module in modules.all_modules())
	except Exception:
		pass
	try:
		from fuse_theme import api

		keys.update(tile.get("module", tile["key"]) for tile in api._all_tiles())
	except Exception:
		pass
	keys.discard(registry.MODULE_KEY)
	keys.discard("support")
	return sorted(keys)


def _save_unlocked(doc):
	"""Save a Role or Module Profile, clearing a lock a failed earlier run left behind.

	Saving a profile queues a job that re-applies it to its users, and locks the profile until
	that job runs. The job is queued after commit, so a load that fails later rolls back, the
	job never runs, and the lock stays for hours: every retry stops at "Document Queued".
	The lock is keyed by doctype and name, so it can be cleared before the profile exists.
	"""
	if doc.is_new():
		doc.name = doc.get("role_profile") or doc.get("module_profile_name")
	doc.unlock()
	doc.save(ignore_permissions=True)


def _presenter_profiles():
	if frappe.db.exists("Role Profile", PROFILE):
		role_profile = frappe.get_doc("Role Profile", PROFILE)
		role_profile.set("roles", [])
	else:
		role_profile = frappe.new_doc("Role Profile")
		role_profile.role_profile = PROFILE
	for role in PRESENTER_ROLES:
		role_profile.append("roles", {"role": role})
	_save_unlocked(role_profile)

	hidden_field = frappe.get_meta("Module Profile").has_field("fuse_hidden_modules")
	module_profile = frappe.get_doc("Module Profile", PROFILE) if frappe.db.exists("Module Profile", PROFILE) else \
		frappe.get_doc({"doctype": "Module Profile", "module_profile_name": PROFILE})
	module_profile.set("block_modules", [])
	for module in BLOCK_MODULES:
		if frappe.db.exists("Module Def", module):
			module_profile.append("block_modules", {"module": module})
	if hidden_field:
		module_profile.fuse_hidden_modules = "\n".join(_other_keys())
	_save_unlocked(module_profile)

	# The retread tiles leave every other presenter's Fuse Home, so each industry sees only its own.
	others = []
	if hidden_field:
		for name, text in frappe.get_all("Module Profile", filters={"name": ["!=", PROFILE]},
				fields=["name", "fuse_hidden_modules"], as_list=True):
			lines = common.split((text or "").replace(",", "\n"))
			if lines and registry.MODULE_KEY not in lines:
				frappe.db.set_value("Module Profile", name, "fuse_hidden_modules", "\n".join(lines + [registry.MODULE_KEY]))
				others.append(name)
	return f"{PROFILE} (role and module profile)" + (f"; retread tiles hidden from {', '.join(others)}" if others else "")


def _presenter(email):
	"""Put an existing login on the retread presenter profiles and limit it to the company.

	Never creates a login: that is done by a person, with a password nobody else knows.
	"""
	email = (email or "").strip()
	# The profile replaces the login's roles. Never do that to an administrator or to whoever is
	# running the loader: they would lock themselves out of their own site.
	if email in ("Administrator", frappe.session.user) or "System Manager" in frappe.get_roles(email):
		frappe.throw(f"{email} is an administrator login. Use a separate presenter login.", title="Not a presenter login")
	if not frappe.db.exists("User", email):
		frappe.throw(f"There is no user {email}. Create the login first, then load again.", title="No such user")
	user = frappe.get_doc("User", email)
	user.role_profile_name = PROFILE
	if user.meta.has_field("role_profiles"):
		user.set("role_profiles", [{"role_profile": PROFILE}])
	user.module_profile = PROFILE
	user.save(ignore_permissions=True)
	for allow, value in (("Company", COMPANY), ("Customer Group", GROUP)):
		if not frappe.db.exists("User Permission", {"user": email, "allow": allow, "for_value": value}):
			frappe.get_doc({"doctype": "User Permission", "user": email, "allow": allow, "for_value": value,
				"apply_to_all_doctypes": 1, "is_default": 1}).insert(ignore_permissions=True)
	return email


# ──────────────────────────────────────────────────────────────────────────────
# Working time
# ──────────────────────────────────────────────────────────────────────────────

def _snap_back(moment):
	"""The latest working moment at or before `moment` (weekdays, 07:00 to 16:30)."""
	while True:
		if moment.weekday() >= 5:
			moment = datetime.combine(moment.date() - timedelta(days=moment.weekday() - 4), DAY_END)
		elif moment.time() > DAY_END:
			moment = datetime.combine(moment.date(), DAY_END)
		elif moment.time() < DAY_START:
			moment = datetime.combine(moment.date() - timedelta(days=1), DAY_END)
		else:
			return moment


def _retreat(moment, hours):
	"""`moment` moved back by `hours` of working time."""
	moment = _snap_back(moment)
	left = timedelta(hours=hours)
	while left > timedelta(0):
		start = datetime.combine(moment.date(), DAY_START)
		available = moment - start
		if left <= available:
			return moment - left
		left -= available
		moment = _snap_back(start - timedelta(minutes=1))
	return moment


# ──────────────────────────────────────────────────────────────────────────────
# The line
# ──────────────────────────────────────────────────────────────────────────────

def _path(rng, route="Retread", repairs=False, failure=None, not_retreadable=False):
	"""Every step a tyre takes from the branch back to its owner, as (stage, outcome, extra)."""
	op = lambda stage: rng.choice(OPERATORS[stage])  # noqa: E731
	reason = lambda outcome: rng.choice([r for r, o, _i in REASONS if o == outcome])  # noqa: E731
	steps = [("Receive at Branch", "Received", {})]
	if not_retreadable:
		steps.append(("1st Inspection", "No", {"reason": reason("Not Retreadable"), "operator": op("1st Inspection")}))
		steps.append(("Final Inspection", "Reject", {"reason": reason("Reject"), "operator": op("Final Inspection")}))
	else:
		steps.append(("1st Inspection", "Yes", {"route": route, "operator": op("1st Inspection")}))
		pattern = rng.choice(PATTERNS)[0]

		def line(with_repairs):
			out = []
			if with_repairs or route == "Repair Only":
				out.append(("Repairs", "Done", {"operator": op("Repairs")}))
			if route == "Retread":
				out.append(("Building", "Done", {"operator": op("Building"), "tread_pattern": pattern}))
			out.append(("Chambers", "Into Chamber", {"operator": op("Chambers")}))
			out.append(("Chambers", "Cured", {"operator": op("Chambers")}))
			return out

		steps += line(repairs)
		if failure in ("Redo", "Repair"):
			steps.append(("Final Inspection", failure, {"reason": reason(failure), "operator": op("Final Inspection")}))
			steps += line(failure == "Repair")
			steps.append(("Final Inspection", "Pass", {"operator": op("Final Inspection")}))
		elif failure == "Reject":
			steps.append(("Final Inspection", "Reject", {"reason": reason("Reject"), "operator": op("Final Inspection")}))
		else:
			steps.append(("Final Inspection", "Pass", {"operator": op("Final Inspection")}))
	steps += [("Dispatch", "Dispatched", {"operator": op("Dispatch")}), ("Invoice", "Invoiced", {}),
		("Deliver to Customer", "Delivered", {})]
	return steps


def _cut(steps, last):
	"""The steps up to and including the last one recorded with outcome `last` (or stage:outcome)."""
	for i in range(len(steps) - 1, -1, -1):
		stage, outcome, _extra = steps[i]
		if last in (outcome, f"{stage}:{outcome}"):
			return steps[: i + 1]
	return steps


def _times(rng, steps, end_at):
	"""Working-time timestamps for each step, counted back from the last one."""
	times = [end_at]
	for stage, outcome, _extra in reversed(steps[1:]):
		key = outcome if outcome in GAP else stage
		low, high = GAP.get(key, (1, 6))
		times.append(_retreat(times[-1], rng.uniform(low, high)))
	return list(reversed(times))


class Serials:
	"""Tyre numbers that look real and never share their last four digits, so a demo search for
	four digits always lands on one tyre."""

	def __init__(self, rng, prefix, start):
		self.rng, self.prefix, self.next_own, self.tails = rng, prefix, start, set()

	def take(self, brand, own=False):
		while True:
			if own:
				serial = f"{self.prefix}{self.next_own}"
				self.next_own += 1
			else:
				serial = f"{BRANDS[brand]}{self.rng.randint(1000000, 9999999)}"
			tail = serial[-4:]
			if tail not in self.tails and not frappe.db.exists("FR Casing", serial):
				self.tails.add(tail)
				return serial


def _size(rng):
	return rng.choices([s[0] for s in SIZES], weights=[s[4] for s in SIZES])[0]


def _build_line(rng):
	now = _snap_back(now_datetime())
	prefix = common.own_prefix()
	serials = Serials(rng, prefix, cint(frappe.db.get_single_value("FR Settings", "next_own_number")) or 10001)
	serials.tails.add(RETURNING["serial"][-4:])
	customers = list(CUSTOMERS)
	plans = []

	def plan(last, hours_ago, customer=None, branch=None, tag=None, **path):
		customer = customer or rng.choice(customers)
		branch = branch or rng.choice(CUSTOMERS[customer])
		steps = _cut(_path(rng, **path), last)
		end_at = _retreat(now, rng.uniform(*hours_ago)) if isinstance(hours_ago, tuple) else hours_ago
		plans.append({"customer": customer, "branch": branch, "steps": steps, "times": _times(rng, steps, end_at),
			"brand": rng.choice(list(BRANDS)), "size": _size(rng), "own": rng.random() < 0.1, "tag": tag})

	# A week of finished work, a few of them redone, repaired or rejected along the way.
	for i in range(90):
		failure = "Redo" if i % 15 == 3 else "Repair" if i % 23 == 5 else "Reject" if i % 19 == 7 else None
		plan("Delivered", (6, 62), failure=failure, repairs=rng.random() < 0.25, not_retreadable=(i % 31 == 11))
	# Back at the branches. Cape Coastal's are the delivery demo; Karoo's two share their load.
	for _ in range(3):
		plan("Invoiced", (1, 6), customer="Cape Coastal Transport (Pty) Ltd", branch="Bellville Branch", tag="deliver")
	plan("Dispatched", (0.5, 3), customer="Cape Coastal Transport (Pty) Ltd", branch="Bellville Branch", tag="deliver")
	for _ in range(2):
		plan("Dispatched", (0.5, 3), customer="Karoo Freight Lines (Pty) Ltd", branch="Bellville Branch", tag="refuse")
	for _ in range(3):
		plan("Invoiced", (1, 10))
	for _ in range(3):
		plan("Dispatched", (1, 8))
	# Finished today, waiting for a load. Two are already on Paarl's.
	for _ in range(2):
		plan("Pass", (0.3, 4), customer="Boland Bulk Haulers (Pty) Ltd", branch="Paarl Branch", tag="paarl_load")
	for _ in range(7):
		plan("Pass", (0.2, 5), repairs=rng.random() < 0.3)
	plan("Reject", (1, 6), failure="Reject")
	# Cured, waiting for Final Inspection.
	for _ in range(6):
		plan("Cured", (0.1, 3))
	# Curing now in Chamber 2, which went in seventy minutes ago.
	curing_at = _retreat(now, 70 / 60)
	for _ in range(10):
		plan("Into Chamber", curing_at, tag="curing")
	# Built, four of them loaded into Chamber 1, six waiting for a chamber.
	for _ in range(4):
		plan("Building:Done", (0.2, 2), tag="loading")
	for _ in range(6):
		plan("Building:Done", (0.2, 4))
	# Two redone this morning: back to waiting for Building.
	for _ in range(2):
		plan("Redo", (0.5, 2.5), failure="Redo")
	# Through first inspection, waiting for Building; four needed Repairs first.
	for i in range(10):
		plan("Repairs:Done" if i < 4 else "1st Inspection:Yes", (0.5, 12), repairs=i < 4)
	# Repair-only jobs waiting for the repair bay; one has waited since yesterday.
	plan("1st Inspection:Yes", (14, 18), route="Repair Only")
	for _ in range(2):
		plan("1st Inspection:Yes", (0.5, 6), route="Repair Only")
	# Waiting for first inspection: two have sat at the factory for three days.
	for _ in range(2):
		plan("Received", (26, 30))
	for _ in range(6):
		plan("Received", (0.2, 8))
	# Failed first inspection, waiting for Final Inspection to confirm the reject.
	for _ in range(2):
		plan("No", (0.5, 5), not_retreadable=True)

	rows = common.stages()
	made = {"jobs": 0, "curing": [], "loading": [], "deliver": [], "refuse": [], "paarl_load": []}

	# The returning tyre's first visit, seven months ago.
	old = _cut(_path(rng), "Delivered")
	_insert(RETURNING["serial"], RETURNING["brand"], RETURNING["size"], RETURNING["customer"], RETURNING["branch"],
		old, _times(rng, old, _retreat(now - timedelta(days=212), 2)), rows, own=False)
	made["jobs"] += 1

	for item in sorted(plans, key=lambda p: p["times"][0]):
		serial = serials.take(item["brand"], own=item["own"])
		job = _insert(serial, item["brand"], item["size"], item["customer"], item["branch"], item["steps"], item["times"],
			rows, own=item["own"])
		made["jobs"] += 1
		if item["tag"]:
			made[item["tag"]].append(job)

	frappe.db.set_single_value("FR Settings", "next_own_number", serials.next_own)
	_chambers(made, curing_at)
	_branch_loads(made)
	return made


def _insert(serial, brand, size, customer, branch, steps, times, rows, own=False):
	customer = _customer(customer)
	if not frappe.db.exists("FR Casing", serial):
		frappe.get_doc({"doctype": "FR Casing", "serial": serial, "serial_source": "Factory" if own else "Manufacturer",
			"customer": customer, "company": COMPANY, "size": size, "brand": brand}).insert(ignore_permissions=True)
		frappe.db.set_value("FR Casing", serial, "creation", times[0], update_modified=False)
	else:
		frappe.db.set_value("FR Casing", serial, "customer", customer, update_modified=False)
	job = frappe.get_doc({
		"doctype": "FR Job Card", "casing": serial, "customer": customer, "branch": branch, "company": COMPANY,
		"flow": "Customer Retread", "route": "Retread", "received_on": times[0], "position": 0,
		"next_stages": steps[0][0], "status": "In Progress",
		"promised_date": (get_datetime(times[0]) + timedelta(days=6)).date(),
	})
	receive_operator = OPERATORS["Receive at Branch"].get(branch)
	for (stage, outcome, extra), at in zip(steps, times, strict=True):
		operator = extra.get("operator") or (receive_operator if stage in ("Receive at Branch", "Deliver to Customer") else None)
		floor.record_stage(job, stage, outcome, operator=operator, reason=extra.get("reason"), route=extra.get("route"),
			tread_pattern=extra.get("tread_pattern"), at=at, save=False, rows=rows)
		if outcome == "Invoiced":
			job.price = _price(job)
	job.insert(ignore_permissions=True)
	frappe.db.set_value("FR Job Card", job.name, "creation", times[0], update_modified=False)
	floor.touch_casing(serial)
	return job.name


def _price(job):
	if job.result in ("Rejected", "Not Retreadable"):
		return 0
	field = "repair_price" if job.route == "Repair Only" else "retread_price"
	return frappe.db.get_value("FR Tyre Size", job.size, field) or 0


def _row(job, with_result=False):
	fields = ["serial", "customer"] + (["result"] if with_result else [])
	values = frappe.db.get_value("FR Job Card", job, fields, as_dict=True)
	return dict(values, job_card=job)


def _chambers(made, curing_at):
	"""Chamber 2 curing the ten that went in seventy minutes ago; Chamber 1 loading four more."""
	if made["curing"]:
		load = frappe.get_doc({"doctype": "FR Chamber Load", "chamber": "Chamber 2", "status": "Curing",
			"company": COMPANY, "started_at": curing_at, "operator": OPERATORS["Chambers"][0]})
		for job in made["curing"]:
			load.append("tyres", _row(job))
		load.insert(ignore_permissions=True)
		for job in made["curing"]:
			frappe.db.set_value("FR Job Card", job, "chamber_load", load.name, update_modified=False)
	if made["loading"]:
		load = frappe.get_doc({"doctype": "FR Chamber Load", "chamber": "Chamber 1", "status": "Loading", "company": COMPANY})
		for job in made["loading"]:
			load.append("tyres", _row(job))
		load.insert(ignore_permissions=True)


def _branch_loads(made):
	"""A sent load for every branch holding tyres at it, and Paarl's next load half filled."""
	at_branch = frappe.get_all("FR Job Card", filters={"company": COMPANY, "status": ["in", ["Dispatched", "Invoiced"]]},
		fields=["name", "branch", "serial", "customer", "result"])
	by_branch = {}
	for job in at_branch:
		by_branch.setdefault(job.branch, []).append(job)
	for branch, jobs in by_branch.items():
		sent = max(
			frappe.db.get_value("FR Job Event", {"parent": job.name, "outcome": "Dispatched"}, "at") for job in jobs
		)
		load = frappe.get_doc({"doctype": "FR Dispatch", "branch": branch, "status": "Sent", "company": COMPANY,
			"sent_at": sent, "operator": OPERATORS["Dispatch"][0]})
		for job in jobs:
			load.append("tyres", {"job_card": job.name, "serial": job.serial, "customer": job.customer, "result": job.result})
		load.insert(ignore_permissions=True)
		for job in jobs:
			frappe.db.set_value("FR Job Card", job.name, "dispatch", load.name, update_modified=False)
	if made["paarl_load"]:
		load = frappe.get_doc({"doctype": "FR Dispatch", "branch": "Paarl Branch", "status": "Open", "company": COMPANY})
		for job in made["paarl_load"]:
			load.append("tyres", _row(job, with_result=True))
		load.insert(ignore_permissions=True)


def _clear():
	"""Every retread tyre, job, chamber load and dispatch on the demo site. Demo only."""
	for child, parent in (("FR Job Event", "FR Job Card"), ("FR Chamber Load Tyre", "FR Chamber Load"),
			("FR Dispatch Tyre", "FR Dispatch")):
		frappe.db.delete(child, {"parenttype": parent})
	for doctype in ("FR Job Card", "FR Chamber Load", "FR Dispatch", "FR Casing"):
		frappe.db.delete(doctype)
	frappe.db.set_single_value("FR Settings", "next_own_number", 10001)


def _summary(made, profiles, who):
	def tails(jobs):
		return ", ".join(frappe.db.get_value("FR Job Card", job, "serial")[-4:] for job in jobs)

	return (
		f"{made['jobs']} tyres loaded around the current time.<br>"
		f"<b>Returning tyre</b> for the claims story: book in <b>{RETURNING['serial']}</b> for Karoo Freight Lines.<br>"
		f"<b>Chamber 2</b> is curing {len(made['curing'])} tyres; <b>Chamber 1</b> is loading {len(made['loading'])}.<br>"
		f"<b>Deliver to Customer</b>: Cape Coastal Transport at Bellville. Their tyres end {tails(made['deliver'])}. "
		f"Type {tails(made['refuse'])} (Karoo Freight's) to show a wrong tyre refused.<br>"
		f"Presenter profiles: {profiles}." + (f"<br>Presenter login: {who}." if who else
		"<br>No presenter login given: create one, then load again with it to put it on the profiles.")
	)
