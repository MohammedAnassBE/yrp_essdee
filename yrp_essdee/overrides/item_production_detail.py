"""yrp_essdee customisations on yrp's `Item Production Detail`.

- Sync `primary_item_attribute` alias to mirror `primary_attribute` (production_api compat).
- On `onload`, populate `__onload.attr_list` and `__onload.dependent_attribute` so the
  Vue components (`ItemAttributeList`, `ItemDependentAttributeDetail`) can render
  attribute values exactly like they do on the Item form.
"""

import frappe

from yrp_essdee.yrp_essdee.api.ipd import (
	fetch_combination_items,
	save_item_details,
	update_if_string_instance,
)


def before_validate(doc, method=None):
	_sync_combination_payloads(doc)
	_sync_cloth_payloads(doc)
	_sync_marker_groups(doc)
	_clear_set_item_payloads_when_disabled(doc)
	_validate_set_item_defaults(doc)


def validate(doc, method=None):
	# `primary_item_attribute` is now native (matches production_api). No alias sync needed.
	_sync_bom_attribute_mappings(doc)
	if not doc.is_new() and len(doc.get("packing_attribute_details") or []) > 0:
		_packing_tab_validations(doc)
	if doc.get("stiching_process") and len(doc.get("stiching_item_details") or []) > 0:
		_stiching_tab_validations(doc)
	if doc.get("cutting_process") and (
		len(doc.get("cutting_attributes") or []) > 0
		or len(doc.get("cloth_attributes") or []) > 0
		or len(doc.get("accessory_attributes") or []) > 0
		or len(doc.get("stiching_item_combination_details") or []) > 0
	):
		_cutting_tab_validations(doc)
	if len(doc.get("accessory_attributes") or []) > 0 and update_if_string_instance(doc.get("cloth_accessory_json")):
		if not update_if_string_instance(doc.get("stiching_accessory_json")):
			frappe.throw("Enter the Details for Stitching Accessory Combination")


def _sync_combination_payloads(doc):
	items = []
	for row in doc.item_bom or []:
		if not row.based_on_attribute_mapping:
			if row.item in items:
				frappe.throw("Duplicate Item in BOM " + row.item + " in Row " + str(row.idx))
			items.append(row.item)

	if doc.get("set_item_detail") and doc.is_set_item:
		doc.set("set_item_combination_details", save_item_details(doc.set_item_detail))

	if doc.get("stiching_item_detail"):
		doc.set("stiching_item_combination_details", save_item_details(doc.stiching_item_detail, ipd_doc=doc))


def _sync_cloth_payloads(doc):
	if len(doc.get("cloth_detail") or []) > 0:
		names = set()
		for cloth in doc.cloth_detail:
			names.add(cloth.name1)
		if len(names) != len(doc.cloth_detail):
			frappe.throw("Duplicates are occured in the cloth detail")

	cloths = [cloth.name1 for cloth in (doc.cloth_detail or [])]
	cut_json = update_if_string_instance(doc.get("cutting_cloths_json"))
	if cut_json:
		cut_json["select_list"] = cloths
	doc.cutting_cloths_json = cut_json


def _sync_marker_groups(doc):
	if not doc.get("marker_details"):
		return
	items = []
	for item in doc.marker_details:
		item["selected"].sort()
		selected = ",".join(item["selected"])
		if selected:
			items.append({"group_panels": selected})
	doc.set("cutting_marker_groups", items)


def _clear_set_item_payloads_when_disabled(doc):
	if doc.is_set_item:
		return
	doc.set("set_item_combination_details", [])
	doc.major_attribute_value = None
	doc.set_item_attribute = None


