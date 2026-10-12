"""What this app contributes to Fuse: its switch and its tiles.

Kept apart from install.py: these are read on every Fuse Home load, by other apps, and that call
has no business importing set-up code.

The key is permanent. Renaming it orphans a client's saved setting and silently switches the
module back on.
"""

MODULE_KEY = "fr_retread"

MODULES = [
	{
		"key": MODULE_KEY,
		"label": "Retread: Tyre Production",
		"description": "Floor screens, Job Cards, chambers, dispatch, delivery and the production view. "
		"Off hides the retread tiles.",
	},
]

FLOOR = ["Retread Floor", "Retread Office", "System Manager"]
OFFICE = ["Retread Office", "System Manager"]

# Lucide icons, inner SVG only — fuse_theme wraps them. The emoji is what Fuse Home draws where
# it does not draw stroked icons, which is why both are given.
TABLET = '<rect width="16" height="20" x="4" y="2" rx="2" ry="2"></rect><line x1="12" x2="12.01" y1="18" y2="18"></line>'
GAUGE = '<path d="m12 14 4-4"></path><path d="M3.34 19a10 10 0 1 1 17.32 0"></path>'
CLIPBOARD = (
	'<rect width="8" height="4" x="8" y="2" rx="1" ry="1"></rect>'
	'<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>'
	'<path d="M12 11h4"></path><path d="M12 16h4"></path><path d="M8 11h.01"></path><path d="M8 16h.01"></path>'
)
HISTORY = (
	'<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path>'
	'<path d="M12 7v5l4 2"></path>'
)
RECEIPT = (
	'<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"></path>'
	'<path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"></path><path d="M12 17.5v-11"></path>'
)
ROUTE = (
	'<circle cx="6" cy="19" r="3"></circle><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"></path>'
	'<circle cx="18" cy="5" r="3"></circle>'
)


def get_modules():
	return [dict(module) for module in MODULES]


def get_tiles():
	return [
		{
			"key": "fr_floor",
			"module": MODULE_KEY,
			"label": "Retread Floor",
			"blurb": "Record each tyre at each stage, on a tablet or phone",
			"icon": "📱",
			"svg": TABLET,
			"route": ["fuse-retread"],
			"requires_page": "fuse-retread",
			"roles": FLOOR,
		},
		{
			"key": "fr_production",
			"module": MODULE_KEY,
			"label": "Production",
			"blurb": "Tyres at each stage, today's output, rejects and redos",
			"icon": "📊",
			"svg": GAUGE,
			"route": ["fr-production"],
			"requires_page": "fr-production",
			"roles": OFFICE,
		},
		{
			"key": "fr_job_cards",
			"module": MODULE_KEY,
			"label": "Job Cards",
			"blurb": "Every tyre on the line, stage by stage",
			"icon": "📋",
			"svg": CLIPBOARD,
			"route": ["List", "FR Job Card"],
			# Everything still in, until the filter is cleared.
			"options": {"status": ["!=", "Delivered"]},
			"roles": FLOOR,
		},
		{
			"key": "fr_invoice",
			"module": MODULE_KEY,
			"label": "Invoice",
			"blurb": "Finished tyres back at the branch, ready to invoice",
			"icon": "🧾",
			"svg": RECEIPT,
			"route": ["List", "FR Job Card"],
			"options": {"status": "Dispatched"},
			"roles": OFFICE,
		},
		{
			"key": "fr_tyres",
			"module": MODULE_KEY,
			"label": "Tyre History",
			"blurb": "A tyre's whole life, the evidence for claims",
			"icon": "🕘",
			"svg": HISTORY,
			"route": ["List", "FR Casing"],
			"group": "reference",
			"roles": FLOOR,
		},
		{
			"key": "fr_flows",
			"module": MODULE_KEY,
			"label": "The Four Flows",
			"blurb": "Retreads, claims, own stock and casing credits on one line",
			"icon": "🔀",
			"svg": ROUTE,
			"route": ["fr-flows"],
			"requires_page": "fr-flows",
			"group": "reference",
			"roles": FLOOR,
		},
	]
