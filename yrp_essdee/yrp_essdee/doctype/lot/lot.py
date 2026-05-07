"""Lot controller for yrp_essdee.

This mirrors production_api's Lot behavior for the non-Time-and-Action flow.
The BOM calculation intentionally stays on YRP's IPD Matrix engine because
yrp_essdee runs on the base YRP process model.
"""

import json
import math
from itertools import groupby

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime

from yrp.yrp.doctype.item.item import get_attribute_details, get_or_create_variant
from yrp.yrp.doctype.item_dependent_attribute_mapping.item_dependent_attribute_mapping import (
	get_dependent_attribute_details,
)


class Lot(Document):
	def before_submit(self):
		if len(self.get("bom_summary") or []) == 0:
			frappe.throw("BOM is not calculated")

	def before_validate(self):
		if self.get("item_details"):
			items = save_item_details(self.item_details)
			self.set("items", items)

		if self.get("order_item_details") and self.production_detail:
			order_items = save_order_item_details(
				self.production_detail,
				self.get("lot_order_details") or [],
				self.order_item_details,
			)
			self.set("lot_order_details", order_items)

		if self.is_new():
			if not self.lot_hash_value:
				self.lot_hash_value = make_autoname(key="hash")
			if len(self.get("items") or []) > 0:
				self.calculate_order()
		else:
			try:
				doc = frappe.get_doc("Lot", self.name)
			except Exception:
				doc = None
			if doc and len(doc.get("items") or []) == 0 and len(self.get("items") or []) > 0:
				self.calculate_order()

			self.total_quantity = sum(float(item.qty or 0) for item in (self.get("items") or []))

		self.total_order_quantity = sum(
			float(item.quantity or 0) for item in (self.get("lot_order_details") or [])
		)

	def validate(self):
		self._fetch_item_from_production_order()
		self._validate_item_matches_ipd()
		self._roll_up_totals()

	def before_save(self):
		if self.is_new():
			return

		prev_ppo = frappe.db.get_value("Lot", self.name, "production_order")
		cur_ppo = self.production_order

		if not prev_ppo and not cur_ppo:
			return

		if prev_ppo:
			delete_ppo_lot_qty(prev_ppo, self.name)
		if cur_ppo:
			add_ppo_lot_qty(cur_ppo, self.name, self.get("items") or [])

	def after_insert(self):
		if len(self.get("items") or []) > 0 and self.production_order:
			add_ppo_lot_qty(self.production_order, self.name, self.get("items") or [])

	def calculate_order(self):
		previous_data = {}
		for item in self.get("lot_order_details") or []:
			set_combination = update_if_string_instance(item.set_combination)
			if set_combination not in [None, ""]:
				set_combination = set_combination.copy()
				set_combination.update({"variant": item.item_variant})
				previous_data[frozenset(set_combination.items())] = {
					"cut_qty": item.cut_qty,
					"stich_qty": item.stich_qty,
					"pack_qty": item.pack_qty,
				}

		items, qty = calculate_order_details(
			self.get("items") or [],
			self.production_detail,
			self.packing_uom,
			self.uom,
		)
		if len(items) == 0:
			fallback = []
			for item in self.get("items") or []:
				fallback.append({"item_variant": item.item_variant, "quantity": item.qty})
				qty += item.qty
			self.set("lot_order_details", fallback)
			self.total_order_quantity = qty
			return

		for item in items:
			key = update_if_string_instance(item.get("set_combination"))
			if key not in [None, ""]:
				key = key.copy()
				key.update({"variant": item.get("item_variant")})
				old_values = previous_data.get(frozenset(key.items()))
				if old_values:
					item.update(old_values)

		self.set("lot_order_details", items)
		self.total_order_quantity = qty

	def onload(self):
		if not self.production_detail:
			return

		item_details = fetch_item_details(self.get("items") or [], self.production_detail)
		self.set_onload("item_details", item_details)

		if len(self.get("lot_order_details") or []) > 0:
			items = fetch_order_item_details(self.get("lot_order_details") or [], self.production_detail)
			if items:
				self.db_set("lot_order_details_json", json.dumps(items[0], default=str), update_modified=False)
			self.set_onload("order_item_details", items)

	def _fetch_item_from_production_order(self):
		if not self.production_order:
			return
		from yrp_essdee.overrides.production_order import get_production_order_item

		item = get_production_order_item(self.production_order)
		if item:
			self.item = item

	def _validate_item_matches_ipd(self):
		if not (self.production_detail and self.item):
			return
		ipd_item = frappe.db.get_value("Item Production Detail", self.production_detail, "item")
		if ipd_item and ipd_item != self.item:
			frappe.throw(
				f"IPD {self.production_detail} is for item {ipd_item}, "
				f"but this Lot's item is {self.item}."
			)

	def _roll_up_totals(self):
		self.total_order_quantity = int(
			sum(float(r.quantity or 0) for r in (self.get("lot_order_details") or []))
		)
		self.total_quantity = int(sum(float(r.qty or 0) for r in (self.get("items") or [])))


def update_if_string_instance(obj):
	if isinstance(obj, str):
		obj = json.loads(obj)
	if not obj:
		obj = {}
	return obj


def _as_dict(row):
	if hasattr(row, "as_dict"):
		return row.as_dict()
	return row or {}