def _validate_set_item_defaults(doc):
	if not doc.is_set_item or doc.is_new() or not frappe.db.exists("Item Production Detail", doc.name):
		return

	previous = frappe.get_doc("Item Production Detail", doc.name)
	if not (previous.is_set_item and doc.is_set_item):
		return

	mapping = None
	for row in doc.item_attributes or []:
		if row.attribute == doc.set_item_attribute:
			mapping = row.mapping
			break
	if not mapping:
		return

	map_doc = frappe.get_doc("Item Item Attribute Mapping", mapping)
	map_values = [row.attribute_value for row in (map_doc.values or [])]
	check_dict = {}

	for row in doc.stiching_item_details or []:
		if row.is_default:
			if check_dict.get(row.set_item_attribute_value):
				frappe.throw(f"Select only one Is Default for {row.set_item_attribute_value}")
			check_dict[row.set_item_attribute_value] = 1

	if len(check_dict) < len(map_values):
		frappe.throw("Select Is default for all Set Item Attributes")


def _packing_tab_validations(doc):
	if doc.packing_combo == 0:
		frappe.throw("The packing combo should not be zero")

	if doc.packing_attribute_no == 0:
		frappe.throw("The packing attribute no should not be zero")

	mapping = None
	for row in doc.item_attributes or []:
		if row.attribute == doc.packing_attribute:
			mapping = row.mapping
			break

	map_doc = frappe.get_doc("Item Item Attribute Mapping", mapping)
	if len(map_doc.values) < doc.packing_attribute_no:
		frappe.throw(f"The Packing attribute no is {doc.packing_attribute_no} But there is only {len(map_doc.values)} attributes are available")

	if len(doc.packing_attribute_details or []) != doc.packing_attribute_no:
		frappe.throw(f"Only {doc.packing_attribute_no} {doc.packing_attribute}'s are required")

	attr = set()
	if doc.auto_calculate:
		for row in doc.packing_attribute_details or []:
			attr.add(row.attribute_value)
			row.quantity = 0
	else:
		total = 0.0
		for row in doc.packing_attribute_details or []:
			if not row.quantity:
				frappe.throw("Enter value in Packing Attribute Details, Zero is not considered as a valid quantity")
			total += row.quantity
			attr.add(row.attribute_value)
		if total < doc.packing_combo or total > doc.packing_combo:
			frappe.throw(f"In Packing Attribute Details, the sum of quantity should be {doc.packing_combo}")

	if len(attr) != len(doc.packing_attribute_details or []):
		frappe.throw("Duplicate Attribute values are occured in Packing Attribute Details")


def _stiching_tab_validations(doc):
	if len(doc.stiching_item_details or []) == 0:
		frappe.throw("Enter stiching attribute details")

	attr = set()
	total = 0.0
	for row in doc.stiching_item_details or []:
		if not row.quantity:
			frappe.throw("Enter value in Stiching Item Details, Zero is not considered as a valid quantity")
		total += row.quantity
		attr.add(row.stiching_attribute_value)

	if len(attr) != len(doc.stiching_item_details or []):
		frappe.throw("Duplicate Attribute values are occured in Stiching Item Details")


def _cutting_tab_validations(doc):
	ipd_cloth_attributes = [row.attribute for row in (doc.cloth_attributes or [])]
	ipd_cutting_attributes = [row.attribute for row in (doc.cutting_attributes or [])]
	accessory_attributes = [row.attribute for row in (doc.accessory_attributes or [])]

	if not doc.is_same_packing_attribute and doc.stiching_attribute not in ipd_cutting_attributes and len(ipd_cutting_attributes) > 0:
		frappe.throw(f"{doc.stiching_attribute} Should be in Cutting Combination")

	if doc.stiching_attribute in ipd_cloth_attributes and doc.stiching_attribute not in ipd_cutting_attributes:
		frappe.throw(f"Please mention the {doc.stiching_attribute} in Cutting Combination")

	pre_set_item = frappe.get_value("Item Production Detail", doc.name, "is_set_item")
	if pre_set_item:
		if doc.is_set_item and doc.set_item_attribute not in accessory_attributes and len(accessory_attributes) > 0:
			frappe.throw(f"{doc.set_item_attribute} should be in the Accessory Combination")
		if doc.is_set_item and doc.set_item_attribute not in ipd_cutting_attributes and len(ipd_cutting_attributes) > 0:
			frappe.throw(f"{doc.set_item_attribute} Should be in the Cutting Combination")

	if doc.is_same_packing_attribute:
		for row in doc.stiching_item_combination_details or []:
			row.attribute_value = row.major_attribute_value


