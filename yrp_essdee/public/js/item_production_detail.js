// yrp_essdee — Item Production Detail JS.
// Verbatim port of production_api/essdee_production/doctype/item_production_detail/item_production_detail.js
// with endpoint paths repointed:
//   production_api.essdee_production.doctype.item_production_detail.item_production_detail.X
//                       → yrp_essdee.yrp_essdee.api.ipd.X
//   production_api.production_api.doctype.item.item.get_complete_item_details
//                       → yrp.yrp.doctype.item.item.get_complete_item_details
// Time-and-Action paths and MRP-Settings role checks are stubbed.

frappe.ui.form.on("Item Production Detail", {
	setup(frm) {
		frm.trigger("declarations");
		const setAttributeQuery = (doc) => {
			const attributes = (doc.item_attributes || []).map((a) => a.attribute);
			return { filters: { name: ["in", attributes] } };
		};
		frm.set_query("item", () => {
			frappe.call({
				method: "yrp_essdee.yrp_essdee.api.ipd.get_ipd_item_group",
				callback(r) {
					if (r.message) {
						frm.set_query("item", () => ({ filters: { item_group: ["in", r.message] } }));
					}
				},
			});
		});
		frm.set_query("set_item_attribute", setAttributeQuery);
		frm.set_query("packing_attribute", setAttributeQuery);
		frm.set_query("stiching_attribute", setAttributeQuery);

		const stage_query = () => ({
			query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
			filters: { mapping: frm.stage },
		});
		const packing_query = () => {
			if (!frm.doc.packing_attribute) frappe.throw("Please select the packing attribute first");
			return {
				query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
				filters: { mapping: frm.set_packing_attr_map_value },
			};
		};

		frm.set_query("attribute_value", "packing_attribute_details", packing_query);
		frm.set_query("stage", "ipd_processes", stage_query);
		frm.set_query("pack_in_stage", stage_query);
		frm.set_query("cutting_in_stage", stage_query);
		frm.set_query("stiching_out_stage", stage_query);
		frm.set_query("stiching_in_stage", stage_query);
		frm.set_query("pack_out_stage", stage_query);
		frm.set_query("dependent_attribute_value", "item_bom", stage_query);

		frm.set_query("stiching_attribute_value", "stiching_item_details", () => ({
			query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
			filters: { mapping: frm.stiching_attribute_mapping },
		}));
		frm.set_query("stiching_major_attribute_value", () => ({
			query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
			filters: { mapping: frm.stiching_attribute_mapping },
		}));
		frm.set_query("set_item_attribute_value", "stiching_item_details", () => ({
			query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
			filters: { mapping: frm.set_item_attr_map_value },
		}));
		frm.set_query("item", "item_bom", () => ({ filters: { disabled: 0 } }));
		frm.set_query("major_attribute_value", () => {
			if (!frm.doc.set_item_attribute) frappe.throw("Please set the Set Attribute Item");
			return {
				query: "yrp_essdee.yrp_essdee.api.ipd.get_attribute_detail_values",
				filters: { mapping: frm.set_item_attr_map_value },
			};
		});
	},

	declarations(frm) {
		frm.set_packing_attr_map_value = null;
		frm.set_item_attr_map_value = null;
		frm.stage = null;
		frm.stiching_attribute_mapping = null;
		const rows = frm.doc.item_attributes || [];
		for (const row of rows) {
			if (row.attribute === frm.doc.packing_attribute) frm.set_packing_attr_map_value = row.mapping;
			if (row.attribute === frm.doc.set_item_attribute) frm.set_item_attr_map_value = row.mapping;
			if (row.attribute === frm.doc.dependent_attribute) frm.stage = row.mapping;
			if (row.attribute === frm.doc.stiching_attribute) frm.stiching_attribute_mapping = row.mapping;
		}
	},

	async refresh(frm) {
		frm.trigger("declarations");
		frm.trigger("onload_post_render");

		// Approval buttons (production_api gates these by MRP Settings roles;
		// yrp_essdee shows them to System Manager + Item Master Manager).
		if (!frm.is_new() && frm.doc.approval_status !== "Approved") {
			if (frm.doc.approval_status === "Not Approved") {
				frm.add_custom_button(__("Approve for Cutting"), () => {
					frappe.call({
						method: "yrp_essdee.yrp_essdee.api.ipd.approve_ipd",
						args: { doc_name: frm.doc.name, approval_type: "Cutting Approved" },
						callback() {
							frappe.show_alert({ message: __("Approved for Cutting"), indicator: "blue" });
							frm.reload_doc();
						},
					});
				});
			}
			frm.add_custom_button(__("Approve"), () => {
				frappe.call({
					method: "yrp_essdee.yrp_essdee.api.ipd.approve_ipd",
					args: { doc_name: frm.doc.name, approval_type: "Approved" },
					callback() {
						frappe.show_alert({ message: __("IPD Approved"), indicator: "green" });
						frm.reload_doc();
					},
				});
			});
			frm.change_custom_button_type(__("Approve"), null, "success");
		}
		if (!frm.is_new() && frm.doc.approval_status !== "Not Approved" && frappe.user_roles.includes("System Manager")) {
			frm.add_custom_button(__("Revert Approval"), () => {
				frappe.confirm(__("Revert approval status to Not Approved?"), () => {
					frappe.call({
						method: "yrp_essdee.yrp_essdee.api.ipd.revert_ipd_approval",
						args: { doc_name: frm.doc.name },
						callback() {
							frappe.msgprint({ title: __("Success"), message: __("IPD Reverted Successfully"), indicator: "green" });
							frm.reload_doc();
						},
					});
				});
			});
			frm.change_custom_button_type(__("Revert Approval"), null, "danger");
		}

		// Reset all HTML wrappers
		const html_wrappers = [
			"item_attribute_list_values_html", "dependent_attribute_details_html", "bom_attribute_mapping_html",
			"set_items_html", "stiching_items_html",
			"cutting_items_html", "cutting_cloths_html", "cloth_accessories_html",
			"stiching_accessory_html", "accessory_clothtype_combination_html",
			"emblishment_details_html", "select_cloths_attribute_html",
			"select_attributes_html", "select_cloth_accessory_html", "bundle_group_html",
		];
		for (const fn of html_wrappers) {
			if (frm.fields_dict[fn] && frm.fields_dict[fn].wrapper) {
				$(frm.fields_dict[fn].wrapper).html("");
			}
		}

		if (frm.doc.stiching_in_stage && frm.doc.dependent_attribute) {
			frm.cutting_attrs = await get_stich_in_attributes(
				frm.doc.dependent_attribute_mapping,
				frm.doc.stiching_in_stage,
				frm.doc.item
			);
			if (frm.doc.is_set_item) frm.cutting_attrs.push(frm.doc.set_item_attribute);
			make_select_attributes(frm, "select_attributes_html", "select_attributes_wrapper", "select_attrs_multicheck", "cutting_attributes", "cutting_items_json", "get_cutting_combination");
			make_select_attributes(frm, "select_cloths_attribute_html", "select_cloths_attributes_wrapper", "select_cloth_attrs_multicheck", "cloth_attributes", "cutting_cloths_json", "get_cloth_combination");
			let accessoryClothTypeObj = {};
			try { accessoryClothTypeObj = JSON.parse(frm.doc.accessory_clothtype_json || "{}"); } catch (_) {}
			if (Object.keys(accessoryClothTypeObj).length > 0) {
				make_select_attributes(frm, "select_cloth_accessory_html", "select_cloths_accessory_wrapper", "select_cloth_accessory_multicheck", "accessory_attributes", "cloth_accessory_json", "get_accessory_combination");
			}
		}
		frm.refresh_field("emblishment_details_json");
		frm.refresh_field("cutting_items_json");
		frm.refresh_field("cutting_cloths_json");
		frm.refresh_field("cloth_accessory_json");
		frm.refresh_field("accessory_clothtype_json");
		frm.refresh_field("stiching_accessory_json");

		if (frm.doc.__islocal) {
			hide_field(["item_attribute_list_values_html", "bom_attribute_mapping_html", "dependent_attribute_details_html"]);
		} else {
			unhide_field(["item_attribute_list_values_html", "bom_attribute_mapping_html", "dependent_attribute_details_html"]);
			frm.trigger("load_item_attribute_details");

			if (!frm.doc.is_set_item) hide_field("set_items_html");
			else { unhide_field("set_items_html"); frm.trigger("make_set_combination"); }

			frm.add_custom_button("Duplicate IPD", () => {
				const d = new frappe.ui.Dialog({
					title: "Duplicate IPD",
					fields: [{ label: "Item", fieldname: "item", fieldtype: "Link", options: "Item", default: frm.doc.item, reqd: 1 }],
					primary_action_label: "Duplicate",
					primary_action(values) {
						frappe.call({
							method: "yrp_essdee.yrp_essdee.api.ipd.duplicate_ipd",
							args: { ipd: frm.doc.name, item: values.item },
							freeze: true,
							freeze_message: "Duplicating IPD",
							callback(r) {
								d.hide();
								frappe.set_route("Form", "Item Production Detail", r.message);
							},
						});
					},
				});
				frappe.call({
					method: "yrp_essdee.yrp_essdee.api.ipd.get_ipd_item_group",
					callback(r) {
						if (r.message) d.fields_dict.item.get_query = () => ({ filters: { item_group: ["in", r.message] } });
					},
				});
				d.show();
			});
		}

		frm.trigger("make_hide_and_unhide_tabs");
		if ((frm.doc.cloth_detail || []).length === 0) frm.set_df_property("get_cutting_combination", "hidden", true);
		else frm.set_df_property("get_cutting_combination", "hidden", false);

		// Approved-state lock
		if (!frm.is_new() && frm.doc.approval_status === "Approved") {
			const html_fields = [
				"item_attribute_list_values_html", "dependent_attribute_details_html",
				"set_items_html", "stiching_items_html", "cutting_items_html",
				"cutting_cloths_html", "cloth_accessories_html", "stiching_accessory_html",
				"accessory_clothtype_combination_html", "select_attributes_html",
				"select_cloths_attribute_html", "select_cloth_accessory_html", "bundle_group_html",
			];
			html_fields.forEach((f) => {
				if (frm.fields_dict[f]) {
					$(frm.fields_dict[f].wrapper).css({ "pointer-events": "none", opacity: "0.7" });
				}
			});
			["item_attributes", "item_bom", "packing_attribute_details", "stiching_item_details", "cloth_detail", "cutting_marker_groups"].forEach((t) => frm.set_df_property(t, "read_only", 1));
			["get_packing_attribute_values", "get_set_item_combination", "get_stiching_item_combination", "get_cutting_combination", "update_cloth_items", "get_cloth_combination", "get_stiching_attribute_values", "get_accessory_combination", "get_stiching_accessory_combination"].forEach((b) => frm.set_df_property(b, "hidden", 1));
			["item", "packing_combo", "packing_attribute_no", "primary_item_attribute", "dependent_attribute", "stiching_major_attribute_value", "major_attribute_value", "packing_attribute", "stiching_attribute", "set_item_attribute", "is_set_item", "is_same_packing_attribute", "auto_calculate"].forEach((f) => frm.set_df_property(f, "read_only", 1));
		}
	},

	make_hide_and_unhide_tabs(frm) {
		if (frm.doc.dependent_attribute) {
			frm.trigger("make_stiching_combination");
			frm.trigger("bundle_combination");
			frm.trigger("make_cutting_combination");
			frm.trigger("make_cloth_accessories");
			frm.trigger("make_stiching_accessory_combination");
			frm.trigger("emblishment_details");
			if ((frm.doc.cloth_detail || []).length > 0) frm.trigger("make_clothtype_accessory_combination");
		}
		if (!frm.doc.packing_attribute) {
			frm.$wrapper.find("[data-fieldname='set_item_tab']").hide();
		} else {
			frm.$wrapper.find("[data-fieldname='set_item_tab']").show();
		}
	},

	bundle_combination(frm) {
		if ((frm.doc.stiching_item_details || []).length > 0 && frm.fields_dict["bundle_group_html"]) {
			frm.bundle_group = new frappe.production.ui.BundleGroup(frm.fields_dict["bundle_group_html"].wrapper);
			if (frm.doc.__onload && frm.doc.__onload.bundle_group_details) {
				frm.bundle_group.load_data(frm.doc.__onload.bundle_group_details);
			}
		}
	},

	load_item_attribute_details(frm) {
		$(frm.fields_dict["item_attribute_list_values_html"].wrapper).html("");
		new frappe.production.ui.ItemAttributeList({
			wrapper: frm.fields_dict["item_attribute_list_values_html"].wrapper,
			attr_values: (frm.doc.__onload && frm.doc.__onload["attr_list"]) || [],
		});
		$(frm.fields_dict["dependent_attribute_details_html"].wrapper).html("");
		new frappe.production.ui.ItemDependentAttributeDetail(frm.fields_dict["dependent_attribute_details_html"].wrapper);
		$(frm.fields_dict["bom_attribute_mapping_html"].wrapper).html("");
		new frappe.production.ui.BomItemAttributeMapping(frm.fields_dict["bom_attribute_mapping_html"].wrapper);
	},

	async make_set_combination(frm) {
		$(frm.fields_dict["set_items_html"].wrapper).html("");
		frm.set_item = new frappe.production.ui.CombinationItemDetail(frm.fields_dict["set_items_html"].wrapper);
		if (frm.doc.__onload && frm.doc.__onload.set_item_detail) {
			frm.doc["set_item_detail"] = JSON.stringify(frm.doc.__onload.set_item_detail);
			await frm.set_item.load_data(frm.doc.__onload.set_item_detail);
			frm.set_item.set_attributes();
		}
	},

	async update_cloth_items(frm) {
		if (frm.cloth_item && frm.doc.cutting_cloths_json) {
			const cloths = (frm.doc.cloth_detail || []).filter((c) => c.name1 && c.cloth).map((c) => c.name1);
			let cut_json = frm.doc.cutting_cloths_json;
			if (typeof cut_json === "string") cut_json = JSON.parse(cut_json);
			cut_json["select_list"] = cloths;
			await frm.cloth_item.load_data(cut_json);
			frm.cloth_item.set_attributes();
		}
		if (frm.stiching_accessory && frm.doc.stiching_accessory_json) {
			const cloths = (frm.doc.cloth_detail || []).filter((c) => c.name1 && c.cloth).map((c) => c.name1);
			let stich_json = frm.doc.stiching_accessory_json;
			if (typeof stich_json === "string") stich_json = JSON.parse(stich_json);
			stich_json["select_list"] = cloths;
			await frm.stiching_accessory.load_data(stich_json);
			frm.stiching_accessory.set_attributes();
		}
	},

	async make_stiching_combination(frm) {
		$(frm.fields_dict["stiching_items_html"].wrapper).html("");
		frm.stiching_item = new frappe.production.ui.CombinationItemDetail(frm.fields_dict["stiching_items_html"].wrapper);
		if (frm.doc.__onload && frm.doc.__onload.stiching_item_detail) {
			frm.doc["stiching_item_detail"] = JSON.stringify(frm.doc.__onload.stiching_item_detail);
			await frm.stiching_item.load_data(frm.doc.__onload.stiching_item_detail);
			frm.stiching_item.set_attributes();
		}
	},

	async make_cutting_combination(frm) {
		$(frm.fields_dict["cutting_items_html"].wrapper).html("");
		frm.cutting_item = new frappe.production.ui.CuttingItemDetail(frm.fields_dict["cutting_items_html"].wrapper);
		if (frm.doc.cutting_items_json) {
			await frm.cutting_item.load_data(frm.doc.cutting_items_json);
			frm.cutting_item.set_attributes();
		}
		$(frm.fields_dict["cutting_cloths_html"].wrapper).html("");
		frm.cloth_item = new frappe.production.ui.CuttingItemDetail(frm.fields_dict["cutting_cloths_html"].wrapper);
		if (frm.doc.cutting_cloths_json) {
			await frm.cloth_item.load_data(frm.doc.cutting_cloths_json);
			frm.cloth_item.set_attributes();
		}
	},

	async make_cloth_accessories(frm) {
		$(frm.fields_dict["cloth_accessories_html"].wrapper).html("");
		frm.cloth_accessories = new frappe.production.ui.ClothAccessory(frm.fields_dict["cloth_accessories_html"].wrapper);
		if (frm.doc.cloth_accessory_json) {
			await frm.cloth_accessories.load_data(frm.doc.cloth_accessory_json);
			frm.cloth_accessories.set_attributes();
		}
	},

	async make_stiching_accessory_combination(frm) {
		$(frm.fields_dict["stiching_accessory_html"].wrapper).html("");
		frm.stiching_accessory = new frappe.production.ui.ClothAccessoryCombination(frm.fields_dict["stiching_accessory_html"].wrapper);
		if (frm.doc.stiching_accessory_json) {
			let acc = frm.doc.stiching_accessory_json;
			const cloths = (frm.doc.cloth_detail || []).map((c) => c.name1);
			if (typeof acc === "string") acc = JSON.parse(acc);
			acc["select_list"] = cloths;
			await frm.stiching_accessory.load_data(acc);
			frm.stiching_accessory.set_attributes();
		}
	},

	async make_clothtype_accessory_combination(frm) {
		$(frm.fields_dict["accessory_clothtype_combination_html"].wrapper).html("");
		frm.accessory_clothtype = new frappe.production.ui.AccessoryItems(frm.fields_dict["accessory_clothtype_combination_html"].wrapper);
		if (frm.doc.accessory_clothtype_json) {
			await frm.accessory_clothtype.load_data(frm.doc.accessory_clothtype_json);
		}
	},

	emblishment_details(frm) {
		$(frm.fields_dict["emblishment_details_html"].wrapper).html("");
		frm.emblishment = new frappe.production.ui.EmblishmentDetails(frm.fields_dict["emblishment_details_html"].wrapper);
		if (frm.doc.emblishment_details_json) {
			frm.emblishment.load_data(frm.doc.emblishment_details_json);
		}
	},

	onload_post_render(frm) {
		showOrHideColumns(frm, ["dependent_attribute_value"], "item_bom", frm.doc.dependent_attribute ? 0 : 1);
		updateChildTableReqd(frm, ["dependent_attribute_value"], "item_bom", frm.doc.dependent_attribute ? 1 : 0);
		showOrHideColumns(frm, ["set_item_attribute_value", "is_default"], "stiching_item_details", frm.doc.is_set_item ? 0 : 1);
		updateChildTableReqd(frm, ["set_item_attribute_value", "is_default"], "stiching_item_details", frm.doc.is_set_item ? 1 : 0);
	},

	is_set_item(frm) {
		showOrHideColumns(frm, ["set_item_attribute_value", "is_default"], "stiching_item_details", frm.doc.is_set_item ? 0 : 1);
		updateChildTableReqd(frm, ["set_item_attribute_value", "is_default"], "stiching_item_details", frm.doc.is_set_item ? 1 : 0);
	},

	get_packing_attribute_values(frm) {
		if (!frm.set_packing_attr_map_value) {
			frappe.msgprint("Set the Packing Attribute first (Advance Settings tab) and ensure it appears in Item Attributes.");
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_mapping_attribute_values",
			args: {
				attribute_mapping_value: frm.set_packing_attr_map_value,
				attribute_no: frm.doc.packing_attribute_no,
			},
			callback(r) {
				if (r.message) {
					frm.set_value("packing_attribute_details", r.message);
					frm.refresh_field("packing_attribute_details");
				}
			},
		});
	},

	get_stiching_attribute_values(frm) {
		if (!frm.stiching_attribute_mapping) {
			frappe.msgprint("Set the Stiching Attribute first.");
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_mapping_attribute_values",
			args: { attribute_mapping_value: frm.stiching_attribute_mapping, attribute_no: null },
			callback(r) {
				if (r.message) {
					frm.set_value("stiching_item_details", r.message);
					frm.refresh_field("stiching_item_details");
				}
			},
		});
	},

	async validate(frm) {
		if (frm.doc.__islocal) return;
		if (frm.set_item && frm.doc.is_set_item) {
			const item_details = frm.set_item.get_data();
			frm.doc["set_item_detail"] = JSON.stringify(item_details);
		}
		if (frm.stiching_item) {
			const item_details = frm.stiching_item.get_data();
			if (item_details && (item_details["values"] || []).length > 0) {
				frm.doc["stiching_item_detail"] = JSON.stringify(item_details);
			}
		}
		const sync_multicheck = (mc, target_field) => {
			if (!mc) return;
			const list = mc.get_checked_options().map((a) => ({ attribute: a }));
			frm.set_value(target_field, list);
		};
		sync_multicheck(frm.select_attrs_multicheck, "cutting_attributes");
		sync_multicheck(frm.select_cloth_attrs_multicheck, "cloth_attributes");
		sync_multicheck(frm.select_cloth_accessory_multicheck, "accessory_attributes");

		const sync_json = (vue, doc_field) => {
			if (!vue) return;
			const data = vue.get_data();
			if (data == null) frm.doc[doc_field] = {};
			else if ((data.items || []).length > 0) frm.doc[doc_field] = data;
		};
		sync_json(frm.cutting_item, "cutting_items_json");
		sync_json(frm.cloth_item, "cutting_cloths_json");
		sync_json(frm.cloth_accessories, "cloth_accessory_json");
		sync_json(frm.stiching_accessory, "stiching_accessory_json");

		if (frm.accessory_clothtype) {
			const data = frm.accessory_clothtype.get_data();
			frm.doc.accessory_clothtype_json = data == null ? {} : data;
		}
		if (frm.emblishment) {
			const items = frm.emblishment.get_items();
			frm.doc.emblishment_details_json = !items ? {} : items;
		}
		if (frm.bundle_group) {
			frm.doc["marker_details"] = frm.bundle_group.get_items();
		}
	},

	item(frm) {
		if (!frm.doc.item) {
			frm.set_value("primary_item_attribute", "");
			frm.set_value("item_attributes", []);
			frm.set_value("dependent_attribute", "");
			frm.set_value("dependent_attribute_mapping", "");
			return;
		}
		frappe.call({
			method: "yrp.yrp.doctype.item.item.get_complete_item_details",
			args: { item_name: frm.doc.item },
			callback(r) {
				if (!r.message) return;
				frm.set_value("primary_item_attribute", r.message.primary_attribute);
				frm.set_value("item_attributes", r.message.attributes);
				frm.set_value("dependent_attribute", r.message.dependent_attribute);
				frm.set_value("dependent_attribute_mapping", r.message.dependent_attribute_mapping);
			},
		});
	},

	get_set_item_combination(frm) {
		if (!frm.doc.major_attribute_value) {
			frappe.msgprint("Set the major attribute value");
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_new_combination",
			args: {
				attribute_mapping_value: frm.set_item_attr_map_value,
				packing_attribute_details: frm.doc.packing_attribute_details,
				major_attribute_value: frm.doc.major_attribute_value,
			},
			async callback(r) {
				if (frm.set_item) {
					await frm.set_item.load_data(r.message);
					frm.set_item.set_attributes();
				}
			},
		});
	},

	get_stiching_item_combination(frm) {
		if (!frm.doc.stiching_attribute) return;
		if (!frm.doc.stiching_major_attribute_value) {
			frappe.msgprint("Set the stiching major attribute value");
			return;
		}
		if ((frm.doc.stiching_item_details || []).length === 0) {
			frappe.msgprint("Set the Stiching Item Detail");
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_new_combination",
			args: {
				attribute_mapping_value: frm.stiching_attribute_mapping,
				packing_attribute_details: frm.doc.packing_attribute_details,
				major_attribute_value: frm.doc.stiching_major_attribute_value,
				is_same_packing_attribute: frm.doc.is_same_packing_attribute,
				doc_name: frm.doc.name,
			},
			async callback(r) {
				if (frm.stiching_item) {
					await frm.stiching_item.load_data(r.message);
					frm.stiching_item.set_attributes();
					frm.dirty();
				}
			},
		});
	},

	get_cutting_combination(frm) {
		const checked = frm.select_attrs_multicheck ? frm.select_attrs_multicheck.get_checked_options() : [];
		if (checked.length === 0) {
			frappe.msgprint("Select the attributes to make combination");
			if (frm.cutting_item) frm.cutting_item.load_data([]);
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_combination",
			args: { doc_name: frm.doc.name, attributes: checked, combination_type: "Cutting" },
			async callback(r) {
				if (frm.cutting_item) {
					await frm.cutting_item.load_data(r.message);
					frm.cutting_item.set_attributes();
				}
			},
		});
	},

	get_cloth_combination(frm) {
		if ((frm.doc.cloth_detail || []).length === 0) {
			frappe.msgprint("Fill The Cloth Details");
			return;
		}
		const cloth_list = (frm.doc.cloth_detail || []).map((c) => c.name1);
		const checked = frm.select_cloth_attrs_multicheck ? frm.select_cloth_attrs_multicheck.get_checked_options() : [];
		if (checked.length === 0) {
			frappe.msgprint("Select the attributes to make combination");
			if (frm.cloth_item) frm.cloth_item.load_data([]);
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_combination",
			args: { doc_name: frm.doc.name, attributes: checked, combination_type: "Cloth", cloth_list },
			async callback(r) {
				if (frm.cloth_item) {
					await frm.cloth_item.load_data(r.message);
					frm.cloth_item.set_attributes();
				}
			},
		});
	},

	get_accessory_combination(frm) {
		const checked = frm.select_cloth_accessory_multicheck ? frm.select_cloth_accessory_multicheck.get_checked_options() : [];
		if (checked.length === 0) {
			frappe.msgprint("Select the attributes to make combination");
			if (frm.cloth_accessories) frm.cloth_accessories.load_data([]);
			return;
		}
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_combination",
			args: { doc_name: frm.doc.name, attributes: checked, combination_type: "Accessory" },
			async callback(r) {
				if (frm.cloth_accessories) {
					await frm.cloth_accessories.load_data(r.message);
					frm.cloth_accessories.set_attributes();
				}
			},
		});
	},

	get_stiching_accessory_combination(frm) {
		const cloth_list = (frm.doc.cloth_detail || []).map((c) => c.name1);
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_stiching_accessory_combination",
			args: { cloth_list, doc_name: frm.doc.name },
			async callback(r) {
				if (frm.stiching_accessory) {
					await frm.stiching_accessory.load_data(r.message);
					frm.stiching_accessory.set_attributes();
				}
			},
		});
	},

	set_item_attribute(frm) {
		frm.set_item = new frappe.production.ui.CombinationItemDetail(frm.fields_dict["set_items_html"].wrapper);
		if (frm.doc.major_attribute_value) frm.trigger("get_set_item_combination");
		if (frm.doc.is_set_item && frm.doc.set_item_attribute) {
			frm.trigger("declarations");
			unhide_field(["set_items_html"]);
			if (frm.doc.major_attr_value) frm.trigger("get_set_item_combination");
		}
	},

	packing_attribute(frm) {
		if (frm.doc.packing_attribute) frm.trigger("declarations");
	},

	major_attribute_value(frm) {
		frm.trigger("get_set_item_combination");
	},

	stiching_attribute(frm) {
		if (frm.doc.stiching_attribute) frm.trigger("declarations");
	},
});

