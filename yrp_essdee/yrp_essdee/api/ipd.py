"""yrp_essdee IPD API endpoints — port of production_api's
`production_api.essdee_production.doctype.item_production_detail.item_production_detail`
methods. Adapted to read from yrp's IPD doctype + child tables.
"""

import json
from itertools import groupby

import frappe
from frappe.utils import cint


def update_if_string_instance(obj):
	if isinstance(obj, str):
		obj = json.loads(obj)
	if not obj:
		obj = {}
	return obj


def _row_value(row, fieldname, default=None):
	if isinstance(row, dict):
		return row.get(fieldname, default)
	return getattr(row, fieldname, default)


def _is_truthy(value):
	if isinstance(value, str):
		return value.lower() in ("1", "true", "yes", "on")
	return bool(cint(value))


def get_stich_details(ipd_doc):
	stich_details = {}
	for row in ipd_doc.stiching_item_details or []:
		stich_details[row.stiching_attribute_value] = row.set_item_attribute_value
	return stich_details


def get_dict_table(table_data):
	return [row.as_dict() for row in (table_data or [])]


@frappe.whitelist()
def fetch_combination_items(combination_items):
	combination_items = [row.as_dict() for row in (combination_items or [])]
	combination_result = {"attributes": [], "values": []}
	for _key, items in groupby(combination_items, lambda i: i["index"]):
		items = list(items)
		item_list = {
			"major_attribute": items[0]["major_attribute_value"],
			"val": {},
		}
		for item in items:
			if item["set_item_attribute_value"] not in combination_result["attributes"]:
				combination_result["attributes"].append(item["set_item_attribute_value"])
			item_list["val"][item["set_item_attribute_value"]] = item["attribute_value"]
		combination_result["values"].append(item_list)
	return combination_result


def save_item_details(combination_item_detail, ipd_doc=None):
	combination_item_detail = update_if_string_instance(combination_item_detail)
	item_detail = []
	set_item_stitching_attrs = {}
	set_item_packing_combination = {}
	if ipd_doc and ipd_doc.is_set_item:
		set_item_stitching_attrs = get_stich_details(ipd_doc)
		for row in ipd_doc.set_item_combination_details or []:
			set_item_packing_combination.setdefault(row.major_attribute_value, {})
			set_item_packing_combination[row.major_attribute_value][row.set_item_attribute_value] = row.attribute_value

	for idx, item in enumerate(combination_item_detail.get("values") or []):
		for value in item.get("val") or {}:
			row = {
				"index": idx,
				"major_attribute_value": item["major_attribute"],
				"set_item_attribute_value": value,
				"attribute_value": item["val"][value],
			}
			if ipd_doc and ipd_doc.is_set_item and set_item_stitching_attrs.get(value):
				part = set_item_stitching_attrs[value]
				row["major_attribute_value"] = set_item_packing_combination[item["major_attribute"]][part]
			item_detail.append(row)
	return item_detail


@frappe.whitelist()
def get_ipd_item_group():
	"""Return list of Item Group names used to filter Item picker on IPD form.
	production_api reads this from MRP Settings; yrp_essdee returns all groups."""
	groups = frappe.get_all("Item Group", pluck="name")
	return groups or []


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_attribute_detail_values(doctype, txt, searchfield, start, page_len, filters):
	"""Search-widget for Item Attribute Value filtered by mapping (Item Item
	Attribute Mapping or Item Dependent Attribute Mapping)."""
	mapping = (filters or {}).get("mapping")
	if not mapping:
		return []
	# The mapping arg may point at an Item Item Attribute Mapping (item-attribute
	# values) or an Item Dependent Attribute Mapping (stage values via `details`).
	if frappe.db.exists("Item Item Attribute Mapping", mapping):
		rows = frappe.get_all(
			"Item Item Attribute Mapping Value",
			filters={"parent": mapping},
			fields=["attribute_value as name"],
			limit_start=int(start or 0),
			limit_page_length=int(page_len or 20),
		)
		return [(r["name"],) for r in rows if not txt or txt.lower() in (r["name"] or "").lower()]
	if frappe.db.exists("Item Dependent Attribute Mapping", mapping):
		rows = frappe.get_all(
			"Item Dependent Attribute Mapping Detail",
			filters={"parent": mapping},
			fields=["attribute_value as name"],
			limit_start=int(start or 0),
			limit_page_length=int(page_len or 20),
		)
		return [(r["name"],) for r in rows if not txt or txt.lower() in (r["name"] or "").lower()]
	return []


