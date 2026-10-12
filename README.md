# Fuse Retread

Tyre retreading for Fuse: every tyre traced from the branch, through the factory and back to its
owner, on simple floor screens. Frappe / ERPNext v16. Requires `erpnext` and `fuse_core`.

## Rules this app keeps

- **Its own doctypes, all prefixed `FR`.** No Fuse Manufacturing doctype is touched. A customer's
  tyre is not the retreader's own stock, so nothing here moves ERPNext stock.
- **One identity per tyre, for life** (FR Casing): the manufacturer's serial, or a number the factory
  issues (`P` and digits by default). The DOT code is recorded but is never the identity.
- **One Job Card per visit** (FR Job Card). Not ERPNext's Job Card, which hangs off a Work Order,
  a BOM and a finished item.
- **The line is configuration.** FR Stage holds the client's own stages, in order, with which are
  recording points and which routes they sit on. `engine.py` reads it; nothing about the line is
  hard-coded. Stages cannot be skipped: every recording asks the engine first.
- **Nothing posts to Sage Intacct in this version.** The invoice is a preview.

## What is in it

| Area | Screens and doctypes |
|---|---|
| Floor (tablet or phone) | page **fuse-retread**: Receive at Branch, 1st Inspection, Repairs, Building, Chambers, Final Inspection, Dispatch, Deliver to Customer |
| Office | FR Job Card (invoice preview and approval), FR Casing (life history), page **fr-production**, page **fr-flows** |
| Set-up lists | FR Settings, FR Stage, FR Branch, FR Tyre Size (prices), FR Tyre Brand, FR Tread Pattern, FR Reason, FR Operator, FR Chamber |
| Records | FR Casing, FR Job Card (+ FR Job Event), FR Chamber Load, FR Dispatch |
| Roles | Retread Floor, Retread Office (created on install) |

Final Inspection outcomes follow the client's drawing: Pass, A Reject (to Dispatch), B Redo (back
to the start of the line), C Repair (back to Repairs). A No at 1st Inspection sends the tyre to
Final Inspection to be confirmed as a reject.

## Install

1. Push the repo, add it to the Fuse bench (Frappe Cloud → Apps → Add from GitHub), **Deploy**
   (not just Update: Update skips `bench build`, so the pages' CSS would be missing).
2. Install on the site. `before_install` creates the two roles; `after_install` seeds the stage
   list and the settings defaults and adds the module switch to Active Modules.
3. If `after_migrate` did not fire, run **`fuse_retread.install.after_install`** as System Manager.
4. Open **FR Settings** and set the company.

## Demo

Job Card list → menu → **Load Retread Demo** (System Manager, demo site only: site config
`fuse_demo_site`). Give it the presenter login, which must already exist. **Start again** rebuilds
the line around the current time. See `demo/retread.py` for what it makes. Back up the demo site
first (`S:\Products\Fuse\demo_profiles\PROFILES.md`).

## Checks

```
python -m unittest discover -s fuse_retread/tests -t .
python -m ruff check .
```
