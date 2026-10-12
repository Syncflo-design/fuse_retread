"""Small things every part of the app reads: the settings, the stage list, the tyre number rules."""

import re

import frappe


def company():
	value = frappe.db.get_single_value("FR Settings", "company")
	if not value:
		frappe.throw("Set the company in FR Settings first.", title="Retread is not set up")
	return value


def own_prefix():
	return (frappe.db.get_single_value("FR Settings", "own_prefix") or "P").strip().upper()


def normalise(serial):
	"""A tyre number as it is stored: no spaces, upper case. Staff type it both ways."""
	return re.sub(r"\s+", "", serial or "").upper()


def is_own_number(serial, prefix=None):
	"""Whether `serial` has the shape of a number the factory issues: the prefix, then digits."""
	prefix = prefix or own_prefix()
	return bool(re.fullmatch(re.escape(prefix) + r"\d+", serial or ""))


def split(text):
	return [line.strip() for line in (text or "").splitlines() if line.strip()]


def stages():
	"""The site's stage list in order, as plain dicts the route engine reads."""
	return frappe.get_all(
		"FR Stage",
		fields=["stage", "sequence", "screen", "on_retread", "on_repair", "optional_on_retread", "suggested"],
		order_by="sequence asc",
	)


def stage_for_screen(screen, rows=None):
	"""The first stage drawn on a given screen — Chambers, Dispatch, Deliver, Receive, Office."""
	for row in rows or stages():
		if row.get("screen") == screen:
			return row["stage"]
	return None
