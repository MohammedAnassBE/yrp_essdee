import json
from itertools import cycle, islice

import frappe

from yrp.yrp.doctype.item.item import get_or_create_variant


ATTRIBUTES = {
	"Size": ["S", "M", "L", "XL"],
	"Colour": ["Peach", "Pista", "Lavender", "Navy", "Denim"],
	"Part": ["Top", "Bottom"],
	"Panel": ["Top Front", "Top Back", "Bottom Front", "Bottom Back", "Sleeve"],
	"Stage": ["Cut", "Piece", "Pack"],
	"Dia": ["60 Dia"],
	"Name": ["Boho Style", "Living My Best Life", "Hamic Logo", "MMA Print", "Essdee Core"],
}

PRODUCT_NAMES = [
	"Mens Sports Vest - 11222",
	"Mens Sports Vest - 11223",
	"Mens Sports Vest - 11224",
	"Mens Sports Vest - 11225",
	"Hamic - Lovely Bermuda Set RNS",
	"Hamic - Rocky Collar T-Shirt RNS",
	"Designer Mini Trunks I.E",
	"BRAVO BRIEFS ( O.E)",
	"STARKIDS T.Shirt (R.N.S)",
	"Baby Shark Shorts Set Half Sleeve(Cord) T56205",
	"AISHWARYA PLAIN",
	"EE - 46207 Hot Shorts Set Half Sleeve",
	"UL-11402 Tank Top (MMA Collection)",
	"Designer Long Trunks I.E",
	"Rocky Half Sleeve Polo",
]