function showOrHideColumns(frm, fields, table, hidden) {
	const grid_field = frm.get_field(table);
	if (!grid_field) return;
	const grid = grid_field.grid;
	if (!grid || !grid.fields_map) return;
	if (frappe.ui.form.editable_row) frappe.ui.form.editable_row.toggle_editable_row(false);
	for (const field of fields) {
		if (grid.fields_map[field]) grid.fields_map[field].hidden = hidden;
	}
	grid.visible_columns = undefined;
	grid.setup_visible_columns();
	if (grid.header_row) {
		grid.header_row.wrapper.remove();
		delete grid.header_row;
		grid.make_head();
	}
	for (const row of grid.grid_rows || []) {
		if (row.open_form_button) { row.open_form_button.parent().remove(); delete row.open_form_button; }
		for (const field in row.columns) {
			if (row.columns[field] !== undefined) row.columns[field].remove();
		}
		for (const fieldname of fields) {
			const df = (row.docfields || []).find((f) => f.fieldname === fieldname);
			if (df) df.hidden = hidden;
		}
		delete row.columns;
		row.columns = [];
		row.render_row();
	}
	if (frappe.ui.form.editable_row) frappe.ui.form.editable_row.toggle_editable_row(false);
}

function updateChildTableReqd(frm, fields, table, reqd) {
	const grid_field = frm.get_field(table);
	if (!grid_field) return;
	const grid = grid_field.grid;
	if (!grid) return;
	for (const row of grid.grid_rows || []) {
		if (row.open_form_button) { row.open_form_button.parent().remove(); delete row.open_form_button; }
		for (const field in row.columns) {
			if (row.columns[field] !== undefined) row.columns[field].remove();
		}
		for (const fieldname of fields) {
			const df = (row.docfields || []).find((f) => f.fieldname === fieldname);
			if (df) df.reqd = reqd;
		}
		delete row.columns;
		row.columns = [];
		row.render_row();
	}
	if (frappe.ui.form.editable_row) frappe.ui.form.editable_row.toggle_editable_row(false);
}

