"""The office side: a tyre's life history, the invoice preview, and the production view."""

import frappe
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate, time_diff_in_hours

from fuse_retread import common, floor

# ──────────────────────────────────────────────────────────────────────────────
# Tyre history — the evidence behind a claim
# ──────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def casing_history(casing):
	"""Every visit a tyre has made, newest first, with who did what at each stage."""
	frappe.get_doc("FR Casing", casing).check_permission("read")
	jobs = frappe.get_all(
		"FR Job Card",
		filters={"casing": casing},
		fields=["name", "customer", "branch", "route", "tread_pattern", "status", "result", "received_on",
			"delivered_on", "redo_count", "repair_count", "stage"],
		order_by="received_on desc",
	)
	for job in jobs:
		job["customer_name"] = frappe.db.get_value("Customer", job.customer, "customer_name") or job.customer
		job["events"] = frappe.get_all(
			"FR Job Event",
			filters={"parent": job.name, "parenttype": "FR Job Card"},
			fields=["stage", "outcome", "reason", "operator", "at"],
			order_by="at asc, idx asc",
		)
		built = [e for e in job["events"] if e.stage == "Building"]
		job["built_by"] = built[-1].operator if built else None
		job["built_on"] = built[-1].at if built else None
	return jobs


# ──────────────────────────────────────────────────────────────────────────────
# Invoice preview
# ──────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def invoice_preview(job):
	"""What the Sage Intacct sales invoice for this tyre would carry. Nothing is posted."""
	doc = frappe.get_doc("FR Job Card", job)
	doc.check_permission("read")
	settings = frappe.get_cached_doc("FR Settings")
	prices = frappe.db.get_value("FR Tyre Size", doc.size, ["retread_price", "repair_price"], as_dict=True) or {}

	if doc.result in ("Rejected", "Not Retreadable"):
		item, description, price = (
			settings.invoice_item,
			f"Casing {doc.serial} ({doc.size}) inspected, {doc.result.lower()}: returned, no charge",
			0,
		)
	elif doc.route == "Repair Only":
		item, description, price = settings.repair_item, f"Repair, {doc.size}, tyre {doc.serial}", flt(prices.get("repair_price"))
	else:
		pattern = f", {doc.tread_pattern}" if doc.tread_pattern else ""
		item, description, price = (
			settings.invoice_item,
			f"Retread {doc.size}{pattern}, tyre {doc.serial}",
			flt(prices.get("retread_price")),
		)
	vat = round(price * flt(settings.vat_percent) / 100, 2)
	return {
		"job": doc.name,
		"customer": doc.customer,
		"customer_name": frappe.db.get_value("Customer", doc.customer, "customer_name") or doc.customer,
		"branch": doc.branch,
		"date": nowdate(),
		"lines": [{"item": item, "description": description, "qty": 1, "price": price}],
		"net": price,
		"vat_percent": flt(settings.vat_percent),
		"vat": vat,
		"total": price + vat,
		"ready": "Invoice" in common.split(doc.next_stages) or doc.status in ("Invoiced", "Delivered"),
		"invoiced": doc.status in ("Invoiced", "Delivered"),
	}


@frappe.whitelist()
def approve_invoice(job, operator=None):
	"""Mark the invoice as raised. In this version the preview is the invoice: nothing posts."""
	doc = frappe.get_doc("FR Job Card", job)
	doc.check_permission("write")
	preview = invoice_preview(job)
	stage = common.stage_for_screen("Office")
	floor.record_stage(doc, stage, "Invoiced", operator=operator or None, save=False,
		note="Preview approved. Not posted to Sage Intacct in this version.")
	doc.price = preview["net"]
	doc.save()
	return invoice_preview(job)


# ──────────────────────────────────────────────────────────────────────────────
# The production view
# ──────────────────────────────────────────────────────────────────────────────