ACCESSORY_SPECS = [
	{"name": "Single Jersey 30's RL Dyed Fabric 28gg", "uom": "Kg", "attrs": ["Colour"]},
	{"name": "Cotton AOP Discharge Print Fabric New", "uom": "Kg", "attrs": ["Colour"]},
	{"name": "30's RL 97%Cotton,3%Elast Dyed Lycra Rib", "uom": "Kg", "attrs": ["Colour"]},
	{"name": "Dyed Fabric 36's RL", "uom": "Kg", "attrs": ["Colour"]},
	{"name": "Fleece Fabric 240 GSM", "uom": "Kg", "attrs": ["Colour"]},
	{"name": "Size Label 100% Cotton", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Compo Label 100% Cotton", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Wash Care Label", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Brand Woven Label", "uom": "Nos", "attrs": ["Colour"]},
	{"name": "Hang Tag", "uom": "Nos", "attrs": ["Colour"]},
	{"name": "Price Tag", "uom": "Nos", "attrs": ["Colour"]},
	{"name": "Hamic - Lovely Bermuda Set RNS TwillTape - 12mm", "uom": "Meter", "attrs": ["Colour"]},
	{"name": "Inner Elastic", "uom": "Meter", "attrs": ["Size"]},
	{"name": "Hamic - Lovely Bermuda Set RNS DTF Sticker - Small", "uom": "Nos", "attrs": ["Name"]},
	{"name": "Hamic - Lovely Bermuda Set RNS Simmer Sticker - Big", "uom": "Nos", "attrs": ["Name"]},
	{"name": "Fusing Sticker-EssdeeCore (45-80)", "uom": "Nos", "attrs": ["Colour"]},
	{"name": "Inner Card Big", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Plain Poly Bag BOPP (37 Micron)", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Corrugated Bottom Box-265mmx215mmx75mm", "uom": "Nos", "attrs": ["Size"]},
	{"name": "Hamic - Lovely Bermuda Set RNS Top Box", "uom": "Nos", "attrs": ["Size"]},
]

SUPPLIERS = [
	{
		"supplier_name": "Essdee Main Unit",
		"is_company_location": 1,
		"address": {
			"address_line1": "12 Textile Park Road",
			"address_line2": "Main Production Block",
			"city": "Tiruppur",
			"state": "Tamil Nadu",
			"pincode": "641604",
			"phone": "0421-2451001",
			"email_id": "stores@essdee.example",
		},
	},
	{
		"supplier_name": "Cutting Vendor",
		"is_company_location": 0,
		"address": {
			"address_line1": "24 Pattern Layout Street",
			"address_line2": "Cutting Unit",
			"city": "Tiruppur",
			"state": "Tamil Nadu",
			"pincode": "641602",
			"phone": "0421-2451002",
			"email_id": "cutting.vendor@example.com",
		},
	},
	{
		"supplier_name": "Fusing Vendor",
		"is_company_location": 0,
		"address": {
			"address_line1": "8 Industrial Estate Road",
			"address_line2": "Fusing Section",
			"city": "Avinashi",
			"state": "Tamil Nadu",
			"pincode": "641654",
			"phone": "04296-245103",
			"email_id": "fusing.vendor@example.com",
		},
	},
	{
		"supplier_name": "Stitching Vendor",
		"is_company_location": 0,
		"address": {
			"address_line1": "41 Needle Works Avenue",
			"address_line2": "Line A",
			"city": "Tiruppur",
			"state": "Tamil Nadu",
			"pincode": "641603",
			"phone": "0421-2451004",
			"email_id": "stitching.vendor@example.com",
		},
	},
	{
		"supplier_name": "Packing Vendor",
		"is_company_location": 0,
		"address": {
			"address_line1": "17 Dispatch Nagar",
			"address_line2": "Packing Bay",
			"city": "Tiruppur",
			"state": "Tamil Nadu",
			"pincode": "641605",
			"phone": "0421-2451005",
			"email_id": "packing.vendor@example.com",
		},
	},
]

LEGACY_PRODUCT_NAMES = [
	"YRP Demo Mens Sports Vest - 11222",
	"YRP Demo Mens Sports Vest - 11223",
	"YRP Demo Mens Sports Vest - 11224",
	"YRP Demo Mens Sports Vest - 11225",
	"YRP Demo Hamic Lovely Bermuda Set RNS",
	"YRP Demo Rocky Collar T-Shirt RNS",
	"YRP Demo Designer Mini Trunks IE",
	"YRP Demo Bravo Briefs OE",
	"YRP Demo Starkids T-Shirt RNS",
	"YRP Demo Baby Shark Shorts Set",
	"YRP Demo Aishwarya Plain",
	"YRP Demo Hot Shorts Half Sleeve",
	"YRP Demo Tank Top MMA",
	"YRP Demo Long Trunks IE",
	"YRP Demo Polo Half Sleeve",
]

LEGACY_ACCESSORY_NAMES = [
	"YRP Demo Single Jersey Fabric 165 GSM",
	"YRP Demo Cotton AOP Fabric 180 GSM",
	"YRP Demo Lycra Rib Fabric 260 GSM",
	"YRP Demo Dyed Interlock Fabric 210 GSM",
	"YRP Demo Fleece Fabric 240 GSM",
	"YRP Demo Size Label 100 Cotton",
	"YRP Demo Compo Label 100 Cotton",
	"YRP Demo Wash Care Label",
	"YRP Demo Brand Woven Label",
	"YRP Demo Hang Tag",
	"YRP Demo Price Tag",
	"YRP Demo Twill Tape 12mm",
	"YRP Demo Inner Elastic",
	"YRP Demo DTF Sticker Small",
	"YRP Demo Simmer Sticker Big",
	"YRP Demo Fusing Sticker Core",
	"YRP Demo Inner Card Big",
	"YRP Demo Plain Poly Bag BOPP",
	"YRP Demo Corrugated Bottom Box",
	"YRP Demo Top Box",
]

ACCESSORY_VALUE_MAP = {
	"Size Label 100% Cotton": {"Size": ["45 cm", "50 cm", "55 cm", "60 cm"]},
	"Compo Label 100% Cotton": {"Size": ["45 cm", "50 cm", "55 cm", "60 cm"]},
	"Wash Care Label": {"Size": ["45 cm", "50 cm", "55 cm", "60 cm"]},
	"Inner Elastic": {"Size": ["30 mm"]},
	"Inner Card Big": {"Size": ["7 x 9", "7.5 x 9.5", "8 x 10", "8.5 x 11"]},
	"Plain Poly Bag BOPP (37 Micron)": {
		"Size": ["8 x 10 + 2", "8.5 x 11 + 2", "9\" X 11\" + 2", "10 x 12 + 2"],
	},
	"Corrugated Bottom Box-265mmx215mmx75mm": {
		"Size": ["13\" x 3\"", "13.25\" x 3\"", "13.75\" x 3.25\"", "14.25\" x 3.25\""],
	},
	"Hamic - Lovely Bermuda Set RNS Top Box": {
		"Size": ["13\" x 3.25\"", "13.25\" x 3.25\"", "13.75\" x 3.75\"", "14.25\" x 3.50\""],
	},
	"Brand Woven Label": {"Colour": ["Dark Peach 1", "Pastel Pista", "Lavender 1", "Navy 4", "Steel Blue"]},
	"Hang Tag": {"Colour": ["Dark Peach 1", "Pastel Pista", "Lavender 1", "Navy 4", "Steel Blue"]},
	"Price Tag": {"Colour": ["Dark Peach 1", "Pastel Pista", "Lavender 1", "Navy 4", "Steel Blue"]},
	"Hamic - Lovely Bermuda Set RNS TwillTape - 12mm": {
		"Colour": ["Peach", "Garden Green", "Lavender 1", "Navy", "Steel Blue"],
	},
	"Hamic - Lovely Bermuda Set RNS DTF Sticker - Small": {
		"Name": ["Boho Style", "Living My Best Life", "Hamic Logo", "MMA Print"],
	},
	"Hamic - Lovely Bermuda Set RNS Simmer Sticker - Big": {
		"Name": ["Living My Best Life", "Boho Style", "Essdee Core", "Hamic Logo"],
	},
	"Fusing Sticker-EssdeeCore (45-80)": {
		"Colour": ["Dark Peach 1", "Pastel Pista", "Lavender 1", "Navy 4", "Steel Blue"],
	},
}

BOM_MAPPING_QUANTITY_BY_ITEM_VALUE = {
	"Inner Elastic": {
		"Size": {
			"S": 0.35,
			"M": 0.39,
			"L": 0.43,
			"XL": 0.47,
		}
	}
}

PROCESS_SEQUENCE = [
	{"process_name": "Cutting", "in_stage": None, "out_stage": "Cut"},
	{"process_name": "Yolk Fusing", "in_stage": "Cut", "out_stage": "Cut"},
	{"process_name": "Stitching", "in_stage": "Cut", "out_stage": "Piece"},
	{"process_name": "Ironing", "in_stage": "Piece", "out_stage": "Piece"},
	{"process_name": "Packing", "in_stage": "Piece", "out_stage": "Pack"},
]

PANEL_QTY = {
	"Top Front": 1,
	"Top Back": 1,
	"Bottom Front": 1,
	"Bottom Back": 1,
	"Sleeve": 2,
}

PART_PANELS = {
	"Top": ["Top Front", "Top Back", "Sleeve"],
	"Bottom": ["Bottom Front", "Bottom Back"],
}

COLOUR_SET_COMBINATIONS = [
	{"major": "Denim", "Top": "Denim", "Bottom": "Navy"},
	{"major": "Peach", "Top": "Peach", "Bottom": "Denim"},
	{"major": "Pista", "Top": "Pista", "Bottom": "Peach"},
	{"major": "Lavender", "Top": "Lavender", "Bottom": "Pista"},
	{"major": "Navy", "Top": "Navy", "Bottom": "Peach"},
]


def create_demo_data():
	"""Create a production_api-style demo set on the current site."""
	_assert_custom_fields_installed()
	reset_demo_data()
	_seed_masters()

	suppliers = _seed_suppliers()
	products = _seed_product_items()
	accessories = _seed_accessory_items()

	ipds = []
	lots = []
	bom_results = []
	for index in range(5):
		spec = _ipd_spec(index, products[index], accessories)
		ipd = _create_ipd(spec)
		_set_product_uom_conversion(spec["product"], spec["packing_combo"])
		_create_process_matrices(ipd, spec)
		production_order = _create_production_order(index, spec)
		lot = _create_lot(index, ipd, spec, production_order.name)
		bom_result = _calculate_lot_bom(lot.name)
		bom_result["lot"] = lot.name
		bom_result["production_order"] = production_order.name
		bom_result["order_qty"] = spec["order_qty"]
		bom_result["pack_item_qty"] = frappe.db.get_value("Lot", lot.name, "total_quantity")
		bom_results.append(bom_result)
		ipds.append(ipd.name)
		lots.append(lot.name)

	frappe.db.commit()
	return {
		"products": len(products),
		"accessories": len(accessories),
		"suppliers": len(suppliers),
		"ipds": ipds,
		"lots": lots,
		"production_orders": [row["production_order"] for row in bom_results],
		"lot_bom_results": bom_results,
	}


def verify_demo_data():
	"""Verify the seeded demo data and each Lot BOM calculation."""
	product_items = _items_by_name1(PRODUCT_NAMES)
	accessory_items = _items_by_name1(_accessory_names())
	supplier_names = [s["supplier_name"] for s in SUPPLIERS]
	suppliers = frappe.get_all(
		"Supplier",
		filters={"supplier_name": ["in", supplier_names]},
		fields=["name", "supplier_name", "is_company_location"],
		limit_page_length=100,
	)
	ipd_names = frappe.get_all(
		"Item Production Detail",
		filters={"item": ["in", list(product_items.values())]},
		pluck="name",
	)
	lot_names = frappe.get_all(
		"Lot",
		filters={"lot_name": ["in", _lot_names()]},
		pluck="name",
	)
	production_orders = frappe.get_all(
		"Production Order",
		filters={"comments": ["like", "Production Order for YD0526-%"]},
		pluck="name",
	)

	_assert(len(product_items) == 15, f"Expected 15 product items, found {len(product_items)}")
	_assert(len(accessory_items) == 20, f"Expected 20 accessory items, found {len(accessory_items)}")
	_assert(len(suppliers) == 5, f"Expected 5 suppliers, found {len(suppliers)}")
	_assert(len(production_orders) == 5, f"Expected 5 Production Orders, found {len(production_orders)}")
	_assert(len(ipd_names) == 5, f"Expected 5 IPDs, found {len(ipd_names)}")
	_assert(len(lot_names) == 5, f"Expected 5 Lots, found {len(lot_names)}")
	_assert_no_legacy_demo_tag()

	supplier_address_checks = _verify_supplier_addresses(suppliers)
	attribute_checks = _verify_attribute_values()
	product_attribute_checks = _verify_product_attribute_mappings(product_items)
	accessory_attribute_checks = _verify_accessory_attribute_mappings(accessory_items)

	ipd_checks = []
	for ipd_name in sorted(ipd_names):
		ipd = frappe.get_doc("Item Production Detail", ipd_name)
		matrices = frappe.get_all(
			"IPD Process Matrix",
			filters={"ipd": ipd.name},
			fields=["name", "process_name", "reference_item_variant"],
			order_by="process_name asc",
		)
		mapped_bom = [row for row in ipd.item_bom if row.based_on_attribute_mapping and row.attribute_mapping]
		_assert(len(ipd.ipd_processes) == 5, f"{ipd.name} does not have 5 IPD processes")
		_assert(len(matrices) >= 20, f"{ipd.name} does not have size-wise process matrices")
		_assert(len(ipd.item_bom) >= 6, f"{ipd.name} has too few BOM rows")
		_assert(
			len(mapped_bom) == len(ipd.item_bom),
			f"{ipd.name} should have attribute mappings for every Item BOM row",
		)
		_verify_bom_mapping_quantities(ipd)
		_verify_ipd_combination_data(ipd)
		_assert(ipd.packing_combo, f"{ipd.name} missing packing_combo")
		_assert(ipd.packing_attribute == "Colour", f"{ipd.name} missing packing_attribute")
		_assert(ipd.stiching_attribute == "Panel", f"{ipd.name} missing stiching_attribute")
		_assert(len(ipd.stiching_item_details) >= 5, f"{ipd.name} missing stiching_item_details")
		_assert(len(ipd.cloth_detail) >= 1, f"{ipd.name} missing cloth_detail")
		ipd_checks.append({
			"ipd": ipd.name,
			"item": ipd.item,
			"bom_rows": len(ipd.item_bom),
			"mapped_bom_rows": len(mapped_bom),
			"matrices": len(matrices),
		})

	lot_checks = []
	for lot_name in sorted(lot_names):
		result = _calculate_lot_bom(lot_name)
		lot = frappe.get_doc("Lot", lot_name)
		processes = sorted({row.process_name for row in lot.bom_summary if row.process_name})
		_assert(lot.production_order, f"{lot.name} is not linked to a Production Order")
		po_item = frappe.db.get_value(
			"Production Order Detail",
			{"parent": lot.production_order, "parenttype": "Production Order"},
			"item",
		)
		_assert(po_item == lot.item, f"{lot.name} Production Order item does not match Lot item")
		_assert(result["major_rows"] >= 5, f"{lot.name} has too few major BOM rows")
		_assert(result["accessory_rows"] >= 5, f"{lot.name} has too few accessory BOM rows")
		_assert(len(processes) >= 5, f"{lot.name} BOM does not cover 5 processes")
		lot_checks.append({
			"lot": lot.name,
			"production_order": lot.production_order,
			"item": lot.item,
			"order_qty": lot.total_order_quantity,
			"pack_qty": lot.total_quantity,
			"bom_rows": len(lot.bom_summary),
			"major_rows": result["major_rows"],
			"accessory_rows": result["accessory_rows"],
			"processes": processes,
		})

	frappe.db.commit()
	return {
		"products": len(product_items),
		"accessories": len(accessory_items),
		"suppliers": len(suppliers),
		"supplier_addresses": supplier_address_checks,
		"production_orders": len(production_orders),
		"attribute_checks": attribute_checks,
		"product_attribute_mappings": product_attribute_checks,
		"accessory_attribute_mappings": accessory_attribute_checks,
		"ipds": len(ipd_checks),
		"lots": len(lot_checks),
		"ipd_checks": ipd_checks,
		"lot_checks": lot_checks,
	}


def reset_demo_data():
	"""Remove only the YRP demo records owned by this seeder."""
	lot_names = _lot_names()
	for name in frappe.get_all("Lot", filters={"lot_name": ["in", lot_names]}, pluck="name"):
		_force_delete("Lot", name)

	for production_order in set(
		frappe.get_all(
			"Production Order",
			filters={"comments": ["like", "YRP Demo Production Order%"]},
			pluck="name",
		)
		+ frappe.get_all(
			"Production Order",
			filters={"comments": ["like", "Production Order for YD0526-%"]},
			pluck="name",
		)
	):
		_force_delete("Production Order", production_order)

	product_items = _items_by_name1(PRODUCT_NAMES + LEGACY_PRODUCT_NAMES)
	accessory_items = _items_by_name1(_accessory_names() + LEGACY_ACCESSORY_NAMES)
	for item in frappe.get_all(
		"Item",
		filters={"name": ["like", "YRP Demo %"]},
		fields=["name", "name1"],
		limit_page_length=1000,
	):
		if item.name1 in LEGACY_PRODUCT_NAMES:
			product_items[item.name1] = item.name
		else:
			accessory_items[item.name1] = item.name
	all_item_ids = list(product_items.values()) + list(accessory_items.values())

	if all_item_ids:
		ipds = frappe.get_all(
			"Item Production Detail",
			filters={"item": ["in", all_item_ids]},
			pluck="name",
		)
		for ipd_name in ipds:
			for matrix in frappe.get_all("IPD Process Matrix", filters={"ipd": ipd_name}, pluck="name"):
				_force_delete("IPD Process Matrix", matrix)
			_force_delete("Item Production Detail", ipd_name)

		for mapping in set(
			frappe.get_all("Item BOM Attribute Mapping", filters={"item": ["in", all_item_ids]}, pluck="name")
			+ frappe.get_all("Item BOM Attribute Mapping", filters={"bom_item": ["in", all_item_ids]}, pluck="name")
		):
			_force_delete("Item BOM Attribute Mapping", mapping)

		for item in all_item_ids:
			for variant in frappe.get_all("Item Variant", filters={"item": item}, pluck="name"):
				_force_delete("Item Variant", variant)

		for mapping in frappe.get_all(
			"Item Dependent Attribute Mapping",
			filters={"item": ["in", list(product_items.values())]},
			pluck="name",
		):
			_force_delete("Item Dependent Attribute Mapping", mapping)

		item_mapping_names = [
			row.mapping
			for row in frappe.get_all(
				"Item Item Attribute",
				filters={"parent": ["in", all_item_ids]},
				fields=["mapping"],
			)
			if row.mapping
		]
		for item in all_item_ids:
			_force_delete("Item", item)
		for mapping in set(item_mapping_names):
			_force_delete("Item Item Attribute Mapping", mapping)

	for warehouse in _warehouse_names():
		_force_delete("Warehouse", warehouse)

	for supplier in frappe.get_all(
		"Supplier",
		filters={
			"supplier_name": [
				"in",
				[s["supplier_name"] for s in SUPPLIERS]
				+ [
					"YRP Demo Essdee Main Unit",
					"YRP Demo Cutting Vendor",
					"YRP Demo Fusing Vendor",
					"YRP Demo Stitching Vendor",
					"YRP Demo Packing Vendor",
				],
			]
		},
		pluck="name",
	):
		_force_delete("Supplier", supplier)

	frappe.db.commit()
	return {"status": "reset"}


def _verify_attribute_values():
	checks = []
	for attr, values in ATTRIBUTES.items():
		_assert(frappe.db.exists("Item Attribute", attr), f"Missing Item Attribute {attr}")
		actual_values = set(
			frappe.get_all(
				"Item Attribute Value",
				filters={"attribute_name": attr},
				pluck="attribute_value",
			)
		)
		missing = set(values) - actual_values
		_assert(not missing, f"Missing Item Attribute Values for {attr}: {sorted(missing)}")
		checks.append({"attribute": attr, "values": len(values)})
	return checks


def _assert_no_legacy_demo_tag():
	tagged_items = frappe.get_all(
		"Item",
		filters={"name": ["like", "YRP Demo %"]},
		pluck="name",
		limit_page_length=1000,
	)
	tagged_suppliers = frappe.get_all(
		"Supplier",
		filters={"supplier_name": ["like", "YRP Demo %"]},
		pluck="name",
		limit_page_length=1000,
	)
	tagged_warehouses = frappe.get_all(
		"Warehouse",
		filters={"name": ["like", "YRP Demo %"]},
		pluck="name",
		limit_page_length=1000,
	)
	_assert(
		not (tagged_items or tagged_suppliers or tagged_warehouses),
		f"Legacy YRP Demo records still exist: {tagged_items + tagged_suppliers + tagged_warehouses}",
	)


def _verify_supplier_addresses(suppliers):
	checks = []
	for supplier in suppliers:
		addresses = frappe.get_all(
			"Address",
			filters=[
				["Dynamic Link", "link_doctype", "=", "Supplier"],
				["Dynamic Link", "link_name", "=", supplier.name],
				["Dynamic Link", "parenttype", "=", "Address"],
				["Address", "disabled", "=", 0],
				["Address", "is_primary_address", "=", 1],
			],
			fields=["name", "city", "state", "pincode"],
			limit=1,
		)
		_assert(addresses, f"{supplier.supplier_name} does not have a primary supplier address")
		checks.append({
			"supplier": supplier.supplier_name,
			"address": addresses[0].name,
			"city": addresses[0].city,
			"state": addresses[0].state,
			"pincode": addresses[0].pincode,
		})
	return checks


def _verify_product_attribute_mappings(product_items):
	checks = []
	for item_label, item_name in sorted(product_items.items()):
		item = frappe.get_doc("Item", item_name)
		item_attrs = {row.attribute: row.mapping for row in item.attributes}
		for attr in ["Stage", "Part", "Panel", "Colour", "Size"]:
			_assert(attr in item_attrs, f"{item_label} missing Item attribute {attr}")
			_assert(item_attrs[attr], f"{item_label} missing Item Item Attribute Mapping for {attr}")
			mapping = frappe.get_doc("Item Item Attribute Mapping", item_attrs[attr])
			mapped_values = {row.attribute_value for row in mapping.values}
			missing = set(ATTRIBUTES[attr]) - mapped_values
			_assert(not missing, f"{item_label} mapping for {attr} missing values: {sorted(missing)}")
		_assert(item.dependent_attribute == "Stage", f"{item_label} missing dependent attribute Stage")
		_assert(
			item.dependent_attribute_mapping
			and frappe.db.exists("Item Dependent Attribute Mapping", item.dependent_attribute_mapping),
			f"{item_label} missing Item Dependent Attribute Mapping",
		)
		idam = frappe.get_doc("Item Dependent Attribute Mapping", item.dependent_attribute_mapping)
		_assert(len(idam.details) == 3, f"{item_label} IDAM should have 3 Stage details")
		checks.append({
			"item": item_label,
			"attributes": len(item_attrs),
			"dependent_mapping": item.dependent_attribute_mapping,
		})
	return checks


def _verify_accessory_attribute_mappings(accessory_items):
	checks = []
	for item_label, item_name in sorted(accessory_items.items()):
		item = frappe.get_doc("Item", item_name)
		_assert(item.attributes, f"{item_label} should have at least one accessory attribute")
		for row in item.attributes:
			_assert(row.mapping, f"{item_label} missing mapping for accessory attribute {row.attribute}")
			mapping = frappe.get_doc("Item Item Attribute Mapping", row.mapping)
			_assert(mapping.values, f"{item_label} mapping for {row.attribute} has no values")
		checks.append({"item": item_label, "attributes": len(item.attributes)})
	return checks


def _verify_bom_mapping_quantities(ipd):
	for row in ipd.item_bom:
		_assert(row.attribute_mapping, f"{ipd.name} BOM row for {row.item} has no attribute mapping")
		values = frappe.get_all(
			"Item BOM Attribute Mapping Value",
			filters={"parent": row.attribute_mapping},
			fields=["quantity"],
			limit_page_length=1000,
		)
		_assert(values, f"{row.attribute_mapping} has no mapping values")
		_assert(
			all(float(value.quantity or 0) > 0 for value in values),
			f"{row.attribute_mapping} has zero quantity values",
		)
		if row.item == "Inner Elastic":
			_verify_inner_elastic_mapping(row.attribute_mapping)


def _verify_inner_elastic_mapping(attribute_mapping):
	rows = frappe.db.sql(
		"""
		select `index`, attribute, attribute_value, type, quantity
		from `tabItem BOM Attribute Mapping Value`
		where parent = %s
		order by `index`, type, idx
		""",
		(attribute_mapping,),
		as_dict=True,
	)
	grouped = {}
	for row in rows:
		group = grouped.setdefault(row.index, {"quantity": float(row.quantity or 0)})
		if row.type == "item" and row.attribute == "Size":
			group["item_size"] = row.attribute_value
		elif row.type == "bom" and row.attribute == "Size":
			group["bom_size"] = row.attribute_value

	expected = BOM_MAPPING_QUANTITY_BY_ITEM_VALUE["Inner Elastic"]["Size"]
	actual = {row["item_size"]: row for row in grouped.values() if row.get("item_size")}
	for size, quantity in expected.items():
		_assert(size in actual, f"Inner Elastic mapping missing product size {size}")
		_assert(actual[size].get("bom_size") == "30 mm", f"Inner Elastic {size} should map to 30 mm")
		_assert(abs(float(actual[size].get("quantity") or 0) - quantity) < 0.0001, f"Inner Elastic {size} quantity should be {quantity}")


def _verify_ipd_combination_data(ipd):
	_assert(len(ipd.packing_attribute_details) >= len(COLOUR_SET_COMBINATIONS), f"{ipd.name} should have multi-colour packing rows")
	_assert(ipd.is_set_item, f"{ipd.name} should be configured as a set item")
	_assert(ipd.set_item_attribute == "Part", f"{ipd.name} should use Part as set item attribute")
	_assert(ipd.major_attribute_value == "Top", f"{ipd.name} should use Top as major part")
	_assert(ipd.is_same_packing_attribute, f"{ipd.name} should keep stitching colours tied to packing")
	_assert(len(ipd.set_item_combination_details) >= len(COLOUR_SET_COMBINATIONS) * 2, f"{ipd.name} missing set item colour mappings")
	_assert(
		len(ipd.stiching_item_combination_details) >= len(COLOUR_SET_COMBINATIONS) * len(PANEL_QTY),
		f"{ipd.name} missing stitching panel-colour mappings",
	)
	set_colours = {
		(row.index, row.set_item_attribute_value): row.attribute_value
		for row in ipd.set_item_combination_details
	}
	for row in ipd.stiching_item_combination_details:
		part = _part_for_panel(row.set_item_attribute_value)
		expected_colour = set_colours.get((row.index, part))
		_assert(expected_colour, f"{ipd.name} stitching row {row.idx} has no {part} colour mapping")
		_assert(
			row.major_attribute_value == expected_colour and row.attribute_value == expected_colour,
			f"{ipd.name} stitching row {row.idx} should use {expected_colour}",
		)
	cutting_attrs = {row.attribute for row in ipd.cutting_attributes}
	cloth_attrs = {row.attribute for row in ipd.cloth_attributes}
	_assert({"Panel", "Colour"}.issubset(cutting_attrs), f"{ipd.name} missing cutting Panel/Colour selections")
	_assert({"Panel", "Colour"}.issubset(cloth_attrs), f"{ipd.name} missing cloth Panel/Colour selections")
	expected_json_rows = len(PANEL_QTY) * (len(COLOUR_SET_COMBINATIONS) - 1)
	_assert(_json_item_count(ipd.cutting_items_json) >= expected_json_rows, f"{ipd.name} cutting JSON is incomplete")
	_assert(_json_item_count(ipd.cutting_cloths_json) >= expected_json_rows, f"{ipd.name} cloth JSON is incomplete")


def _json_item_count(value):
	if not value:
		return 0
	data = json.loads(value) if isinstance(value, str) else value
	return len((data or {}).get("items") or [])


def _assert_custom_fields_installed():
	count = frappe.db.count("Custom Field", {"module": "YRP Essdee"})
	_assert(count >= 79, "YRP Essdee custom fields are not installed. Run migrate before seeding demo data.")


def _seed_masters():
	for uom, whole in {
		"Pieces": 1,
		"Nos": 1,
		"Kg": 0,
		"Meter": 0,
		"Box": 1,
	}.items():
		_ensure_uom(uom, whole)

	_ensure_item_group("All Item Groups", is_group=1)
	_ensure_item_group("Products", parent="All Item Groups", is_group=0)
	_ensure_item_group("Accessories", parent="All Item Groups", is_group=0)

	for attr, values in ATTRIBUTES.items():
		_ensure_attribute(attr)
		for value in values:
			_ensure_attribute_value(attr, value)
	for attr_values in ACCESSORY_VALUE_MAP.values():
		for attr, values in attr_values.items():
			_ensure_attribute(attr)
			for value in values:
				_ensure_attribute_value(attr, value)

	for process in PROCESS_SEQUENCE:
		_ensure_process(process["process_name"])


def _seed_suppliers():
	created = {}
	for spec in SUPPLIERS:
		existing = frappe.get_all(
			"Supplier",
			filters={"supplier_name": spec["supplier_name"]},
			pluck="name",
			limit=1,
		)
		if existing:
			doc = frappe.get_doc("Supplier", existing[0])
		else:
			doc = frappe.new_doc("Supplier")
		doc.supplier_name = spec["supplier_name"]
		doc.is_company_location = spec["is_company_location"]
		doc.disabled = 0
		doc.save(ignore_permissions=True)
		created[spec["supplier_name"]] = doc.name
		_ensure_supplier_address(doc.name, spec)

	for spec in SUPPLIERS:
		warehouse = f"{spec['supplier_name']} Warehouse"
		if not frappe.db.exists("Warehouse", warehouse):
			wdoc = frappe.new_doc("Warehouse")
			wdoc.name1 = warehouse
			wdoc.supplier = created[spec["supplier_name"]]
			wdoc.disabled = 0
			wdoc.insert(ignore_permissions=True)
	return created


def _ensure_supplier_address(supplier, spec):
	address_spec = spec.get("address") or {}
	if not address_spec:
		return None

	existing = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", supplier],
			["Dynamic Link", "parenttype", "=", "Address"],
			["Address", "address_type", "=", "Office"],
		],
		pluck="name",
		limit=1,
	)
	doc = frappe.get_doc("Address", existing[0]) if existing else frappe.new_doc("Address")
	doc.address_title = spec["supplier_name"]
	doc.address_type = "Office"
	doc.address_line1 = address_spec["address_line1"]
	doc.address_line2 = address_spec.get("address_line2")
	doc.city = address_spec["city"]
	doc.state = address_spec.get("state")
	doc.country = address_spec.get("country") or "India"
	doc.pincode = address_spec.get("pincode")
	doc.phone = address_spec.get("phone")
	doc.email_id = address_spec.get("email_id")
	doc.is_primary_address = 1
	doc.is_shipping_address = 1
	doc.disabled = 0
	if not existing:
		doc.append("links", {
			"link_doctype": "Supplier",
			"link_name": supplier,
		})
	doc.save(ignore_permissions=True)
	return doc.name