@frappe.whitelist()
def get_mapping_attribute_values(attribute_mapping_value, attribute_no=None):
	"""Return values from an Item Item Attribute Mapping, optionally limited to N rows.
	Used by Get Packing Attribute Values + Get Stiching Attribute Values buttons."""
	if not attribute_mapping_value or not frappe.db.exists("Item Item Attribute Mapping", attribute_mapping_value):
		return []
	m = frappe.get_doc("Item Item Attribute Mapping", attribute_mapping_value)
	if attribute_no in (None, "", "null", "None"):
		return [{"stiching_attribute_value": v.attribute_value, "quantity": 0} for v in (m.values or [])]

	values = [{"attribute_value": v.attribute_value, "quantity": 0} for v in (m.values or [])]
	try:
		n = int(attribute_no)
		values = values[: max(n, 0)]
	except (TypeError, ValueError):
		pass
	return values


@frappe.whitelist()
def get_stiching_in_stage_attributes(dependent_attribute_mapping, stiching_in_stage, item=None):
	"""For the given dependent stage, return the depending attributes."""
	if not dependent_attribute_mapping or not stiching_in_stage:
		return []
	if not frappe.db.exists("Item Dependent Attribute Mapping", dependent_attribute_mapping):
		return []
	from yrp.yrp.doctype.item_dependent_attribute_mapping.item_dependent_attribute_mapping import (
		get_dependent_attribute_details,
	)

	attribute_details = get_dependent_attribute_details(dependent_attribute_mapping)
	for attr in attribute_details.get("attr_list") or {}:
		if attr == stiching_in_stage:
			return attribute_details["attr_list"][attr].get("attributes") or []
	return []


@frappe.whitelist()
def approve_ipd(doc_name, approval_type):
	"""Set IPD approval_status. production_api enforces role checks via MRP
	Settings; yrp_essdee delegates to Frappe's permission system."""
	if approval_type not in ("Cutting Approved", "Approved"):
		frappe.throw(f"Invalid approval_type: {approval_type}")
	doc = frappe.get_doc("Item Production Detail", doc_name)
	doc.approval_status = approval_type
	if approval_type == "Approved":
		doc.approved_by = frappe.session.user
	doc.save(ignore_permissions=True)
	return doc.approval_status


@frappe.whitelist()
def revert_ipd_approval(doc_name):
	doc = frappe.get_doc("Item Production Detail", doc_name)
	doc.approval_status = "Not Approved"
	doc.approved_by = None
	doc.save(ignore_permissions=True)
	return doc.approval_status


@frappe.whitelist()
def get_new_combination(attribute_mapping_value, packing_attribute_details=None, major_attribute_value=None, is_same_packing_attribute=0, doc_name=None):
	"""Build the production_api CombinationItemDetail payload for set/stiching."""
	packing_attribute_details = update_if_string_instance(packing_attribute_details)
	if not attribute_mapping_value or not frappe.db.exists("Item Item Attribute Mapping", attribute_mapping_value):
		return {"attributes": [], "values": []}

	mapping_doc = frappe.get_doc("Item Item Attribute Mapping", attribute_mapping_value)
	attributes = [row.attribute_value for row in (mapping_doc.values or [])]

	stiching_item_details = {}
	set_item_details = {}
	is_default_list = []
	ipd_doc = None
	if doc_name:
		ipd_doc = frappe.get_doc("Item Production Detail", doc_name)
		if ipd_doc.is_set_item:
			for row in ipd_doc.stiching_item_details or []:
				stiching_item_details[row.stiching_attribute_value] = row.set_item_attribute_value
				if row.is_default:
					is_default_list.append(row.stiching_attribute_value)
			for row in ipd_doc.set_item_combination_details or []:
				set_item_details.setdefault(row.major_attribute_value, {})
				set_item_details[row.major_attribute_value][row.set_item_attribute_value] = row.attribute_value

	item_detail = []
	is_same_packing_attribute = _is_truthy(is_same_packing_attribute)
	for row in packing_attribute_details:
		major_value = _row_value(row, "attribute_value")
		if not major_value:
			continue
		item_list = {
			"major_attribute": major_value,
			"val": {},
		}
		for attr_value in attributes:
			if attr_value == major_attribute_value:
				item_list["val"][attr_value] = major_value
			elif is_same_packing_attribute:
				if ipd_doc and ipd_doc.is_set_item:
					part = stiching_item_details.get(attr_value)
					item_list["val"][attr_value] = set_item_details.get(major_value, {}).get(part)
				else:
					item_list["val"][attr_value] = major_value
			elif ipd_doc and ipd_doc.is_set_item and attr_value in is_default_list:
				part = stiching_item_details.get(attr_value)
				item_list["val"][attr_value] = set_item_details.get(major_value, {}).get(part)
			else:
				item_list["val"][attr_value] = None
		item_detail.append(item_list)

	return {
		"attributes": attributes,
		"values": item_detail,
	}