def _row_get(row, key, default=None):
	if isinstance(row, dict):
		return row.get(key, default)
	return getattr(row, key, default)


def delete_ppo_lot_qty(ppo, lot):
	if not frappe.db.exists("DocType", "Production Ordered Detail"):
		return
	frappe.db.sql(
		"""
		DELETE FROM `tabProduction Ordered Detail`
		WHERE parent = %s
		  AND reference_doctype = 'Lot'
		  AND reference_name = %s
		""",
		(ppo, lot),
	)


def add_ppo_lot_qty(ppo, lot, items):
	if not frappe.db.exists("DocType", "Production Ordered Detail"):
		return
	for item in items:
		doc = frappe.new_doc("Production Ordered Detail")
		doc.parent = ppo
		doc.parenttype = "Production Order"
		doc.parentfield = "production_ordered_details"
		doc.reference_doctype = "Lot"
		doc.reference_name = lot
		doc.item_variant = item.item_variant
		doc.quantity = item.qty
		doc.save(ignore_permissions=True)


def calculate_order_details(items, production_detail, packing_uom, final_uom):
	item_detail = frappe.get_cached_doc("Item Production Detail", production_detail)
	final_list = []
	doc = frappe.get_cached_doc("Item", item_detail.item)
	dept_attr = None
	pack_stage = None
	if item_detail.dependent_attribute:
		pack_stage = item_detail.pack_in_stage
		dept_attr = item_detail.dependent_attribute

	uom_factor = get_uom_conversion_factor(doc.uom_conversion_details, final_uom, packing_uom)
	final_qty = 0

	attrs = {}
	parts = []
	comb_dict = {}
	if item_detail.is_set_item:
		for attr in item_detail.set_item_combination_details:
			comb_dict.setdefault(attr.major_attribute_value, {})
			comb_dict[attr.major_attribute_value].setdefault(
				attr.set_item_attribute_value,
				attr.attribute_value,
			)
			if attr.set_item_attribute_value not in parts:
				parts.append(attr.set_item_attribute_value)

	x = 0
	if item_detail.is_set_item:
		major_part = item_detail.major_attribute_value
		for attr in item_detail.packing_attribute_details:
			for part in parts:
				colour = comb_dict.get(attr.attribute_value, {}).get(part)
				item_list = []
				for item in items:
					variant = frappe.get_cached_doc("Item Variant", item.item_variant)
					qty = item.qty * uom_factor
					if item_detail.auto_calculate:
						qty = qty / item_detail.packing_attribute_no
					else:
						qty = qty / item_detail.packing_combo

					attrs = {}
					for attribute in variant.attributes:
						attribute = attribute.as_dict()
						if attribute.attribute == dept_attr:
							attrs[attribute.attribute] = pack_stage
						else:
							attrs[attribute.attribute] = attribute["attribute_value"]

					attrs[item_detail.packing_attribute] = colour
					attrs[item_detail.set_item_attribute] = part
					new_variant = get_or_create_variant(
						variant.item,
						attrs,
						dependent_attr=item_detail.dependent_attribute_mapping,
					)
					temp_qty = (
						math.ceil(qty)
						if item_detail.auto_calculate
						else math.ceil(qty * attr.quantity)
					)
					if item_detail.major_attribute_value == part:
						final_qty += temp_qty

					row = {
						"item_variant": new_variant,
						"quantity": temp_qty,
						"row_index": x,
						"table_index": 0,
						"set_combination": {},
					}
					if part == major_part:
						row["set_combination"]["major_part"] = part
						row["set_combination"]["major_colour"] = colour
					else:
						row["set_combination"]["major_part"] = major_part
						row["set_combination"]["major_colour"] = comb_dict.get(
							attr.attribute_value,
							{},
						).get(major_part)
					item_list.append(row)
				x += 1
				final_list += item_list
	else:
		for attr in item_detail.packing_attribute_details:
			item_list = []
			for item in items:
				variant = frappe.get_cached_doc("Item Variant", item.item_variant)
				qty = item.qty * uom_factor
				if item_detail.auto_calculate:
					qty = qty / item_detail.packing_attribute_no
				else:
					qty = qty / item_detail.packing_combo

				attrs = {}
				for attribute in variant.attributes:
					attribute = attribute.as_dict()
					if attribute.attribute == dept_attr:
						attrs[attribute.attribute] = pack_stage
					else:
						attrs[attribute.attribute] = attribute["attribute_value"]

				attrs[item_detail.packing_attribute] = attr.attribute_value
				new_variant = get_or_create_variant(
					variant.item,
					attrs,
					dependent_attr=item_detail.dependent_attribute_mapping,
				)
				temp_qty = (
					math.ceil(qty)
					if item_detail.auto_calculate
					else math.ceil(qty * attr.quantity)
				)
				final_qty += temp_qty
				item_list.append({
					"item_variant": new_variant,
					"quantity": temp_qty,
					"row_index": x,
					"table_index": 0,
					"set_combination": {"major_colour": attr.attribute_value},
				})
			x += 1
			final_list += item_list

	return final_list, final_qty


