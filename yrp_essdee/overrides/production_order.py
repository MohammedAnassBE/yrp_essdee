"""yrp_essdee customisations on yrp's `Production Order`.

Single-item rule: the rows in `production_order_details` may reference at most ONE
distinct `Item`. This mirrors how production_api's Lot is bound to a single Item.

Wired via `doc_events.Production Order` in hooks.py.
"""

import frappe


def validate(doc, method=None):
	enforce_single_item(doc)


def before_submit(doc, method=None):
	enforce_single_item(doc, require_item=True)


def enforce_single_item(doc, require_item=False):
	"""Server-side rule: only one DISTINCT Item across the items table.

	Multiple rows of the same Item are allowed at the data layer; the row cap
	is enforced in the UI only (yrp_essdee/public/js/production_order.js).
	"""
	items = sorted({r.item for r in (doc.get("production_order_details") or []) if r.item})
	if require_item and not items:
		frappe.throw("Production Order must contain one Item before submit.")
	if len(items) > 1:
		frappe.throw(
			f"Production Order may contain only one Item. Found {len(items)}: {items}."
		)
	return items[0] if items else None


@frappe.whitelist()
def get_production_order_item(production_order):
	"""Return the single Item linked to a Production Order, or None.

	Lot doctypes can call this to fetch the item from a linked Production Order
	(replicates production_api's Lot.production_order → item flow).
	"""
	if not production_order:
		return None
	rows = frappe.get_all(
		"Production Order Detail",
		filters={"parent": production_order, "parenttype": "Production Order"},
		fields=["item"],
	)
	items = {r.item for r in rows if r.item}
	if not items:
		return None
	if len(items) > 1:
		frappe.throw(
			f"Production Order {production_order} has {len(items)} distinct items; expected exactly one."
		)
	return next(iter(items))