def _seed_product_items():
	products = []
	for name in PRODUCT_NAMES:
		item = _ensure_item(
			name=name,
			item_group="Products",
			default_uom="Pieces",
			attrs=["Stage", "Part", "Panel", "Colour", "Size"],
			attr_values={
				"Stage": ATTRIBUTES["Stage"],
				"Part": ATTRIBUTES["Part"],
				"Panel": ATTRIBUTES["Panel"],
				"Colour": ATTRIBUTES["Colour"],
				"Size": ATTRIBUTES["Size"],
			},
			is_stock_item=1,
			is_purchase_item=0,
			is_sales_item=1,
			primary_attribute="Size",
			dependent_attribute="Stage",
		)
		products.append(item)
	return products


def _seed_accessory_items():
	accessories = {}
	for spec in ACCESSORY_SPECS:
		attr_values = {
			attr: (ACCESSORY_VALUE_MAP.get(spec["name"], {}).get(attr) or ATTRIBUTES[attr])
			for attr in spec["attrs"]
		}
		item = _ensure_item(
			name=spec["name"],
			item_group="Accessories",
			default_uom=spec["uom"],
			attrs=spec["attrs"],
			attr_values=attr_values,
			is_stock_item=1,
			is_purchase_item=1,
			is_sales_item=0,
		)
		accessories[spec["name"]] = item
	return accessories