def save_order_item_details(name, lot_order_details, item_details):
	item_details = update_if_string_instance(item_details)
	if isinstance(item_details, dict):
		item_details = [item_details] if item_details else []

	qty_dict = {}
	for item in lot_order_details or []:
		set_comb = update_if_string_instance(item.set_combination)
		key = (item.item_variant, tuple(sorted(set_comb.items())))
		qty_dict[key] = {
			"cut_qty": item.cut_qty,
			"pack_qty": item.pack_qty,
			"stich_qty": item.stich_qty,
		}

	items = []
	row_index = 0
	for group in item_details or []:
		for item in group.get("items") or []:
			item_name = item.get("name")
			item_attributes = dict(item.get("attributes") or {})
			primary_attribute = item.get("primary_attribute")
			for attr, values in (item.get("values") or {}).items():
				quantity = values.get("qty") or 0
				if primary_attribute:
					item_attributes[primary_attribute] = attr
				variant = get_or_create_variant(item_name, item_attributes)
				set_comb = update_if_string_instance(item.get("item_keys"))
				key = (variant, tuple(sorted(set_comb.items())))
				old_qty = qty_dict.get(key, {})
				items.append({
					"item_variant": variant,
					"quantity": quantity,
					"row_index": row_index,
					"table_index": 0,
					"cut_qty": old_qty.get("cut_qty", 0),
					"pack_qty": old_qty.get("pack_qty", 0),
					"stich_qty": old_qty.get("stich_qty", 0),
					"set_combination": item.get("item_keys") or {},
				})
			row_index += 1
	return items


def save_item_details(item_details):
	item_details = update_if_string_instance(item_details)
	if isinstance(item_details, dict):
		item_details = [item_details] if item_details else []
	if len(item_details) == 0:
		return []

	item = item_details[0]
	items = []
	for id1, row in enumerate(item.get("items") or []):
		if row.get("primary_attribute"):
			attributes = dict(row.get("attributes") or {})
			if item.get("dependent_attribute") and item.get("final_state"):
				attributes[item["dependent_attribute"]] = item["final_state"]
			for id2, val in enumerate((row.get("values") or {}).keys()):
				cell = row["values"][val]
				attrs = attributes.copy()
				attrs[row["primary_attribute"]] = val
				variant_name = get_or_create_variant(item["item"], attrs)
				items.append({
					"item_variant": variant_name,
					"qty": cell.get("qty") or 0,
					"ratio": cell.get("ratio") or 0,
					"mrp": cell.get("mrp") or 0,
					"table_index": id1,
					"row_index": id2,
				})
		else:
			attributes = dict(row.get("attributes") or {})
			variant_name = get_or_create_variant(item["item"], attributes)
			values = row.get("values") or {}
			items.append({
				"item_variant": variant_name,
				"qty": values.get("qty") or 0,
				"ratio": values.get("ratio") or 0,
				"mrp": values.get("mrp") or 0,
				"table_index": id1,
			})
	return items


def fetch_item_details(items, production_detail):
	items = [_as_dict(item) for item in (items or [])]
	if len(items) == 0:
		return None

	dependent_attr_map_value = frappe.get_value(
		"Item Production Detail",
		production_detail,
		"dependent_attribute_mapping",
	)
	grp_variant = frappe.get_value("Item Variant", items[0]["item_variant"], "item")
	variant_attr_details = get_attribute_details(
		grp_variant,
		dependent_attr_mapping=dependent_attr_map_value,
	)
	primary_attr = variant_attr_details["primary_attribute"]
	uom = get_isfinal_uom(production_detail)["uom"]
	doc = frappe.get_cached_doc("Item", grp_variant)
	item_structure = get_item_details(
		grp_variant,
		attr_details=variant_attr_details,
		uom=uom,
		production_detail=production_detail,
		dependent_attr_mapping=dependent_attr_map_value,
	)
	if not isinstance(item_structure, dict):
		return item_structure

	item_attribute_details = {}
	items = sorted(items, key=lambda i: i.get("table_index") or 0)
	for _, variants in groupby(items, lambda i: i.get("table_index") or 0):
		variants = list(variants)
		item1 = {}
		values = {}
		for variant in variants:
			current_variant = frappe.get_cached_doc("Item Variant", variant["item_variant"])
			item_attribute_details = get_item_attribute_details(current_variant, variant_attr_details)
			if doc.dependent_attribute and doc.dependent_attribute in item_attribute_details:
				del item_attribute_details[doc.dependent_attribute]
			if doc.primary_attribute:
				for attr in current_variant.attributes:
					if attr.attribute == primary_attr:
						values[attr.attribute_value] = {
							"qty": variant.get("qty") or 0,
							"ratio": variant.get("ratio") or 0,
							"mrp": variant.get("mrp") or 0,
						}
						break
			else:
				values["qty"] = variant.get("qty") or 0
				values["ratio"] = variant.get("ratio") or 0
				values["mrp"] = variant.get("mrp") or 0

		attrs = {}
		for attr in item_structure.get("attributes") or []:
			if attr in item_attribute_details:
				attrs[attr] = item_attribute_details[attr]

		item1["primary_attribute"] = primary_attr or None
		item1["attributes"] = attrs
		item1["values"] = values
		item_structure["items"].append(item1)
	return item_structure