@frappe.whitelist()
def get_combination(doc_name, attributes, combination_type, cloth_list=None):
	ipd_doc = frappe.get_doc("Item Production Detail", doc_name)
	attributes = update_if_string_instance(attributes)
	item_attributes = ipd_doc.item_attributes
	packing_attr = ipd_doc.packing_attribute
	packing_attr_details = ipd_doc.packing_attribute_details

	cloth_colours = []
	for pack_attr in packing_attr_details or []:
		cloth_colours.append(pack_attr.attribute_value)

	if ipd_doc.is_set_item:
		for row in ipd_doc.set_item_combination_details or []:
			if row.attribute_value not in cloth_colours:
				cloth_colours.append(row.attribute_value)

	item_attr_val_list = get_combination_attr_list(attributes, packing_attr, cloth_colours, item_attributes)
	part_accessory_combination = {}
	accessory_list = []
	if combination_type == "Accessory":
		cloth_accessories = update_if_string_instance(ipd_doc.accessory_clothtype_json)
		for cloth_accessory, cloth in cloth_accessories.items():
			accessory_list.append(cloth_accessory)
			part_accessory_combination.setdefault(cloth, []).append(cloth_accessory)
	else:
		cloth_list = update_if_string_instance(cloth_list)

	stich_attr = ipd_doc.stiching_attribute
	is_set_item = ipd_doc.is_set_item
	set_attr = ipd_doc.set_item_attribute if is_set_item else None
	pack_attr = ipd_doc.packing_attribute

	item_list = []
	if len(attributes) == 1:
		for attr_val in item_attr_val_list[attributes[0]]:
			if combination_type == "Cutting":
				item_list.append({
					attributes[0]: attr_val,
					"Dia": None,
					"Weight": None,
				})
			elif combination_type == "Accessory":
				if attributes[0] == set_attr:
					if attr_val in part_accessory_combination:
						for acc in part_accessory_combination[attr_val]:
							item_list.append({
								attributes[0]: attr_val,
								"Accessory": acc,
								"Dia": None,
								"Weight": None,
							})
				else:
					for acc in accessory_list:
						item_list.append({
							attributes[0]: attr_val,
							"Accessory": acc,
							"Dia": None,
							"Weight": None,
						})
			else:
				item_list.append({
					attributes[0]: attr_val,
					"Cloth": None,
				})
	elif is_set_item and pack_attr in attributes and set_attr in attributes and stich_attr in attributes:
		item_attr_list = item_attr_val_list.copy()
		del item_attr_list[pack_attr]
		del item_attr_list[stich_attr]

		set_data = {set_attr: {}}
		for value in item_attr_val_list[set_attr]:
			set_data[set_attr][value] = {
				pack_attr: [],
				stich_attr: [],
			}

		item_attr_list[set_attr] = set_data[set_attr]
		item_attr_list = get_set_tri_struct(ipd_doc, item_attr_list, set_attr, pack_attr, stich_attr)

		set_attr_values = item_attr_list[set_attr]
		del item_attr_list[set_attr]

		attributes = pop_attributes(attributes, [set_attr, pack_attr, stich_attr])
		items = get_set_tri_combination(set_attr_values, set_attr, pack_attr, stich_attr, combination_type, part_accessory_combination)
		item_list = make_comb_list(attributes, items, combination_type, item_attr_list)

		attributes.append(set_attr)
		attributes.append(pack_attr)
		attributes.append(stich_attr)

	elif is_set_item and pack_attr in attributes and set_attr in attributes and stich_attr not in attributes:
		item_attr_list = item_attr_val_list.copy()
		del item_attr_list[pack_attr]

		set_data = {set_attr: {}}
		for value in item_attr_val_list[set_attr]:
			set_data[set_attr][value] = []

		item_attr_list[set_attr] = set_data[set_attr]
		for row in ipd_doc.set_item_combination_details or []:
			if row.attribute_value not in item_attr_list[set_attr][row.set_item_attribute_value]:
				item_attr_list[set_attr][row.set_item_attribute_value].append(row.attribute_value)

		set_attr_values = item_attr_list[set_attr]
		del item_attr_list[set_attr]

		attributes = pop_attributes(attributes, [set_attr, pack_attr])
		items = get_comb_items(set_attr_values, set_attr, pack_attr, combination_type, part_accessory_combination)
		item_list = make_comb_list(attributes, items, combination_type, item_attr_list)
		attributes.append(set_attr)
		attributes.append(pack_attr)

	elif is_set_item and stich_attr in attributes and set_attr in attributes and pack_attr not in attributes:
		item_attr_list = change_attr_list(item_attr_val_list, ipd_doc.stiching_item_details, stich_attr, set_attr)
		set_attr_values = item_attr_list[set_attr]
		del item_attr_list[set_attr]
		attributes = pop_attributes(attributes, [set_attr, stich_attr])
		items = get_comb_items(set_attr_values, set_attr, stich_attr, combination_type, part_accessory_combination)
		item_list = make_comb_list(attributes, items, combination_type, item_attr_list)
		attributes.append(set_attr)
		attributes.append(stich_attr)

	elif not is_set_item and pack_attr in attributes and stich_attr in attributes:
		item_attr_list = change_pack_stich_attr_list(item_attr_val_list, ipd_doc.stiching_item_combination_details, stich_attr, pack_attr)
		pack_attr_values = item_attr_list[pack_attr]
		del item_attr_list[pack_attr]
		attributes = pop_attributes(attributes, [pack_attr, stich_attr])
		items = get_comb_items(pack_attr_values, stich_attr, pack_attr, combination_type, part_accessory_combination)
		item_list = make_comb_list(attributes, items, combination_type, item_attr_list)
		attributes.append(stich_attr)
		attributes.append(pack_attr)

	else:
		item_list = get_item_list(item_attr_val_list, attributes)
		items = []
		if is_set_item and combination_type == "Accessory":
			for item in item_list:
				if item[set_attr] in part_accessory_combination:
					for accessory in part_accessory_combination[item[set_attr]]:
						row = item.copy()
						row["Accessory"] = accessory
						items.append(row)
		elif combination_type == "Accessory":
			for item in item_list:
				for accessory in accessory_list:
					row = item.copy()
					row["Accessory"] = accessory
					items.append(row)
		else:
			items = item_list
		for item in items:
			add_combination_value(combination_type, item)
		item_list = items

	if combination_type == "Cutting":
		additional_attr = ["Dia", "Weight"]
	elif combination_type == "Accessory":
		additional_attr = ["Accessory", "Dia", "Weight"]
	else:
		additional_attr = ["Cloth"]

	select_list = accessory_list if combination_type == "Accessory" else cloth_list
	return {
		"combination_type": combination_type,
		"attributes": attributes + additional_attr,
		"items": item_list,
		"select_list": select_list,
	}


