import json

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_lot_order_details(work_order):
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("read")
	lot = _get_work_order_lot(wo)
	ipd_name = _get_work_order_ipd(wo, lot)
	rows = _lot_order_rows_for_work_order(wo, lot)
	from yrp_essdee.yrp_essdee.doctype.lot.lot import fetch_order_item_details

	return {
		"work_order": wo.name,
		"lot": lot.name,
		"lot_name": lot.get("lot_name") or lot.name,
		"process_name": wo.process_name,
		"quantity_field": "quantity",
		"rows": rows,
		"order_item_details": fetch_order_item_details(lot.get("lot_order_details") or [], ipd_name),
	}


@frappe.whitelist()
def calculate_deliverables(work_order, rows):
	rows = frappe.parse_json(rows) if isinstance(rows, str) else rows
	wo = frappe.get_doc("Work Order", work_order)
	wo.check_permission("write")
	if wo.docstatus != 0:
		frappe.throw(_("Calculate can only update a draft Work Order."))

	lot = _get_work_order_lot(wo)
	variant_demands = _variant_demands_from_rows(wo, lot, rows)

	if not variant_demands:
		frappe.throw(_("Enter Qty greater than zero to calculate deliverables."))

	ipd_name = _get_work_order_ipd(wo, lot)
	if not wo.process_name:
		frappe.throw(_("Process Name is required to calculate deliverables."))

	from yrp.yrp.doctype.item_production_detail.item_production_detail import (
		calculate_major_deliverables,
	)

	calculated_rows = calculate_major_deliverables(
		ipd_name,
		variant_demands,
		process_names=[wo.process_name],
		include_outputs=1,
	)
	deliverables = _to_work_order_items(
		[row for row in calculated_rows if row.get("side") == "Input"],
		"deliverable",
	)
	receivables = _to_work_order_items(
		[row for row in calculated_rows if row.get("side") == "Output"],
		"receivable",
		wo,
	)
	if not deliverables:
		frappe.throw(_("No deliverables were calculated for {0}.").format(wo.process_name))
	if not receivables:
		frappe.throw(_("No receivables were calculated for {0}.").format(wo.process_name))

	wo.set("deliverables", deliverables)
	wo.set("receivables", receivables)
	wo.deliverable_details = ""
	wo.receivable_details = ""
	wo.save()

	from yrp.stock.save_stock_items import group_items_for_ui

	return {
		"work_order": wo.name,
		"lot": lot.name,
		"deliverables": len(deliverables),
		"receivables": len(receivables),
		"deliverable_details": group_items_for_ui(wo.get("deliverables") or [], "Work Order Deliverables"),
		"receivable_details": group_items_for_ui(wo.get("receivables") or [], "Work Order Receivables"),
	}


def _get_work_order_lot(wo):
	if not wo.meta.get_field("lot"):
		frappe.throw(_("Lot field is not available on Work Order."))
	lot_name = wo.get("lot")
	if not lot_name:
		frappe.throw(_("Select Lot before calculating Work Order deliverables."))
	if not frappe.db.exists("Lot", lot_name):
		frappe.throw(_("Lot {0} does not exist.").format(lot_name))
	lot = frappe.get_doc("Lot", lot_name)
	lot.check_permission("read")
	return lot


def _get_work_order_ipd(wo, lot):
	ipd_name = wo.production_detail or lot.production_detail
	if not ipd_name:
		frappe.throw(_("Production Detail is required to calculate deliverables."))
	return ipd_name


def _lot_order_rows_for_work_order(wo, lot):
	source_rows = lot.get("lot_order_details") or []
	if not source_rows:
		frappe.throw(_("Lot {0} does not have Lot Order Details.").format(lot.name))

	out = []
	for row in source_rows:
		if not row.item_variant:
			continue
		qty = flt(row.get("quantity"))
		out.append({
			"item_variant": row.item_variant,
			"item": frappe.get_cached_value("Item Variant", row.item_variant, "item"),
			"attributes": _variant_attributes(row.item_variant),
			"qty": qty,
			"original_qty": qty,
			"uom": _variant_uom(row.item_variant),
			"set_combination": _normal_json(row.get("set_combination")),
		})
	if not out:
		frappe.throw(_("Lot {0} does not have item quantities for {1}.").format(lot.name, wo.process_name))
	return out


def _variant_demands_from_rows(wo, lot, rows):
	if _is_lot_order_payload(rows):
		rows = _rows_from_lot_order_payload(wo, lot, rows)
		return _variant_demands_from_flat_rows(wo, lot, rows, allow_same_item_variants=True)
	return _variant_demands_from_flat_rows(wo, lot, rows)


def _is_lot_order_payload(rows):
	return (
		isinstance(rows, list)
		and len(rows) > 0
		and isinstance(rows[0], dict)
		and rows[0].get("items") is not None
	)