@frappe.whitelist()
def fetch_order_item_details(items, production_detail, process=None, includes_packing: bool = False):
	ipd_doc = frappe.get_doc("Item Production Detail", production_detail)
	items = update_if_string_instance(items)
	if isinstance(items, dict):
		items = [items] if items else []
	items = [_as_dict(item) for item in (items or [])]
	if not items:
		return []

	field = "quantity"
	if process:
		if frappe.db.exists("DocType", "Process") and frappe.db.exists("Process", process):
			prs_doc = frappe.get_cached_doc("Process", process)
			if getattr(prs_doc, "is_group", 0):
				for prs in prs_doc.process_details:
					process = prs.process_name
					break

		field = (
			"quantity"
			if process == getattr(ipd_doc, "cutting_process", None)
			else "cut_qty"
			if process == getattr(ipd_doc, "stiching_process", None)
			else "stich_qty"
			if process == getattr(ipd_doc, "packing_process", None)
			else None
		)
		if includes_packing:
			field = "cut_qty"
		if not field:
			stage = None
			for prs in ipd_doc.ipd_processes:
				if prs.process_name == process:
					stage = getattr(prs, "stage", None) or getattr(prs, "out_stage", None)
					break
			if stage:
				field = (
					"cut_qty"
					if stage == getattr(ipd_doc, "stiching_in_stage", None)
					else "stich_qty"
					if stage == getattr(ipd_doc, "pack_in_stage", None)
					else "pack_qty"
				)

		if not field:
			frappe.msgprint(f"Please Mention Process {process} in IPD")
			return []

	item_details = []
	items = sorted(items, key=lambda i: i.get("row_index") or 0)
	primary_values = get_ipd_primary_values(production_detail)
	for _, variants in groupby(items, lambda i: i.get("row_index") or 0):
		variants = list(variants)
		current_variant = frappe.get_cached_doc("Item Variant", variants[0]["item_variant"])
		current_item_attribute_details = get_attribute_details(
			current_variant.item,
			dependent_attr_mapping=ipd_doc.dependent_attribute_mapping,
		)
		item = {
			"name": current_variant.item,
			"attributes": get_item_attribute_details(current_variant, current_item_attribute_details),
			"item_keys": {},
			"is_set_item": ipd_doc.is_set_item,
			"set_attr": ipd_doc.set_item_attribute,
			"pack_attr": ipd_doc.packing_attribute,
			"major_attr_value": ipd_doc.major_attribute_value,
			"primary_attribute": current_item_attribute_details["primary_attribute"],
			"dependent_attribute": current_item_attribute_details["dependent_attribute"],
			"dependent_attribute_details": current_item_attribute_details[
				"dependent_attribute_details"
			],
			"values": {},
		}
		current_item_attribute_details["primary_attribute_values"] = primary_values
		if item["primary_attribute"]:
			for attr in current_item_attribute_details["primary_attribute_values"]:
				item["values"][attr] = {"qty": 0}
			for variant in variants:
				set_combination = update_if_string_instance(variant.get("set_combination"))
				if set_combination:
					if set_combination.get("major_part"):
						item["item_keys"]["major_part"] = set_combination.get("major_part")
					if set_combination.get("major_colour"):
						item["item_keys"]["major_colour"] = set_combination.get("major_colour")

				current_variant = frappe.get_cached_doc("Item Variant", variant["item_variant"])
				for attr in current_variant.attributes:
					if attr.attribute == item.get("primary_attribute"):
						item["values"][attr.attribute_value] = {
							"qty": variant.get(field) or 0,
						}
						break
		else:
			item["values"]["default"] = {
				"qty": variants[0].get(field) or 0,
			}

		index = get_item_group_index(item_details, current_item_attribute_details)
		if index == -1:
			item_details.append({
				"attributes": current_item_attribute_details["attributes"],
				"primary_attribute": current_item_attribute_details["primary_attribute"],
				"primary_attribute_values": current_item_attribute_details[
					"primary_attribute_values"
				],
				"dependent_attribute": current_item_attribute_details["dependent_attribute"],
				"dependent_attribute_details": current_item_attribute_details[
					"dependent_attribute_details"
				],
				"additional_parameters": current_item_attribute_details["additional_parameters"],
				"stiching_attribute": ipd_doc.stiching_attribute,
				"items": [item],
			})
		else:
			item_details[index]["items"].append(item)

	for item in item_details:
		size_wise_total = {}
		total_sum = 0
		for row in item["items"]:
			row_sum = 0
			for val in row["values"]:
				size_wise_total.setdefault(val, 0)
				size_wise_total[val] += row["values"][val]["qty"]
				row_sum += row["values"][val]["qty"]
			row["total_qty"] = row_sum
			total_sum += row_sum
		item["size_wise_total"] = size_wise_total
		item["total_sum"] = total_sum

	return item_details


def get_item_attribute_details(variant, item_attributes):
	attribute_details = {}
	for attr in variant.attributes:
		if attr.attribute in item_attributes["attributes"]:
			attribute_details[attr.attribute] = attr.attribute_value
	return attribute_details


def variant_attribute_details(variant):
	if isinstance(variant, str):
		variant = frappe.get_cached_doc("Item Variant", variant)
	return {attr.attribute: attr.attribute_value for attr in variant.attributes}


def get_variant_attr_details(variant):
	return _variant_attrs(variant)


def get_item_group_index(items, item_details):
	for i, item in enumerate(items):
		if sorted(item.get("attributes") or []) != sorted(item_details.get("attributes") or []):
			continue
		if item.get("primary_attribute") != item_details.get("primary_attribute"):
			continue
		if sorted(item.get("primary_attribute_values") or []) != sorted(
			item_details.get("primary_attribute_values") or []
		):
			continue
		if item.get("dependent_attribute") != item_details.get("dependent_attribute"):
			continue
		return i
	return -1