async function get_stich_in_attributes(dependent_attribute_mapping, stiching_in_stage, item) {
	return new Promise((resolve) => {
		frappe.call({
			method: "yrp_essdee.yrp_essdee.api.ipd.get_stiching_in_stage_attributes",
			args: { dependent_attribute_mapping, stiching_in_stage, item },
			callback: (r) => resolve(r.message || []),
		});
	});
}

function make_select_attributes(frm, html_field, html_class, name, attrs, json_field, combination_type) {
	const $wrapper = frm.get_field(html_field).$wrapper;
	$wrapper.empty();
	const select_attributes_wrapper = $(`<div class="${html_class}"></div>`).appendTo($wrapper);
	const cutting_attr_list = frm.doc[attrs] || [];
	const check_list = cutting_attr_list.map((a) => a.attribute);
	frm[name] = frappe.ui.form.make_control({
		parent: select_attributes_wrapper,
		df: {
			fieldname: "select_attributes_wrapper",
			fieldtype: "MultiCheck",
			sort_options: false,
			columns: 4,
			get_data: () => (frm.cutting_attrs || []).map((attr) => ({ label: attr, value: attr, checked: check_list.includes(attr) ? 1 : 0 })),
			on_change: () => {
				frm.set_value(json_field, {});
				frm.trigger(combination_type);
			},
		},
		render_input: true,
	});
	frm[name].refresh_input();
}