def _rows_from_lot_order_payload(wo, lot, payload):
	_validate_lot_order_payload(lot, payload)
	from yrp_essdee.yrp_essdee.doctype.lot.lot import save_order_item_details

	return save_order_item_details(
		_get_work_order_ipd(wo, lot),
		lot.get("lot_order_details") or [],
		payload,
	)


def _variant_demands_from_flat_rows(wo, lot, rows, allow_same_item_variants=False):
	allowed_rows = _lot_order_rows_for_work_order(wo, lot)
	allowed_by_variant = {row["item_variant"]: row for row in allowed_rows}
	allowed_items = _lot_item_names(lot)
	variant_demands = []
	for row in rows or []:
		item_variant = row.get("item_variant")
		if not item_variant:
			continue
		if allow_same_item_variants:
			item = frappe.get_cached_value("Item Variant", item_variant, "item")
			if item not in allowed_items:
				frappe.throw(_("Item Variant {0} is not part of Lot {1}.").format(item_variant, lot.name))
		elif item_variant not in allowed_by_variant:
			frappe.throw(_("Item Variant {0} is not part of Lot {1}.").format(item_variant, lot.name))
		qty = flt(row.get("qty") or row.get("quantity"))
		if qty < 0:
			frappe.throw(_("Qty cannot be negative for {0}.").format(item_variant))
		if qty > 0:
			variant_demands.append({"item_variant": item_variant, "qty": qty})
	return variant_demands


def _validate_lot_order_payload(lot, payload):
	allowed_items = _lot_item_names(lot)
	for group in payload or []:
		for item in group.get("items") or []:
			item_name = item.get("name")
			if item_name and item_name not in allowed_items:
				frappe.throw(_("Item {0} is not part of Lot {1}.").format(item_name, lot.name))


def _lot_item_names(lot):
	items = {
		frappe.get_cached_value("Item Variant", row.item_variant, "item")
		for row in lot.get("lot_order_details") or []
		if row.item_variant
	}
	if lot.get("item"):
		items.add(lot.item)
	return {item for item in items if item}


def _to_work_order_items(calculated_rows, row_type, wo=None):
	items = []
	for row in calculated_rows or []:
		qty = flt(row.get("required_qty") or row.get("qty"))
		if qty <= 0:
			continue
		item_variant = row.get("item_variant")
		out = {
			"item_variant": item_variant,
			"qty": qty,
			"pending_quantity": qty,
			"uom": row.get("uom") or _variant_uom(item_variant),
			"set_combination": {},
		}
		if row_type == "deliverable":
			out.update({
				"is_calculated": 1,
			})
		else:
			out.update({
				"process_cost": wo.process_cost if wo else None,
				"cost": 0,
				"total_cost": 0,
			})
		items.append(out)
	_assign_editor_indices(items)
	return items


def _assign_editor_indices(rows):
	table_indexes = {}
	row_indexes = {}
	for row in rows:
		item_variant = row.get("item_variant")
		if not item_variant:
			continue
		parent_item = frappe.get_cached_value("Item Variant", item_variant, "item")
		if not parent_item:
			continue
		attr_details = _item_attribute_details(parent_item)
		table_key = _table_group_key(attr_details)
		if table_key not in table_indexes:
			table_indexes[table_key] = len(table_indexes)

		attrs = _variant_attributes(item_variant)
		primary_attribute = attr_details.get("primary_attribute")
		if primary_attribute:
			logical_attrs = tuple(
				(attr, attrs.get(attr) or "")
				for attr in attr_details.get("attributes") or []
			)
			row_key = (table_key, parent_item, logical_attrs, row.get("uom") or "")
		else:
			row_key = (table_key, parent_item, tuple(sorted(attrs.items())), row.get("uom") or "")
		if row_key not in row_indexes:
			row_indexes[row_key] = len(row_indexes)

		row["table_index"] = table_indexes[table_key]
		row["row_index"] = row_indexes[row_key]


def _item_attribute_details(item):
	from yrp.yrp.doctype.item.item import get_attribute_details

	return get_attribute_details(item)


def _table_group_key(attr_details):
	return (
		tuple(sorted(attr_details.get("attributes") or [])),
		attr_details.get("primary_attribute") or "",
		tuple(sorted(attr_details.get("primary_attribute_values") or [])),
	)


def _variant_attributes(item_variant):
	rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": item_variant, "parenttype": "Item Variant"},
		fields=["attribute", "attribute_value"],
		order_by="idx asc",
	)
	return {row.attribute: row.attribute_value for row in rows}


def _variant_uom(item_variant):
	item = frappe.get_cached_value("Item Variant", item_variant, "item")
	return frappe.get_cached_value("Item", item, "default_unit_of_measure") if item else None


def _normal_json(value):
	if not value:
		return {}
	return json.loads(value) if isinstance(value, str) else value