@frappe.whitelist()
def get_item_details(
	item_name,
	attr_details=None,
	uom=None,
	production_detail=None,
	dependent_state=None,
	dependent_attr_mapping=None,
	ppo=None,
):
	if not attr_details:
		item = get_attribute_details(item_name, dependent_attr_mapping=dependent_attr_mapping)
	else:
		item = attr_details

	pack_out_stage = (
		frappe.get_value("Item Production Detail", production_detail, "pack_out_stage")
		if production_detail
		else None
	)
	if uom:
		item["default_uom"] = uom

	final_state = None
	final_state_attr = None
	item["items"] = []
	if item["dependent_attribute"]:
		attribute = dependent_state if dependent_state else pack_out_stage
		for attr in item["dependent_attribute_details"].get("attr_list") or {}:
			if attr == attribute:
				final_state = attribute
				final_state_attr = list(
					item["dependent_attribute_details"]["attr_list"][attr].get("attributes") or []
				)
				break
		if not final_state:
			frappe.msgprint("There is no final state for this item")
			return []
		item["final_state"] = final_state
		if item["primary_attribute"] in final_state_attr:
			final_state_attr.remove(item["primary_attribute"])
		item["final_state_attr"] = final_state_attr
	elif not item["dependent_attribute"] and not item["primary_attribute"]:
		doc = frappe.get_cached_doc("Item", item["item"])
		item["final_state_attr"] = [attr.attribute for attr in doc.attributes]
	else:
		item.setdefault("final_state_attr", [])

	if production_detail:
		pack_attr_value = frappe.get_value(
			"Item Production Detail",
			production_detail,
			"packing_attribute",
		)
		item["packing_attr"] = pack_attr_value
		item["primary_attribute_values"] = get_ipd_primary_values(production_detail)
		if ppo:
			primary = frappe.get_value(
				"Item Production Detail",
				production_detail,
				"primary_item_attribute",
			)
			ppo_doc = frappe.get_doc("Production Order", ppo)
			d = {
				"primary_attribute": primary,
				"attributes": {},
				"values": {},
			}
			values = {}
			for row in ppo_doc.production_order_details:
				attrs = _production_order_row_attrs(row)
				if not attrs.get(primary):
					continue
				values.setdefault(attrs[primary], {"qty": 0, "ratio": 0, "mrp": 0})
				values[attrs[primary]]["qty"] += row.quantity or 0
				values[attrs[primary]]["ratio"] = getattr(row, "ratio", 0) or 0
				values[attrs[primary]]["mrp"] = getattr(row, "mrp", 0) or 0
			for row in ppo_doc.production_ordered_details:
				if not row.item_variant:
					continue
				attrs = get_variant_attr_details(row.item_variant)
				if attrs.get(primary) in values:
					values[attrs[primary]]["qty"] -= row.quantity or 0
			d["values"] = values
			item["items"].append(d)

	return item


def _production_order_row_attrs(row):
	if row.item_variant:
		return get_variant_attr_details(row.item_variant)
	if getattr(row, "attributes_json", None):
		return update_if_string_instance(row.attributes_json)
	return {}


@frappe.whitelist()
def get_isfinal_uom(item_production_detail, get_pack_stage=None):
	uom = None
	doc = frappe.get_doc("Item Production Detail", item_production_detail)
	if doc.dependent_attribute_mapping:
		attribute_details = get_dependent_attribute_details(doc.dependent_attribute_mapping)
		if doc.pack_out_stage in attribute_details["attr_list"]:
			uom = attribute_details["attr_list"][doc.pack_out_stage].get("uom")
	else:
		item_doc = frappe.get_cached_doc("Item", doc.item)
		uom = item_doc.default_unit_of_measure

	if get_pack_stage:
		packing_uom = uom
		if doc.dependent_attribute_mapping:
			attribute_details = get_dependent_attribute_details(doc.dependent_attribute_mapping)
			packing_uom = attribute_details["attr_list"].get(doc.pack_in_stage, {}).get("uom") or uom
		return {
			"item": doc.item,
			"uom": uom,
			"pack_in_stage": doc.pack_in_stage,
			"pack_out_stage": doc.pack_out_stage,
			"packing_uom": packing_uom,
			"dependent_attr_mapping": doc.dependent_attribute_mapping,
			"tech_pack_version": doc.tech_pack_version,
			"pattern_version": doc.pattern_version,
			"packing_combo": doc.packing_combo,
		}
	return {"uom": uom}


def get_uom_conversion_factor(uom_conversion_details, from_uom, to_uom):
	if not to_uom:
		to_uom = from_uom
	if from_uom == to_uom:
		return 1

	to_uom_factor = None
	from_uom_factor = None
	for item in uom_conversion_details:
		if item.uom == from_uom:
			from_uom_factor = item.conversion_factor
		if item.uom == to_uom:
			to_uom_factor = item.conversion_factor

	if not from_uom_factor or not to_uom_factor:
		return 1
	return from_uom_factor / to_uom_factor


@frappe.whitelist()
def get_dict_object(data):
	if isinstance(data, str):
		data = json.loads(data)
	return data


@frappe.whitelist()
def combine_child_tables(table1, table2):
	table = table1 + table2
	return [row.as_dict() for row in table]