def _ensure_item(
	name,
	item_group,
	default_uom,
	attrs,
	attr_values,
	is_stock_item,
	is_purchase_item,
	is_sales_item,
	primary_attribute=None,
	dependent_attribute=None,
):
	existing = frappe.get_all("Item", filters={"name1": name}, pluck="name", limit=1)
	if existing:
		doc = frappe.get_doc("Item", existing[0])
	else:
		doc = frappe.new_doc("Item")
		doc.flags.name_set = True
		doc.name = name

	doc.name1 = name
	doc.item_group = item_group
	doc.default_unit_of_measure = default_uom
	doc.is_stock_item = is_stock_item
	doc.allow_negative_stock = 1 if is_stock_item else 0
	doc.is_purchase_item = is_purchase_item
	doc.is_sales_item = is_sales_item
	doc.primary_attribute = None
	doc.dependent_attribute = None
	doc.dependent_attribute_mapping = None
	doc.set("attributes", [])
	for attr in attrs:
		doc.append("attributes", {"attribute": attr})
	doc.save(ignore_permissions=True)

	_populate_item_attribute_mappings(doc.name, attrs, attr_values)

	if dependent_attribute:
		idam = _create_dependent_attribute_mapping(doc.name)
		doc = frappe.get_doc("Item", doc.name)
		doc.primary_attribute = primary_attribute
		doc.dependent_attribute = dependent_attribute
		doc.dependent_attribute_mapping = idam
		doc.save(ignore_permissions=True)
	elif primary_attribute:
		doc = frappe.get_doc("Item", doc.name)
		doc.primary_attribute = primary_attribute
		doc.save(ignore_permissions=True)

	return doc.name


