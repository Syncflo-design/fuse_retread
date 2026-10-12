"""The route rules, walked through the customer-retread drawing.

    python -m unittest discover -s fuse_retread/tests -t .
"""

import unittest

from fuse_retread import engine
from fuse_retread.engine import RouteError

STAGES = engine.default_stage_rows()


def received():
	"""A tyre just booked in at the branch."""
	state = {"route": "Retread", "position": 0, "next": ["Receive at Branch"], "result": "",
		"status": "In Progress", "redo_count": 0, "repair_count": 0, "in_chamber": 0}
	return engine.apply(STAGES, state, "Receive at Branch", "Received")


def run(state, *steps):
	for step in steps:
		stage, outcome = step[0], step[1]
		route = step[2] if len(step) > 2 else None
		state = engine.apply(STAGES, state, stage, outcome, route=route)
	return state


def built_and_cured():
	return run(
		received(), ("1st Inspection", "Yes", "Retread"), ("Building", "Done"),
		("Chambers", "Into Chamber"), ("Chambers", "Cured"),
	)


class TestRoute(unittest.TestCase):
	def test_received_waits_for_first_inspection(self):
		self.assertEqual(received()["next"], ["1st Inspection"])

	def test_retread_offers_repairs_or_building(self):
		state = run(received(), ("1st Inspection", "Yes", "Retread"))
		self.assertEqual(state["next"], ["Repairs", "Building"])

	def test_repair_only_route_goes_repairs_then_chambers(self):
		state = run(received(), ("1st Inspection", "Yes", "Repair Only"))
		self.assertEqual(state["next"], ["Repairs"])
		state = run(state, ("Repairs", "Done"))
		self.assertEqual(state["next"], ["Chambers"])

	def test_happy_path_to_the_customer(self):
		state = run(built_and_cured(), ("Final Inspection", "Pass"))
		self.assertEqual(state["result"], "Passed")
		self.assertEqual(state["next"], ["Dispatch"])
		state = run(state, ("Dispatch", "Dispatched"))
		self.assertEqual((state["status"], state["next"]), ("Dispatched", ["Invoice"]))
		state = run(state, ("Invoice", "Invoiced"))
		self.assertEqual((state["status"], state["next"]), ("Invoiced", ["Deliver to Customer"]))
		state = run(state, ("Deliver to Customer", "Delivered"))
		self.assertEqual((state["status"], state["next"]), ("Delivered", []))

	def test_stages_cannot_be_skipped(self):
		state = run(received(), ("1st Inspection", "Yes", "Retread"))
		with self.assertRaises(RouteError) as caught:
			run(state, ("Final Inspection", "Pass"))
		self.assertIn("Repairs or Building", str(caught.exception))

	def test_in_a_chamber_nothing_else_records(self):
		state = run(received(), ("1st Inspection", "Yes"), ("Building", "Done"), ("Chambers", "Into Chamber"))
		with self.assertRaises(RouteError):
			run(state, ("Final Inspection", "Pass"))
		with self.assertRaises(RouteError):
			run(state, ("Chambers", "Into Chamber"))

	def test_cure_needs_a_chamber_first(self):
		state = run(received(), ("1st Inspection", "Yes"), ("Building", "Done"))
		with self.assertRaises(RouteError):
			run(state, ("Chambers", "Cured"))

	def test_redo_goes_back_to_the_start_of_the_line(self):
		state = run(built_and_cured(), ("Final Inspection", "Redo"))
		self.assertEqual(state["redo_count"], 1)
		self.assertEqual(state["next"], ["Repairs", "Building"])
		self.assertEqual(state["result"], "")

	def test_repair_goes_back_to_repairs_only(self):
		state = run(built_and_cured(), ("Final Inspection", "Repair"))
		self.assertEqual((state["repair_count"], state["next"]), (1, ["Repairs"]))
		state = run(state, ("Repairs", "Done"))
		self.assertEqual(state["next"], ["Building"])

	def test_reject_still_goes_back_to_the_customer(self):
		state = run(built_and_cured(), ("Final Inspection", "Reject"))
		self.assertEqual((state["result"], state["next"]), ("Rejected", ["Dispatch"]))

	def test_not_retreadable_skips_the_line(self):
		state = run(received(), ("1st Inspection", "No"))
		self.assertEqual((state["result"], state["next"]), ("Not Retreadable", ["Final Inspection"]))
		self.assertEqual(engine.outcomes(STAGES, "Final Inspection", state), ["Reject"])
		with self.assertRaises(RouteError):
			run(state, ("Final Inspection", "Pass"))
		state = run(state, ("Final Inspection", "Reject"))
		self.assertEqual(state["next"], ["Dispatch"])

	def test_first_inspection_vocabulary(self):
		self.assertEqual(engine.outcomes(STAGES, "1st Inspection", {}), ["Yes", "No"])
		self.assertEqual(engine.outcomes(STAGES, "Final Inspection", {}), ["Pass", "Reject", "Redo", "Repair"])

	def test_unknown_route_refused(self):
		with self.assertRaises(RouteError):
			run(received(), ("1st Inspection", "Yes", "Sideways"))

	def test_input_state_untouched(self):
		state = received()
		before = dict(state, next=list(state["next"]))
		run(state, ("1st Inspection", "Yes"))
		self.assertEqual(state, before)


if __name__ == "__main__":
	unittest.main()