@frappe.whitelist()
def get_attributes(data):
	grp_variant_doc = frappe.get_cached_doc("Item Variant", data[0].item_variant)
	grp_item = grp_variant_doc.item
	dept_attr = frappe.get_value("Item", grp_item, "dependent_attribute")
	attribute_list = []
	for attrs in grp_variant_doc.attributes:
		if attrs.attribute != dept_attr:
			attribute_list.append(attrs.attribute)
	attribute_list += ["Ratio", "MRP"]

	attr_list = []
	for item in data:
		item = item.as_dict()
		doc = frappe.get_cached_doc("Item Variant", item["item_variant"])
		temp_attr = {}
		for attr in doc.attributes:
			if attr.attribute != dept_attr:
				temp_attr[attr.attribute] = attr.attribute_value
		temp_attr["Ratio"] = item["ratio"]
		temp_attr["MRP"] = item["mrp"]
		attr_list.append(temp_attr)
	return attribute_list, attr_list


@frappe.whitelist()
def get_packing_attributes(ipd):
	ipd_doc = frappe.get_doc("Item Production Detail", ipd)
	major_colours = []
	sizes = ""
	ratios = []
	combo = None
	colour_dict_list = []
	if ipd_doc.auto_calculate:
		combo = ipd_doc.packing_attribute_no

	for item in ipd_doc.packing_attribute_details:
		major_colours.append(item.attribute_value)
		colour_dict_list.append({
			"colour": item.attribute_value,
			"major_colour": item.attribute_value,
		})
		if not combo:
			ratios.append(ipd_doc.packing_combo / item.quantity)

	if ipd_doc.is_set_item:
		set_mapping = None
		for item in ipd_doc.item_attributes:
			if item.attribute == ipd_doc.set_item_attribute:
				set_mapping = item.mapping
				break
		set_map_doc = frappe.get_doc("Item Item Attribute Mapping", set_mapping)
		colour_combo_dict_list = []
		ratio_combo = []
		index = -1
		for colour in major_colours:
			index += 1
			for part in set_map_doc.values:
				colour_combo_dict_list.append({
					"colour": f"{colour}-{part.attribute_value}",
					"major_colour": colour,
				})
				if not combo:
					ratio_combo.append(ratios[index])
		colour_dict_list = colour_combo_dict_list
		ratios = ratio_combo

	mapping = None
	for item in ipd_doc.item_attributes:
		if item.attribute == ipd_doc.primary_item_attribute:
			mapping = item.mapping
			break

	if mapping:
		map_doc = frappe.get_doc("Item Item Attribute Mapping", mapping)
		for item in map_doc.values:
			sizes += item.attribute_value + ","

	return {
		"colour_combo": colour_dict_list,
		"sizes": sizes,
		"ratios": ratios,
		"combo": combo,
		"major_colours": major_colours,
	}


@frappe.whitelist()
def update_order_details(doc_name):
	doc = frappe.get_doc("Lot", doc_name)
	doc.calculate_order()
	doc.save()


@frappe.whitelist()
def get_mapping_details(ipd):
	ipd_doc = frappe.get_cached_doc("Item Production Detail", ipd)
	bom_attribute_list = []
	for bom in ipd_doc.item_bom:
		if bom.attribute_mapping is not None:
			doc = frappe.get_cached_doc("Item BOM Attribute Mapping", bom.attribute_mapping)
			bom_attribute_list.append({
				"bom_item": bom.item,
				"bom_attr_mapping_link": bom.attribute_mapping,
				"bom_attr_mapping_based_on": bom.based_on_attribute_mapping,
				"bom_attr_mapping_list": doc.values,
				"doctype": "Item BOM Attribute Mapping",
				"qty": bom.qty_of_bom_item,
			})

	map_dict = {}
	for mapping in bom_attribute_list:
		bom_qty = mapping.get("qty")
		bom_item = mapping.get("bom_item")
		mapping_values = mapping.get("bom_attr_mapping_list")
		data = []
		for d in mapping_values:
			x = d.index
			if len(data) <= d.index:
				while x >= 0:
					x -= 1
					data.append({"item": [], "bom": [], "quantity": 0})
			if d.type == "item":
				data[d.index]["item"].append(d.attribute_value)
			elif d.type == "bom":
				data[d.index]["bom"].append(d.attribute_value)
			qty = d.quantity
			if d.quantity == 0:
				qty = bom_qty
			data[d.index]["quantity"] = qty

		items = "\n"
		for d in data:
			if d.get("item"):
				item_str = ", ".join(d["item"])
				bom_str = ", ".join(d["bom"])
				items += f"{item_str} -> {bom_str} / {d['quantity']}<br>"
		if bom_item not in map_dict:
			map_dict[bom_item] = items
		else:
			map_dict[bom_item] += items
	return map_dict