def _populate_item_attribute_mappings(item_name, attrs, attr_values):
	item = frappe.get_doc("Item", item_name)
	for attr in attrs:
		row = next((r for r in item.attributes if r.attribute == attr), None)
		if not row:
			continue
		mapping = frappe.get_doc("Item Item Attribute Mapping", row.mapping)
		mapping.attribute_name = attr
		mapping.set("values", [])
		for value in attr_values.get(attr, []):
			mapping.append("values", {"attribute_value": value})
		mapping.save(ignore_permissions=True)
	item.save(ignore_permissions=True)


def _create_dependent_attribute_mapping(item_name):
	for mapping in frappe.get_all("Item Dependent Attribute Mapping", filters={"item": item_name}, pluck="name"):
		_force_delete("Item Dependent Attribute Mapping", mapping)

	doc = frappe.new_doc("Item Dependent Attribute Mapping")
	doc.item = item_name
	doc.dependent_attribute = "Stage"
	stage_attrs = {
		"Cut": ["Panel", "Colour", "Size"],
		"Piece": ["Part", "Colour", "Size"],
		"Pack": ["Size"],
	}
	for stage in ATTRIBUTES["Stage"]:
		doc.append("details", {
			"attribute_value": stage,
			"uom": "Box" if stage == "Pack" else "Pieces",
			"display_name": stage,
			"is_final": 1 if stage == "Pack" else 0,
		})
		for attr in stage_attrs[stage]:
			doc.append("mapping", {
				"dependent_attribute_value": stage,
				"depending_attribute": attr,
			})
	doc.insert(ignore_permissions=True)
	return doc.name