def pop_attributes(attributes, attr_list):
	for attr in attr_list:
		if attr in attributes:
			attributes.pop(attributes.index(attr))
	return attributes


def get_set_tri_struct(ipd_doc, item_attr_list, set_attr, pack_attr, stich_attr):
	for row in ipd_doc.set_item_combination_details or []:
		if row.attribute_value not in item_attr_list[set_attr][row.set_item_attribute_value][pack_attr]:
			item_attr_list[set_attr][row.set_item_attribute_value][pack_attr].append(row.attribute_value)

	for row in ipd_doc.stiching_item_details or []:
		item_attr_list[set_attr][row.set_item_attribute_value][stich_attr].append(row.stiching_attribute_value)

	return item_attr_list


def get_set_tri_combination(set_attr_values, set_attr, pack_attr, stich_attr, combination_type, accessory_combination):
	items = []
	for value in set_attr_values:
		base = {set_attr: value}
		for pack_value in set_attr_values[value][pack_attr]:
			base[pack_attr] = pack_value
			for stich_value in set_attr_values[value][stich_attr]:
				if combination_type == "Accessory":
					if value in accessory_combination:
						for accessory in accessory_combination[value]:
							row = base.copy()
							row[stich_attr] = stich_value
							row["Accessory"] = accessory
							items.append(row)
				else:
					row = base.copy()
					row[stich_attr] = stich_value
					items.append(row)
	return items