@frappe.whitelist()
def get_ipd_print_accessory_combination(ipd):
	ipd_doc = frappe.get_cached_doc("Item Production Detail", ipd)
	stiching_accessory_json = update_if_string_instance(ipd_doc.stiching_accessory_json)
	items = {}
	if ipd_doc.is_set_item:
		for row in stiching_accessory_json.get("items") or []:
			items.setdefault(row[ipd_doc.set_item_attribute], {})
			colour_key = row["major_colour"]
			if row.get("major_attr_value"):
				colour_key += f"({row['major_attr_value']})"

			items[row[ipd_doc.set_item_attribute]].setdefault(colour_key, {})
			items[row[ipd_doc.set_item_attribute]][colour_key].setdefault(row["accessory"], {})
			items[row[ipd_doc.set_item_attribute]][colour_key][row["accessory"]] = {
				"colour": row["accessory_colour"],
				"cloth_type": row["cloth_type"],
			}
	else:
		for row in stiching_accessory_json.get("items") or []:
			items.setdefault(row["major_colour"], {})
			items[row["major_colour"]].setdefault(row["accessory"], {})
			items[row["major_colour"]][row["accessory"]] = {
				"colour": row["accessory_colour"],
				"cloth_type": row["cloth_type"],
			}
	return items


def get_ironing_mistake_pf_items(lot):
	lot_doc = frappe.get_doc("Lot", lot)
	return fetch_order_item_details(lot_doc.lot_order_details, lot_doc.production_detail)


@frappe.whitelist()
def get_ocr_details(lot):
	required = ["Work Order", "Cutting Plan", "Goods Received Note", "Finishing Plan"]
	if not all(frappe.db.exists("DocType", doctype) for doctype in required):
		return {}

	lot_dict = {}
	wo_list = frappe.get_all(
		"Work Order",
		filters={"lot": lot, "docstatus": 1},
		pluck="name",
		order_by="creation",
	)

	ipd, item = frappe.get_value("Lot", lot, ["production_detail", "item"])
	sewing, primary, pcs_per_box = frappe.get_value(
		"Item Production Detail",
		ipd,
		["stiching_process", "primary_item_attribute", "packing_combo"],
	)
	lot_dict["sizes"] = []
	lot_dict["processes"] = {}
	lot_dict["dispatch_detail"] = {}
	lot_dict["total_dispatch"] = 0
	lot_dict["finishing_plan_list"] = []
	includes_packing_process = None
	for wo in wo_list:
		wo_doc = frappe.get_doc("Work Order", wo)
		if wo_doc.includes_packing:
			includes_packing_process = wo_doc.process_name
		cp_list = frappe.get_list("Cutting Plan", filters={"work_order": wo}, pluck="name")
		lot_dict["processes"].setdefault(wo_doc.process_name, {
			"wo_list": [],
			"cp_list": [],
			"data": {},
			"total_sent": 0,
			"total_received": 0,
		})
		lot_dict["processes"][wo_doc.process_name]["cp_list"] += cp_list
		lot_dict["processes"][wo_doc.process_name]["wo_list"].append(wo)
		for row in wo_doc.work_order_calculated_items:
			attr_details = get_variant_attr_details(row.item_variant)
			size = attr_details[primary]
			if size not in lot_dict["sizes"]:
				lot_dict["sizes"].append(size)
			lot_dict["processes"][wo_doc.process_name]["data"].setdefault(
				size,
				{"sent": 0, "received": 0},
			)
			lot_dict["processes"][wo_doc.process_name]["data"][size]["sent"] += (
				row.delivered_quantity
			)
			lot_dict["processes"][wo_doc.process_name]["total_sent"] += row.delivered_quantity
			if not wo_doc.includes_packing:
				lot_dict["processes"][wo_doc.process_name]["data"][size]["received"] += (
					row.received_qty
				)
				lot_dict["processes"][wo_doc.process_name]["total_received"] += row.received_qty

	if includes_packing_process:
		grn_list = frappe.get_all(
			"Goods Received Note",
			filters={
				"against": "Work Order",
				"docstatus": 1,
				"includes_packing": 1,
				"process_name": includes_packing_process,
				"is_return": 0,
				"lot": lot,
			},
			pluck="name",
		)

		grn_item_dict = {}
		for grn in grn_list:
			grn_doc = frappe.get_doc("Goods Received Note", grn)
			for row in grn_doc.items:
				grn_item_dict.setdefault(row.item_variant, 0)
				grn_item_dict[row.item_variant] += row.quantity

		for variant in grn_item_dict:
			attr_details = get_variant_attr_details(variant)
			size = attr_details[primary]
			lot_dict["processes"][includes_packing_process]["total_received"] += (
				grn_item_dict[variant] * pcs_per_box
			)
			lot_dict["processes"][includes_packing_process]["data"][size]["received"] += (
				grn_item_dict[variant] * pcs_per_box
			)

	finishing_plan_list = frappe.get_all("Finishing Plan", filters={"lot": lot}, pluck="name")
	for finishing_plan in finishing_plan_list:
		lot_dict["finishing_plan_list"].append(finishing_plan)
		fp_doc = frappe.get_doc("Finishing Plan", finishing_plan)
		for row in fp_doc.finishing_plan_grn_details:
			attr_details = get_variant_attr_details(row.item_variant)
			size = attr_details[primary]
			lot_dict["dispatch_detail"].setdefault(size, 0)
			lot_dict["dispatch_detail"][size] += row.dispatched * fp_doc.pieces_per_box
			lot_dict["total_dispatch"] += row.dispatched * fp_doc.pieces_per_box

	return lot_dict