def _ipd_spec(index, product, accessories):
	colours = ATTRIBUTES["Colour"]
	fabrics = _accessory_names()[:5]
	packing_combo = 5 if index % 2 == 0 else 10
	pack_plan = _pack_plan(index)
	return {
		"product": product,
		"colour": colours[index % len(colours)],
		"colour_sets": _colour_set_combinations(index),
		"fabric": accessories[fabrics[index]],
		"fabric_weight": 0.16 + (index * 0.02),
		"packing_combo": packing_combo,
		"pack_plan": pack_plan,
		"order_qty": sum(pack_plan.values()) * packing_combo,
		"flat_accessories": _flat_bom_accessories(index),
	}


def _pack_plan(index):
	plans = [
		{"S": 2, "M": 3, "L": 4, "XL": 3},
		{"S": 1, "M": 2, "L": 3, "XL": 2},
		{"S": 4, "M": 5, "L": 6, "XL": 5},
		{"S": 2, "M": 3, "L": 4, "XL": 3},
		{"S": 6, "M": 8, "L": 8, "XL": 6},
	]
	return plans[index]


def _colour_set_combinations(index):
	shift = index % len(COLOUR_SET_COMBINATIONS)
	return COLOUR_SET_COMBINATIONS[shift:] + COLOUR_SET_COMBINATIONS[:shift]


def _flat_bom_accessories(index):
	flat = _accessory_names()[6:]
	start = index * 3
	rotated = flat[start:] + flat[:start]
	return list(islice(cycle(rotated), 5))


def _create_ipd(spec):
	item_doc = frappe.get_doc("Item", spec["product"])
	doc = frappe.new_doc("Item Production Detail")
	doc.item = spec["product"]
	doc.version = 1
	doc.tech_pack_version = f"YRP-DEMO-TP-{spec['product'][-5:]}"
	doc.pattern_version = "YRP-DEMO-PATTERN-1"
	doc.approval_status = "Approved"
	doc.primary_item_attribute = "Size"
	doc.dependent_attribute = "Stage"
	doc.dependent_attribute_mapping = item_doc.dependent_attribute_mapping

	for attr in ["Stage", "Part", "Panel", "Colour", "Size"]:
		doc.append("item_attributes", {
			"attribute": attr,
			"mapping": _item_mapping(spec["product"], attr),
		})

	for row in PROCESS_SEQUENCE:
		doc.append("ipd_processes", row)

	_set_essdee_ipd_fields(doc, spec)
	_add_item_bom(doc, spec)
	doc.insert(ignore_permissions=True)
	return doc


def _set_essdee_ipd_fields(doc, spec):
	colour_sets = spec["colour_sets"]
	doc.packing_combo = spec["packing_combo"]
	doc.packing_attribute_no = len(colour_sets)
	doc.auto_calculate = 1
	doc.packing_attribute = "Colour"
	doc.packing_process = "Packing"
	doc.pack_in_stage = "Piece"
	doc.pack_out_stage = "Pack"
	doc.packing_uom = "Pieces"
	doc.stiching_process = "Stitching"
	doc.stiching_in_stage = "Cut"
	doc.stiching_out_stage = "Piece"
	doc.stiching_attribute = "Panel"
	doc.stiching_major_attribute_value = "Top Front"
	doc.is_same_packing_attribute = 1
	doc.cutting_process = "Cutting"
	doc.is_set_item = 1
	doc.set_item_attribute = "Part"
	doc.major_attribute_value = "Top"

	for colour_set in colour_sets:
		doc.append("packing_attribute_details", {
			"attribute_value": colour_set["major"],
			"quantity": 0,
		})
	for panel, qty in PANEL_QTY.items():
		doc.append("stiching_item_details", {
			"stiching_attribute_value": panel,
			"set_item_attribute_value": _part_for_panel(panel),
			"quantity": qty,
			"category": "Shorts" if "Bottom" in panel else "Body",
			"is_default": 1 if panel in {"Top Front", "Bottom Front"} else 0,
		})
	for index, colour_set in enumerate(colour_sets):
		for part in ATTRIBUTES["Part"]:
			doc.append("set_item_combination_details", {
				"index": index,
				"major_attribute_value": colour_set["major"],
				"set_item_attribute_value": part,
				"attribute_value": colour_set[part],
			})
		for panel in PANEL_QTY:
			part = _part_for_panel(panel)
			panel_colour = colour_set[part]
			doc.append("stiching_item_combination_details", {
				"index": index,
				"major_attribute_value": panel_colour,
				"set_item_attribute_value": panel,
				"attribute_value": panel_colour,
			})
	doc.append("cloth_detail", {
		"name1": "MAIN FABRIC 1",
		"cloth": spec["fabric"],
		"required_gsm": 165 + int(spec["fabric_weight"] * 100),
		"is_bom_item": 1,
	})

	for attr in ["Panel", "Colour"]:
		doc.append("cutting_attributes", {"attribute": attr})
		doc.append("cloth_attributes", {"attribute": attr})

	cutting_rows = _cutting_json_rows(spec)
	doc.cutting_items_json = json.dumps({
		"combination_type": "Cutting",
		"attributes": ["Panel", "Colour", "Dia", "Weight"],
		"items": cutting_rows,
		"select_list": {},
	})
	doc.cutting_cloths_json = json.dumps({
		"combination_type": "Cloth",
		"attributes": ["Panel", "Colour", "Cloth"],
		"items": [
			{
				"Panel": row["Panel"],
				"Colour": row["Colour"],
				"Cloth": "MAIN FABRIC 1",
			}
			for row in cutting_rows
		],
		"select_list": ["MAIN FABRIC 1"],
	})
	doc.cloth_accessory_json = json.dumps({"items": []})
	doc.accessory_clothtype_json = json.dumps({"items": []})
	doc.stiching_accessory_json = json.dumps({
		"items": [
			{
				"accessory": "Size Label 100% Cotton",
				"sizes": list(ATTRIBUTES["Size"]),
				"process": "Stitching",
			}
		]
	})
	doc.emblishment_details_json = json.dumps({"items": []})


def _part_for_panel(panel):
	return "Bottom" if "Bottom" in panel else "Top"


def _panel_colour_rows(spec):
	rows = []
	seen = set()
	for colour_set in spec["colour_sets"]:
		for panel in PANEL_QTY:
			part = _part_for_panel(panel)
			key = (part, panel, colour_set[part])
			if key in seen:
				continue
			seen.add(key)
			rows.append({
				"Part": part,
				"Panel": panel,
				"Colour": colour_set[part],
			})
	return rows


def _piece_colour_rows(spec):
	rows = []
	seen = set()
	for colour_set in spec["colour_sets"]:
		for part in ATTRIBUTES["Part"]:
			key = (part, colour_set[part])
			if key in seen:
				continue
			seen.add(key)
			rows.append({"Part": part, "Colour": colour_set[part]})
	return rows


def _cutting_json_rows(spec):
	rows = []
	for row in _panel_colour_rows(spec):
		rows.append({
			"Panel": row["Panel"],
			"Colour": row["Colour"],
			"Dia": "60 Dia",
			"Weight": spec["fabric_weight"],
		})
	return rows