def get_comb_items(set_attr_values, attr1, attr2, combination_type, accessory_combination):
	items = []
	for attribute1, attribute2 in set_attr_values.items():
		for attr2_data in attribute2:
			if combination_type == "Accessory":
				if attribute1 in accessory_combination:
					for accessory in accessory_combination[attribute1]:
						items.append({
							attr1: attribute1,
							attr2: attr2_data,
							"Accessory": accessory,
						})
			else:
				items.append({
					attr1: attribute1,
					attr2: attr2_data,
				})
	return items


def make_comb_list(attributes, items, combination_type, item_attr_list):
	if len(attributes) == 0:
		for item in items:
			add_combination_value(combination_type, item)
		return items

	item_list = get_item_list(item_attr_list, attributes)
	final_list = []
	for base in items:
		for item in item_list:
			row = item | base
			add_combination_value(combination_type, row)
			final_list.append(row)
	return final_list


def get_item_list(item_attr_list, attributes):
	if not attributes:
		return []
	attrs_len = {}
	initial_attrs = {}
	for key, value in item_attr_list.items():
		attrs_len[key] = len(value)
		initial_attrs[key] = 0
	if any(length == 0 for length in attrs_len.values()):
		return []

	last_item = attributes[len(attributes) - 1]
	item_list = []
	done = False
	while True:
		temp = {}
		for item, item_values in item_attr_list.items():
			temp[item] = item_values[initial_attrs[item]]
			if item == last_item:
				initial_attrs[item] += 1
				if initial_attrs[item] == attrs_len[item]:
					initial_attrs = update_attr_combination(initial_attrs, attributes, last_item, attrs_len)
			if initial_attrs is None:
				done = True
		item_list.append(temp)
		if done:
			break
	return item_list


def change_attr_list(item_attr_val_list, stiching_item_details, stiching_attr, set_attr):
	attr_list = item_attr_val_list.copy()
	stiching_details = {}
	for row in stiching_item_details or []:
		stiching_details.setdefault(row.set_item_attribute_value, []).append(row.stiching_attribute_value)

	if stiching_attr in attr_list:
		del attr_list[stiching_attr]
	attr_list[set_attr] = stiching_details
	return attr_list


def change_pack_stich_attr_list(item_attr_val_list, stiching_item_combination_details, stiching_attr, pack_attr):
	attr_list = item_attr_val_list.copy()
	panel_details = {}
	for row in stiching_item_combination_details or []:
		panel_details.setdefault(row.set_item_attribute_value, [])
		if row.attribute_value not in panel_details[row.set_item_attribute_value]:
			panel_details[row.set_item_attribute_value].append(row.attribute_value)
	if stiching_attr in attr_list:
		del attr_list[stiching_attr]
	attr_list[pack_attr] = panel_details
	return attr_list


def add_combination_value(combination_type, item):
	if combination_type == "Cutting":
		item["Dia"] = None
		item["Weight"] = None
	elif combination_type == "Cloth":
		item["Cloth"] = None
	else:
		item["Dia"] = None
		item["Weight"] = None
	return item