def _events(since, outcomes=None, stage=None):
	"""Stage events since a moment, for this site's retread company only."""
	conditions = ["e.at >= %(since)s", "j.company = %(company)s"]
	values = {"since": since, "company": common.company()}
	if outcomes:
		conditions.append("e.outcome in %(outcomes)s")
		values["outcomes"] = tuple(outcomes)
	if stage:
		conditions.append("e.stage = %(stage)s")
		values["stage"] = stage
	return frappe.db.sql(
		f"""
		select e.stage, e.outcome, e.reason, e.operator, e.at, j.name as job, j.serial
		from `tabFR Job Event` e
		join `tabFR Job Card` j on j.name = e.parent and e.parenttype = 'FR Job Card'
		where {' and '.join(conditions)}
		order by e.at asc
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def production():
	frappe.has_permission("FR Job Card", "read", throw=True)
	rows = common.stages()
	final = next((r["stage"] for r in reversed(rows) if r["screen"] == "Inspection"), None)
	receive = common.stage_for_screen("Receive", rows)
	dispatch = common.stage_for_screen("Dispatch", rows)
	today = getdate(nowdate())
	week_ago = add_days(today, -6)
	now = now_datetime()

	# Where every tyre still in is waiting. A tyre offered "Repairs or Building" is counted at
	# the point it cannot pass by — Building — since most need no repair.
	active = floor._active(fields=["name", "serial", "customer", "next_stages", "in_chamber", "last_event_at", "stage",
		"status", "redo_count"])
	queue = {r["stage"]: 0 for r in rows if r["screen"] not in ("None",)}
	in_chambers = 0
	for job in active:
		upcoming = common.split(job.next_stages)
		if cint(job.in_chamber):
			in_chambers += 1
			continue
		if upcoming:
			queue[upcoming[-1]] = queue.get(upcoming[-1], 0) + 1

	week = _events(week_ago)
	passes = [e for e in week if e.stage == final and e.outcome == "Pass"]
	by_day = []
	for offset in range(6, -1, -1):
		day = add_days(today, -offset)
		by_day.append({"date": str(day), "output": sum(1 for e in passes if getdate(e.at) == day)})

	def problems(items):
		counts = {}
		for e in items:
			key = (e.outcome, e.reason or "No reason")
			counts[key] = counts.get(key, 0) + 1
		return [
			{"outcome": outcome, "reason": reason, "count": count}
			for (outcome, reason), count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
		]

	failures = [e for e in week if e.outcome in ("Reject", "Redo", "Repair", "No")]
	today_failures = [e for e in failures if getdate(e.at) == today]

	waiting_longest = []
	for job in sorted(
		(j for j in active if not cint(j.in_chamber) and j.status == "In Progress" and j.last_event_at),
		key=lambda j: j.last_event_at,
	)[:8]:
		waiting_longest.append({
			"job": job.name, "serial": job.serial,
			"customer": frappe.db.get_value("Customer", job.customer, "customer_name") or job.customer,
			"waiting_for": " or ".join(common.split(job.next_stages)), "last_stage": job.stage,
			"hours": round(time_diff_in_hours(now, job.last_event_at), 1),
		})

	return {
		"target": cint(frappe.db.get_single_value("FR Settings", "daily_target")),
		"output_today": by_day[-1]["output"],
		"by_day": by_day,
		"in_progress": len(active),
		"in_chambers": in_chambers,
		"received_today": sum(1 for e in week if e.stage == receive and getdate(e.at) == today),
		"dispatched_today": sum(1 for e in week if e.stage == dispatch and getdate(e.at) == today),
		"queue": [
			{"stage": r["stage"], "count": queue.get(r["stage"], 0), "suggested": cint(r["suggested"]),
				"screen": r["screen"]}
			for r in rows
			if r["screen"] not in ("None", "Receive")
		],
		"problems_today": problems(today_failures),
		"problems_week": problems(failures),
		"redos_today": sum(1 for e in today_failures if e.outcome == "Redo"),
		"rejects_today": sum(1 for e in today_failures if e.outcome in ("Reject", "No")),
		"waiting_longest": waiting_longest,
		"as_at": str(now),
	}