def _add_item_bom(doc, spec):
	bom_rows = [
		("Size Label 100% Cotton", 1, 1, "Nos", "Stitching"),
		("Compo Label 100% Cotton", 1, 1, "Nos", "Stitching"),
		("Inner Elastic", 1, 0.45, "Meter", "Stitching"),
		("Fusing Sticker-EssdeeCore (45-80)", 1, 1, "Nos", "Yolk Fusing"),
		("Plain Poly Bag BOPP (37 Micron)", 1, 1, "Nos", "Packing"),
		("Corrugated Bottom Box-265mmx215mmx75mm", spec["packing_combo"], 1, "Nos", "Packing"),
	]
	for accessory_name in spec["flat_accessories"]:
		process = "Packing" if accessory_name in {
			"Hang Tag",
			"Price Tag",
			"Inner Card Big",
			"Hamic - Lovely Bermuda Set RNS Top Box",
		} else "Stitching"
		bom_rows.append((accessory_name, 1, 1, _item_uom(accessory_name), process))

	seen = set()
	for accessory_name, product_qty, bom_qty, uom, process in bom_rows:
		if accessory_name in seen:
			continue
		seen.add(accessory_name)
		bom_item = _item_by_name1(accessory_name)
		mapping_name = _create_bom_attribute_mapping(
			product_item=spec["product"],
			bom_item=bom_item,
			bom_qty=bom_qty,
		)
		doc.append("item_bom", {
			"item": bom_item,
			"qty_of_product": product_qty,
			"qty_of_bom_item": bom_qty,
			"uom": uom,
			"process_name": process,
			"based_on_attribute_mapping": 1,
			"attribute_mapping": mapping_name,
			"wastage_pct": 2 if process == "Stitching" else 0,
		})


def _create_bom_attribute_mapping(product_item, bom_item, bom_qty):
	bom_attrs = _item_attributes(bom_item)
	_assert(bom_attrs, f"BOM item {bom_item} should have at least one attribute")

	doc = frappe.new_doc("Item BOM Attribute Mapping")
	doc.item = product_item
	doc.bom_item = bom_item
	quantity_updates = []
	idx = -1
	for bom_attr in bom_attrs:
		item_attr = _source_attr_for_bom_attr(bom_attr)
		doc.append("item_attributes", {"attribute": item_attr, "same_attribute": 0})
		doc.append("bom_item_attributes", {"attribute": bom_attr, "same_attribute": 0})
		source_values = _item_attribute_values(product_item, item_attr)
		target_values = _item_attribute_values(bom_item, bom_attr)
		_assert(target_values, f"{bom_item} has no mapped values for {bom_attr}")
		for value_index, value in enumerate(source_values):
			idx += 1
			target_value = target_values[value_index % len(target_values)]
			quantity = _bom_mapping_quantity(bom_item, item_attr, value, bom_qty)
			item_row = doc.append("values", {
				"index": idx,
				"attribute": item_attr,
				"attribute_value": value,
				"type": "item",
				"quantity": quantity,
			})
			bom_row = doc.append("values", {
				"index": idx,
				"attribute": bom_attr,
				"attribute_value": target_value,
				"type": "bom",
				"quantity": quantity,
			})
			quantity_updates.extend([(item_row, quantity), (bom_row, quantity)])
	doc.insert(ignore_permissions=True)
	for row, quantity in quantity_updates:
		frappe.db.set_value(
			"Item BOM Attribute Mapping Value",
			row.name,
			"quantity",
			quantity,
			update_modified=False,
		)
	return doc.name


def _bom_mapping_quantity(bom_item, item_attr, item_value, default_qty):
	return (
		BOM_MAPPING_QUANTITY_BY_ITEM_VALUE.get(bom_item, {})
		.get(item_attr, {})
		.get(item_value, default_qty)
	)


def _source_attr_for_bom_attr(bom_attr):
	if bom_attr == "Name":
		return "Colour"
	return bom_attr


def _set_product_uom_conversion(product_item, packing_combo):
	doc = frappe.get_doc("Item", product_item)
	doc.set("uom_conversion_details", [])
	doc.append("uom_conversion_details", {"uom": "Pieces", "conversion_factor": 1})
	doc.append("uom_conversion_details", {"uom": "Box", "conversion_factor": packing_combo})
	doc.save(ignore_permissions=True)


def _create_production_order(index, spec):
	doc = frappe.new_doc("Production Order")
	doc.naming_series = "PPO-"
	doc.delivery_date = f"2026-06-{10 + index:02d}"
	doc.dont_deliver_after = f"2026-06-{20 + index:02d}"
	doc.comments = f"Production Order for {_lot_names()[index]}"
	for size, pack_qty in spec["pack_plan"].items():
		pack_variant = get_or_create_variant(
			spec["product"],
			{
				"Stage": "Pack",
				"Size": size,
			},
		)
		doc.append("production_order_details", {
			"item": spec["product"],
			"item_variant": pack_variant,
			"attributes_json": json.dumps({"Size": size}, separators=(",", ":")),
			"quantity": pack_qty,
		})
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


def _item_attributes(item_name):
	return [
		row.attribute
		for row in frappe.get_doc("Item", item_name).attributes
	]


def _item_attribute_values(item_name, attribute):
	mapping = _item_mapping(item_name, attribute)
	if not mapping:
		return []
	return [
		row.attribute_value
		for row in frappe.get_doc("Item Item Attribute Mapping", mapping).values
	]


def _create_process_matrices(ipd, spec):
	for size in ATTRIBUTES["Size"]:
		for piece in _piece_colour_rows(spec):
			size_spec = dict(spec)
			size_spec.update(piece)
			size_spec["size"] = size
			size_spec["panels"] = PART_PANELS[piece["Part"]]
			reference_variant = get_or_create_variant(
				size_spec["product"],
				{
					"Stage": "Piece",
					"Part": piece["Part"],
					"Colour": piece["Colour"],
					"Size": size,
				},
				dependent_attr=ipd.dependent_attribute_mapping,
			)
			_create_cutting_matrix(ipd, size_spec, reference_variant)
			_create_yolk_fusing_matrix(ipd, size_spec, reference_variant)
			_create_stitching_matrix(ipd, size_spec, reference_variant)
			_create_ironing_matrix(ipd, size_spec, reference_variant)
			_create_packing_matrix(ipd, size_spec, reference_variant)


def _create_cutting_matrix(ipd, spec, reference_variant):
	matrix = _new_matrix(ipd, "Cutting", reference_variant, input_item=spec["fabric"])
	matrix.append("input_attributes", {"attribute": "Colour"})
	for attr in ["Panel", "Colour", "Size"]:
		matrix.append("output_attributes", {"attribute": attr})
	for idx, panel in enumerate(spec["panels"], start=1):
		_add_combo(matrix, idx, "Input", 1, spec["fabric_weight"], "Kg", [("Colour", spec["Colour"])])
		_add_combo(
			matrix,
			idx,
			"Output",
			1,
			1,
			"Pieces",
			[("Panel", panel), ("Colour", spec["Colour"]), ("Size", spec["size"])],
		)
	matrix.insert(ignore_permissions=True)


def _create_yolk_fusing_matrix(ipd, spec, reference_variant):
	matrix = _new_matrix(ipd, "Yolk Fusing", reference_variant)
	for attr in ["Panel", "Colour", "Size"]:
		matrix.append("input_attributes", {"attribute": attr})
		matrix.append("output_attributes", {"attribute": attr})
	panel = "Top Back" if spec["Part"] == "Top" else "Bottom Back"
	_add_combo(
		matrix,
		1,
		"Input",
		1,
		1,
		"Pieces",
		[("Panel", panel), ("Colour", spec["Colour"]), ("Size", spec["size"])],
	)
	_add_combo(
		matrix,
		1,
		"Output",
		1,
		1,
		"Pieces",
		[("Panel", panel), ("Colour", spec["Colour"]), ("Size", spec["size"])],
	)
	matrix.insert(ignore_permissions=True)


def _create_stitching_matrix(ipd, spec, reference_variant):
	matrix = _new_matrix(ipd, "Stitching", reference_variant)
	for attr in ["Panel", "Colour", "Size"]:
		matrix.append("input_attributes", {"attribute": attr})
	for attr in ["Part", "Colour", "Size"]:
		matrix.append("output_attributes", {"attribute": attr})
	for idx, panel in enumerate(spec["panels"], start=1):
		_add_combo(
			matrix,
			1,
			"Input",
			idx,
			PANEL_QTY[panel],
			"Pieces",
			[("Panel", panel), ("Colour", spec["Colour"]), ("Size", spec["size"])],
		)
	_add_combo(matrix, 1, "Output", 1, 1, "Pieces", [("Part", spec["Part"]), ("Colour", spec["Colour"]), ("Size", spec["size"])])
	matrix.insert(ignore_permissions=True)