@frappe.whitelist()
def get_stiching_accessory_combination(cloth_list, doc_name):
	ipd_doc = frappe.get_doc("Item Production Detail", doc_name)
	cloth_list = update_if_string_instance(cloth_list)
	combination_list = {
		"select_list": cloth_list,
		"attributes": [],
		"items": [],
	}
	cloth_accessories = update_if_string_instance(ipd_doc.accessory_clothtype_json)
	if ipd_doc.is_set_item:
		combination_list["is_set_item"] = 1
		combination_list["set_attr"] = ipd_doc.set_item_attribute
		combination_list["attributes"] = ["Accessory", ipd_doc.set_item_attribute, "Major Colour", "Accessory Colour", "Cloth"]
		part_colours = {}
		set_colours = {}
		for row in ipd_doc.set_item_combination_details or []:
			set_colours.setdefault(row.index, {})
			set_colours[row.index][row.set_item_attribute_value] = row.attribute_value
			part_colours.setdefault(row.set_item_attribute_value, [])
			part_colours[row.set_item_attribute_value].append(row.attribute_value)
		for accessory, part in cloth_accessories.items():
			base = {
				"accessory": accessory,
				ipd_doc.set_item_attribute: part,
			}
			for idx, colour in enumerate(part_colours.get(part, [])):
				row = base.copy()
				row["major_colour"] = colour
				row["accessory_colour"] = None
				row["cloth_type"] = None
				if part != ipd_doc.major_attribute_value:
					row["major_attr_value"] = set_colours.get(idx, {}).get(ipd_doc.major_attribute_value)
				combination_list["items"].append(row)
	else:
		combination_list["is_set_item"] = 0
		combination_list["attributes"] = ["Accessory", "Major Colour", "Accessory Colour", "Cloth"]
		colours = [row.attribute_value for row in (ipd_doc.packing_attribute_details or [])]
		for accessory, _part in cloth_accessories.items():
			for colour in colours:
				combination_list["items"].append({
					"accessory": accessory,
					"major_colour": colour,
					"accessory_colour": None,
					"cloth_type": None,
				})
	return combination_list


def get_combination_attr_list(attributes, packing_attr, pack_details, item_attributes):
	item_attr_value_list = {}
	for item in item_attributes or []:
		if item.attribute in attributes:
			item_attr_value_list[item.attribute] = get_attr_mapping_details(item.mapping)
	item_attr_value_list[packing_attr] = pack_details
	return {attr: item_attr_value_list[attr] for attr in attributes if attr in item_attr_value_list}


def update_attr_combination(initial_attrs, attributes, last_item, attrs_len):
	for i in range(len(attributes) - 1, -1, -1):
		if attributes[i] != last_item:
			index = initial_attrs[attributes[i]] + 1
			if index < attrs_len[attributes[i]]:
				initial_attrs[attributes[i]] = index
				for j in range(len(attributes) - 1, -1, -1):
					if attributes[j] == attributes[i]:
						return initial_attrs
					initial_attrs[attributes[j]] = 0
	return None


@frappe.whitelist()
def duplicate_ipd(ipd, item):
	"""Duplicate an IPD onto a new item — returns the new IPD name."""
	src = frappe.get_doc("Item Production Detail", ipd)
	new_doc = frappe.copy_doc(src, ignore_no_copy=False)
	new_doc.item = item
	new_doc.approval_status = "Not Approved"
	new_doc.approved_by = None
	new_doc.amended_from = None
	new_doc.insert(ignore_permissions=True)
	return new_doc.name


@frappe.whitelist()
def get_attr_mapping_details(mapping=None, item=None):
	"""Return attribute values for EmblishmentDetails.

	The ported Vue component calls this with an Item Item Attribute Mapping
	name, matching production_api. Keep the item-based response as a fallback
	for any local callers that need the full attribute -> values map.
	"""
	if mapping:
		if not frappe.db.exists("Item Item Attribute Mapping", mapping):
			return []
		m = frappe.get_doc("Item Item Attribute Mapping", mapping)
		return [v.attribute_value for v in (m.values or [])]

	if not item or not frappe.db.exists("Item", item):
		return {}
	idoc = frappe.get_doc("Item", item)
	out = {}
	for ar in idoc.attributes or []:
		if not ar.mapping or not frappe.db.exists("Item Item Attribute Mapping", ar.mapping):
			continue
		m = frappe.get_doc("Item Item Attribute Mapping", ar.mapping)
		out[ar.attribute] = [v.attribute_value for v in (m.values or [])]
	return out