def on_update(doc, method=None):
	"""Mirror production_api's on_update: delete `Item BOM Attribute Mapping`
	docs queued during the validate sync (rows that flipped
	based_on_attribute_mapping from on→off)."""
	queued = getattr(frappe.flags, "yrp_essdee_delete_bom_mapping", None)
	if not queued:
		return
	for name in queued:
		if frappe.db.exists("Item BOM Attribute Mapping", name):
			try:
				frappe.delete_doc("Item BOM Attribute Mapping", name, force=1, ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"yrp_essdee on_update delete BOM mapping {name}: {e}")
	frappe.flags.yrp_essdee_delete_bom_mapping = []


def _sync_bom_attribute_mappings(doc):
	"""For each Item BOM row:
	  - If `based_on_attribute_mapping=1` and no `attribute_mapping` → create
	    a new `Item BOM Attribute Mapping` and link it.
	  - If `based_on_attribute_mapping=0` and has `attribute_mapping` →
	    queue the mapping for deletion in `on_update` and clear the link.
	Mirrors production_api's `update_mapping_values`.
	"""
	frappe.flags.yrp_essdee_delete_bom_mapping = []
	if not (doc.item_bom or []):
		return
	# packing_attribute is a yrp_essdee custom field; fall back to primary_item_attribute
	# if the IPD doesn't declare a packing attribute yet.
	header_attr = (
		doc.get("packing_attribute")
		or doc.get("primary_item_attribute")
		or (doc.item_attributes[0].attribute if doc.item_attributes else None)
	)
	parent_item = doc.item

	for bom in doc.item_bom:
		if bom.based_on_attribute_mapping and not bom.attribute_mapping:
			if not bom.item:
				continue
			mapping = frappe.new_doc("Item BOM Attribute Mapping")
			mapping.item = parent_item
			mapping.bom_item = bom.item
			# Header (item-side) attributes — single row carrying the IPD's
			# governing attribute (Colour for garments, primary fallback otherwise)
			if header_attr:
				mapping.append("item_attributes", {"attribute": header_attr})
			# BOM-side attributes — every attribute the BOM item has
			bom_item_doc = frappe.get_cached_doc("Item", bom.item)
			for attr_row in bom_item_doc.get("attributes") or []:
				mapping.append("bom_item_attributes", {"attribute": attr_row.attribute})
			mapping.flags.ignore_validate = True
			mapping.insert(ignore_permissions=True)
			bom.attribute_mapping = mapping.name
		elif (not bom.based_on_attribute_mapping) and bom.attribute_mapping:
			frappe.flags.yrp_essdee_delete_bom_mapping.append(bom.attribute_mapping)
			bom.attribute_mapping = None


def onload(doc, method=None):
	"""Mirror Item.onload: load attribute values keyed by attribute, plus the
	dependent-attribute details (stage → depending attrs), plus the BOM
	attribute-mapping summary."""
	if not doc.item:
		return
	_load_attribute_list(doc)
	_load_dependent_attribute(doc)
	_load_bom_attribute_list(doc)
	_load_combination_details(doc)


def _load_combination_details(doc):
	set_items = fetch_combination_items(doc.get("set_item_combination_details"))
	if len(set_items["values"]) > 0:
		doc.set_onload("set_item_detail", set_items)

	stich_items = fetch_combination_items(doc.get("stiching_item_combination_details"))
	if len(stich_items["values"]) > 0:
		doc.set_onload("stiching_item_detail", stich_items)