def _create_ironing_matrix(ipd, spec, reference_variant):
	matrix = _new_matrix(ipd, "Ironing", reference_variant)
	for attr in ["Part", "Colour", "Size"]:
		matrix.append("input_attributes", {"attribute": attr})
		matrix.append("output_attributes", {"attribute": attr})
	_add_combo(matrix, 1, "Input", 1, 1, "Pieces", [("Part", spec["Part"]), ("Colour", spec["Colour"]), ("Size", spec["size"])])
	_add_combo(matrix, 1, "Output", 1, 1, "Pieces", [("Part", spec["Part"]), ("Colour", spec["Colour"]), ("Size", spec["size"])])
	matrix.insert(ignore_permissions=True)


def _create_packing_matrix(ipd, spec, reference_variant):
	matrix = _new_matrix(ipd, "Packing", reference_variant)
	for attr in ["Part", "Colour", "Size"]:
		matrix.append("input_attributes", {"attribute": attr})
	matrix.append("output_attributes", {"attribute": "Size"})
	_add_combo(
		matrix,
		1,
		"Input",
		1,
		spec["packing_combo"],
		"Pieces",
		[("Part", spec["Part"]), ("Colour", spec["Colour"]), ("Size", spec["size"])],
	)
	_add_combo(matrix, 1, "Output", 1, 1, "Box", [("Size", spec["size"])])
	matrix.insert(ignore_permissions=True)


def _new_matrix(ipd, process_name, reference_variant, input_item=None):
	matrix = frappe.new_doc("IPD Process Matrix")
	matrix.ipd = ipd.name
	matrix.process_name = process_name
	matrix.reference_item_variant = reference_variant
	matrix.input_item = input_item
	matrix.output_item = ipd.item
	return matrix


def _add_combo(matrix, group_index, side, combo_index, qty, uom, attr_pairs):
	matrix.append("combinations", {
		"group_index": group_index,
		"side": side,
		"combo_index": combo_index,
		"quantity": qty,
		"uom": uom,
	})
	for attr, value in attr_pairs:
		matrix.append("combination_attributes", {
			"group_index": group_index,
			"side": side,
			"combo_index": combo_index,
			"attribute": attr,
			"attribute_value": value,
		})


def _create_lot(index, ipd, spec, production_order):
	doc = frappe.new_doc("Lot")
	doc.lot_name = _lot_names()[index]
	doc.production_order = production_order
	doc.item = spec["product"]
	doc.production_detail = ipd.name
	doc.status = "Open"
	doc.uom = "Box"
	doc.packing_uom = "Pieces"
	doc.pack_in_stage = "Piece"
	doc.pack_out_stage = "Pack"
	doc.dependent_attribute_mapping = ipd.dependent_attribute_mapping
	doc.packing_combo = spec["packing_combo"]
	doc.expected_delivery_date = f"2026-06-{10 + index:02d}"
	for row_index, (size, pack_qty) in enumerate(spec["pack_plan"].items()):
		pack_variant = get_or_create_variant(
			spec["product"],
			{
				"Stage": "Pack",
				"Size": size,
			},
			dependent_attr=ipd.dependent_attribute_mapping,
		)
		doc.append("items", {
			"item_variant": pack_variant,
			"qty": pack_qty,
			"ratio": row_index + 1,
			"mrp": 249 + (index * 25),
			"table_index": 0,
			"row_index": row_index,
		})
	doc.insert(ignore_permissions=True)
	return doc


def _calculate_lot_bom(lot_name):
	from yrp_essdee.yrp_essdee.doctype.lot.lot import calculate_bom

	return calculate_bom(lot_name)


def _ensure_uom(name, whole_number=0):
	if frappe.db.exists("UOM", name):
		doc = frappe.get_doc("UOM", name)
	else:
		doc = frappe.new_doc("UOM")
		doc.uom_name = name
	doc.enabled = 1
	doc.must_be_whole_number = whole_number
	doc.secondary_only = 0
	doc.save(ignore_permissions=True)
	return doc.name


def _ensure_item_group(name, parent=None, is_group=0):
	if frappe.db.exists("Item Group", name):
		doc = frappe.get_doc("Item Group", name)
	else:
		doc = frappe.new_doc("Item Group")
		doc.item_group_name = name
	doc.parent_item_group = parent
	doc.is_group = is_group
	doc.save(ignore_permissions=True)
	return doc.name


def _ensure_attribute(name):
	if frappe.db.exists("Item Attribute", name):
		return name
	doc = frappe.new_doc("Item Attribute")
	doc.attribute_name = name
	doc.numeric_values = 0
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_attribute_value(attribute, value):
	if frappe.db.exists("Item Attribute Value", value):
		existing_attr = frappe.db.get_value("Item Attribute Value", value, "attribute_name")
		_assert(
			existing_attr == attribute,
			f"Attribute Value {value} already exists for {existing_attr}, expected {attribute}",
		)
		return value
	doc = frappe.new_doc("Item Attribute Value")
	doc.flags.name_set = True
	doc.name = value
	doc.attribute_name = attribute
	doc.attribute_value = value
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_process(name):
	if frappe.db.exists("Process", name):
		return name
	doc = frappe.new_doc("Process")
	doc.process_name = name
	doc.input_uom = "Pieces"
	doc.output_uom = "Pieces"
	doc.insert(ignore_permissions=True)
	return doc.name


def _item_mapping(item, attr):
	for row in frappe.get_doc("Item", item).attributes:
		if row.attribute == attr:
			return row.mapping
	return None


def _item_by_name1(name):
	rows = frappe.get_all("Item", filters={"name1": name}, pluck="name", limit=1)
	_assert(rows, f"Item not found: {name}")
	return rows[0]


def _item_uom(name):
	return frappe.db.get_value("Item", _item_by_name1(name), "default_unit_of_measure") or "Nos"


def _items_by_name1(names):
	out = {}
	for row in frappe.get_all(
		"Item",
		filters={"name1": ["in", names]},
		fields=["name", "name1"],
		limit_page_length=1000,
	):
		out[row.name1] = row.name
	return out


def _accessory_names():
	return [spec["name"] for spec in ACCESSORY_SPECS]


def _lot_names():
	return [f"YD0526-{idx:02d}" for idx in range(1, 6)]


def _warehouse_names():
	current = [f"{spec['supplier_name']} Warehouse" for spec in SUPPLIERS]
	legacy = [
		"YRP Demo Warehouse - Essdee Main Unit",
		"YRP Demo Warehouse - Cutting Vendor",
		"YRP Demo Warehouse - Fusing Vendor",
		"YRP Demo Warehouse - Stitching Vendor",
		"YRP Demo Warehouse - Packing Vendor",
	]
	return current + legacy


def _force_delete(doctype, name):
	if not name or not frappe.db.exists(doctype, name):
		return
	try:
		if doctype == "Production Order":
			frappe.db.sql(
				"""
				DELETE FROM `tabProduction Ordered Detail`
				WHERE parent = %s AND parenttype = 'Production Order'
				""",
				(name,),
			)
		doc = frappe.get_doc(doctype, name)
		if getattr(doc, "docstatus", 0) == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	except Exception as exc:
		print(f"skip delete {doctype} {name}: {exc}")


def _assert(condition, message):
	if not condition:
		frappe.throw(message)