@frappe.whitelist()
def get_alternative_details(lot):
	lot_list = frappe.get_all("Lot", filters={"transferred_lot": lot}, pluck="name")
	lot_dict = {}
	for lot_name in lot_list:
		lot_doc = frappe.get_doc("Lot", lot_name)
		details = fetch_order_item_details(lot_doc.lot_order_details, lot_doc.production_detail)
		lot_dict[lot_name] = {
			"item": lot_doc.item,
			"ipd": lot_doc.production_detail,
			"details": details,
		}
	return lot_dict


@frappe.whitelist()
def check_enabled_po():
	if frappe.db.exists("DocType", "MRP Settings"):
		try:
			return frappe.db.get_single_value("MRP Settings", "enable_ppo") or 0
		except Exception:
			return 1
	return 1


@frappe.whitelist()
def get_ipd_primary_values(production_detail):
	doc = frappe.get_cached_doc("Item Production Detail", production_detail)
	primary_attr_values = []
	mapping = None
	for row in doc.item_attributes:
		if row.attribute == doc.primary_item_attribute:
			mapping = row.mapping
			break
	if mapping:
		map_doc = frappe.get_cached_doc("Item Item Attribute Mapping", mapping)
		for val in map_doc.values:
			primary_attr_values.append(val.attribute_value)
	return primary_attr_values


@frappe.whitelist()
def calculate_bom(lot_name):
	lot = frappe.get_doc("Lot", lot_name)
	if not lot.production_detail:
		frappe.throw("Please select Item Production Detail before calculating BOM.")

	from yrp.yrp.doctype.item_production_detail.item_production_detail import calculate_lot_bom

	variant_demands = _get_lot_variant_demands(lot)
	bom = calculate_lot_bom(lot.production_detail, variant_demands)
	major_rows = bom["major_deliverables"]
	accessory_rows = bom["accessories"]
	bom_summary_rows = [
		_to_lot_bom_row(row, is_major=1)
		for row in major_rows
	] + [
		_to_lot_bom_row(row, is_major=0)
		for row in accessory_rows
	]

	lot.set("bom_summary", bom_summary_rows)
	lot.set("bom_additional_items", [])
	lot.bom_summary_json = json.dumps(
		{
			"major_deliverables": major_rows,
			"accessories": accessory_rows,
		},
		default=str,
	)
	lot.last_calculated_time = now_datetime()
	lot.total_quantity = int(sum(row["qty"] for row in variant_demands))
	lot.save(ignore_permissions=True)
	return {
		"rows": len(bom_summary_rows),
		"major_rows": len(major_rows),
		"accessory_rows": len(accessory_rows),
		"total_qty": lot.total_quantity,
	}


def _get_lot_variant_demands(lot):
	rows = []
	for row in lot.get("lot_order_details") or []:
		if row.item_variant and float(row.quantity or 0) > 0:
			rows.append({"item_variant": row.item_variant, "qty": float(row.quantity or 0)})

	if not rows:
		for row in lot.get("items") or []:
			if row.item_variant and float(row.qty or 0) > 0:
				rows.append({"item_variant": row.item_variant, "qty": float(row.qty or 0)})

	if not rows:
		frappe.throw("Please add Item Variant and Qty before calculating BOM.")
	return rows


def _to_lot_bom_row(row, is_major=0):
	return {
		"item_name": row.get("item_variant"),
		"process_name": row.get("process_name"),
		"required_qty": row.get("required_qty") or row.get("qty") or 0,
		"uom": row.get("uom"),
		"is_major": is_major,
	}


@frappe.whitelist()
def get_lot_order_payload(lot_name=None, production_detail=None, item=None):
	lot = None
	if lot_name and frappe.db.exists("Lot", lot_name):
		lot = frappe.get_doc("Lot", lot_name)
		production_detail = lot.production_detail
		item = lot.item

	if lot:
		payload = fetch_item_details(lot.get("items") or [], production_detail)
		if payload:
			return payload

	if not production_detail or not frappe.db.exists("Item Production Detail", production_detail):
		return []

	return get_item_details(
		item_name=item or frappe.db.get_value("Item Production Detail", production_detail, "item"),
		uom=lot.uom if lot else None,
		production_detail=production_detail,
		dependent_attr_mapping=frappe.db.get_value(
			"Item Production Detail",
			production_detail,
			"dependent_attribute_mapping",
		),
		ppo=lot.production_order if lot else None,
	)


@frappe.whitelist()
def save_lot_order_payload(lot_name, payload):
	if isinstance(payload, str):
		payload = json.loads(payload)
	lot = frappe.get_doc("Lot", lot_name)

	lot.set("items", save_item_details(payload))
	if lot.production_detail:
		lot.calculate_order()
	lot.lot_order_details_json = json.dumps(payload, default=str)
	lot.save(ignore_permissions=True)
	frappe.db.commit()
	return {
		"items": len(lot.get("items") or []),
		"lot_order_details": len(lot.get("lot_order_details") or []),
	}


def _variant_attrs(variant_name):
	if not variant_name or not frappe.db.exists("Item Variant", variant_name):
		return {}
	rows = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": variant_name, "parenttype": "Item Variant"},
		fields=["attribute", "attribute_value"],
	)
	return {row.attribute: row.attribute_value for row in rows}


def _resolve_variant(item, attrs):
	if not item or not attrs:
		return None
	candidates = frappe.get_all("Item Variant", filters={"item": item}, pluck="name")
	for candidate in candidates:
		got = _variant_attrs(candidate)
		if all(got.get(k) == v for k, v in attrs.items()):
			return candidate
	return None
