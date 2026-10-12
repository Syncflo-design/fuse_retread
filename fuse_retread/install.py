"""Put a site's retread configuration in step with this version of the app.

Idempotent: it runs on install, on every migrate, and by hand (`fuse_retread.install.after_install`,
System Manager) when a Frappe Cloud deploy skips after_migrate.
"""

import frappe

from fuse_retread import engine, registry

ROLES = {
	"Retread Floor": "Records tyres at each stage on the floor screens.",
	"Retread Office": "Runs the office side: invoicing, the production view and the set-up lists.",
}

# Blank settings get these once, so the form shows what the code already assumes. A value the
# client has set is never overwritten.
SETTINGS_DEFAULTS = {
	"own_prefix": "P",
	"next_own_number": 10001,
	"daily_target": 40,
	"vat_percent": 15,
	"invoice_item": "RETREAD",
	"repair_item": "REPAIR",
}


def before_install():
	_roles()


@frappe.whitelist()
def after_install():
	# Only over HTTP. The same function is the after_install and after_migrate hook, where there
	# is no session to check and a refusal would take the whole migrate down.
	if frappe.request:
		frappe.only_for("System Manager")

	roles = _roles()
	stages = _seed_stages()
	settings = _settings_defaults()
	switches = _sync_switches()
	frappe.db.commit()
	return {"roles": roles, "stages_seeded": stages, "settings_defaults": settings, "switches": switches}


def _roles():
	made = []
	for role, description in ROLES.items():
		if frappe.db.exists("Role", role):
			continue
		frappe.get_doc(
			{"doctype": "Role", "role_name": role, "desk_access": 1, "description": description}
		).insert(ignore_permissions=True)
		made.append(role)
	return made


def _seed_stages():
	"""The line as the client drew it, once. After that the site's own list rules."""
	if not frappe.db.exists("DocType", "FR Stage") or frappe.db.count("FR Stage"):
		return 0
	for row in engine.default_stage_rows():
		doc = frappe.new_doc("FR Stage")
		doc.update(row)
		doc.insert(ignore_permissions=True)
	return len(engine.DEFAULT_STAGES)


def _settings_defaults():
	"""Fill blanks only. Written field by field: the single requires a company, which a fresh
	site does not have yet, so it cannot be saved as a document here."""
	if not frappe.db.exists("DocType", "FR Settings"):
		return []
	filled = []
	for field, value in SETTINGS_DEFAULTS.items():
		if not frappe.db.get_single_value("FR Settings", field):
			frappe.db.set_single_value("FR Settings", field, value)
			filled.append(field)
	return filled


def _sync_switches():
	"""Get this app's switch into Active Modules now, not at the next migrate."""
	try:
		from fuse_core import modules

		modules.sync_modules()
	except Exception:
		frappe.log_error(title="Fuse Retread: could not seed the module switch", message=frappe.get_traceback())
		return None
	return [module["key"] for module in registry.get_modules()]