def _load_bom_attribute_list(doc):
	"""Mirror production_api's `load_bom_attribute_list`. For each BOM row that
	references an `Item BOM Attribute Mapping`, emit:
	  {bom_item, bom_attr_mapping_link, bom_attr_mapping_based_on,
	   bom_attr_mapping_list (the mapping's values child rows), doctype}
	The Vue (`BomAttributeMapping.vue`) reads __onload.bom_attr_list directly."""
	out = []
	for bom in doc.item_bom or []:
		mapping = getattr(bom, "attribute_mapping", None)
		if not mapping or not frappe.db.exists("Item BOM Attribute Mapping", mapping):
			continue
		mapping_doc = frappe.get_cached_doc("Item BOM Attribute Mapping", mapping)
		out.append({
			"bom_item": bom.item,
			"bom_attr_mapping_link": mapping,
			"bom_attr_mapping_based_on": getattr(bom, "based_on_attribute_mapping", 0),
			"bom_attr_mapping_list": [v.as_dict() for v in (mapping_doc.values or [])],
			"doctype": "Item BOM Attribute Mapping",
		})
	doc.set_onload("bom_attr_list", out)


def _load_attribute_list(doc):
	"""Walk the parent Item's `attributes` child table; for each attribute, pull
	its mapped values from `Item Item Attribute Mapping`. Only include attributes
	that the IPD's `item_attributes` selects."""
	ipd_attrs = {r.attribute for r in (doc.item_attributes or [])}
	if not ipd_attrs:
		doc.set_onload("attr_list", [])
		return

	item_doc = frappe.get_doc("Item", doc.item)
	out = []
	for attr_row in item_doc.get("attributes") or []:
		if attr_row.attribute not in ipd_attrs:
			continue
		attribute_doc = frappe.get_doc("Item Attribute", attr_row.attribute)
		if getattr(attribute_doc, "numeric_values", 0):
			continue
		mapped_values = []
		if attr_row.mapping and frappe.db.exists("Item Item Attribute Mapping", attr_row.mapping):
			mapping_doc = frappe.get_doc("Item Item Attribute Mapping", attr_row.mapping)
			mapped_values = [
				{
					"name": v.name,
					"attribute_value": v.attribute_value,
				}
				for v in mapping_doc.values
			]
		out.append({
			"name": attr_row.name,
			"attr_name": attr_row.attribute,
			"attr_values_link": attr_row.mapping,
			"attr_values": mapped_values,
			"doctype": "Item Item Attribute Mapping",
		})
	doc.set_onload("attr_list", out)


def _load_dependent_attribute(doc):
	"""Load dependent attribute details (stage → list of attrs valid at that stage)."""
	if not (doc.dependent_attribute and doc.dependent_attribute_mapping):
		doc.set_onload("dependent_attribute", {})
		return
	try:
		# Reuse yrp's existing helper if available
		from yrp.yrp.doctype.item_dependent_attribute_mapping.item_dependent_attribute_mapping import (
			get_dependent_attribute_details,
		)
		details = get_dependent_attribute_details(doc.dependent_attribute_mapping)
	except Exception:
		details = _fallback_dep_attr_details(doc.dependent_attribute_mapping)
	doc.set_onload("dependent_attribute", details)


def _fallback_dep_attr_details(idam_name):
	"""Build the same shape `get_dependent_attribute_details` returns, in case
	yrp's helper isn't importable."""
	idam = frappe.get_doc("Item Dependent Attribute Mapping", idam_name)
	attr_list = {}
	for r in idam.details or []:
		attr_list[r.attribute_value] = {
			"uom": r.uom,
			"display_name": getattr(r, "display_name", None),
			"is_final": getattr(r, "is_final", 0),
			"depending_attributes": [],
		}
	for r in idam.mapping or []:
		stage = r.dependent_attribute_value
		if stage in attr_list:
			attr_list[stage]["depending_attributes"].append(r.depending_attribute)
	return {
		"dependent_attribute": idam.dependent_attribute,
		"attr_list": attr_list,
	}
