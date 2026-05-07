// yrp_essdee - Lot.js. Mirrors production_api/essdee_production/doctype/lot/lot.js.
// Endpoint paths repointed to yrp_essdee. Time and Action paths skipped.

frappe.ui.form.on("Lot", {
	setup(frm) {
		frm.set_query("production_detail", (doc) => {
			const filters = {};
			if (doc.item) {
				filters.item = doc.item;
			}
			return { filters };
		});
		frm.set_query("production_order", (doc) => ({
			filters: { item: doc.item, docstatus: 1 },
		}));
	},
	refresh(frm) {
		$(".layout-side-section").css("display", "none");

		// Read-only locks from the PO/IPD relationship
		frappe.call({
			method: "yrp_essdee.yrp_essdee.doctype.lot.lot.check_enabled_po",
			callback: (r) => {
				const enabled = !!r.message;
				frm.set_df_property("item", "read_only", enabled);
				frm.refresh_field("item");
				if (frm.doc.item && !frm.doc.production_order) {
					frm.set_df_property("production_order", "read_only", true);
				} else {
					frm.set_df_property("production_order", "read_only", !enabled);
				}
				frm.refresh_field("production_order");
			},
		});

		if (!frm.is_new()) {
			frm.add_custom_button(__("Purchase Summary"), () => {
				frappe.set_route("query-report", "Lot Purchase Summary", {
					lot: frm.doc.name,
				});
			}, __("View"));
		}

		frm.set_df_property("bom_summary", "cannot_add_rows", true);
		frm.set_df_property("bom_summary", "cannot_delete_rows", true);

		if ((frm.doc.lot_time_and_action_details || []).length === 0) {
			frm.add_custom_button("Calculate Order Items", () => {
				const d = new frappe.ui.Dialog({
					title: "Confirm Calculation",
					primary_action_label: "Yes",
					secondary_action_label: "No",
					primary_action() {
						d.hide();
						frappe.call({
							method: "yrp_essdee.yrp_essdee.doctype.lot.lot.update_order_details",
							args: {
								doc_name: frm.doc.name,
							},
							freeze: true,
							freeze_message: __("Calculating Order Items..."),
							callback: () => {
								frm.reload_doc();
							},
						});
					},
					secondary_action() {
						d.hide();
					},
				});
				d.show();
			});
		}

		// Mount LotOrder in items_html (the order plan editor)
		$(frm.fields_dict["items_html"].wrapper).html("");
		frm.item = new frappe.production.ui.LotOrder(frm.fields_dict["items_html"].wrapper);
		if (frm.doc.__onload && frm.doc.__onload.item_details) {
			frm.doc["item_details"] = JSON.stringify(frm.doc.__onload.item_details);
			frm.item.load_data(frm.doc.__onload.item_details);
		} else {
			if (frm.doc.item && frm.doc.production_detail) {
				frappe.call({
					method: "yrp_essdee.yrp_essdee.doctype.lot.lot.get_item_details",
					args: {
						item_name: frm.doc.item,
						uom: frm.doc.uom,
						production_detail: frm.doc.production_detail,
						ppo: frm.doc.production_order,
					},
					callback: (r) => {
						frm.item.load_data(r.message);
						if (frm.doc.production_order) {
							frm.item.show_inputs();
							frm.item.load_data(r.message);
						}
						cur_frm.dirty();
					},
				});
			} else {
				frm.item.load_data([]);
			}
		}

		if ((frm.doc.lot_order_details || []).length > 0) {
			frappe.call({
				method: "yrp_essdee.yrp_essdee.doctype.lot.lot.get_packing_attributes",
				args: {
					ipd: frm.doc.production_detail,
				},
				callback: (r) => {
					frm.fields_dict["size_set_colour"].df.options = r.message.major_colours;
					frm.refresh_field("size_set_colour");
				},
			});
		}

		// Mount CutPlanItems in lot_item_order_detail_html (read-only order grid view)
		$(frm.fields_dict["lot_item_order_detail_html"].wrapper).html("");
		frm.order_detail = new frappe.production.ui.CutPlanItems(
			frm.fields_dict["lot_item_order_detail_html"].wrapper
		);
		if (frm.doc.__onload && frm.doc.__onload.order_item_details) {
			frm.order_detail.load_data(
				frm.doc.__onload.order_item_details,
				(frm.doc.lot_time_and_action_details || []).length
			);
		} else {
			frm.order_detail.load_data([], 0);
		}
		if (frm.doc.is_transferred) frm.order_detail.update_status();

		// OCR Detail
		if (!frm.is_new() && frm.doc.item && frm.doc.production_detail) {
			$(frm.fields_dict["ocr_detail_html"].wrapper).html("");
			new frappe.production.ui.OCRDetail(frm.fields_dict["ocr_detail_html"].wrapper);
		}

		// Alternative Detail (only when has_transferred)
		if (frm.doc.has_transferred) {
			$(frm.fields_dict["alternative_html"].wrapper).html("");
			new frappe.production.ui.AlternativeDetail(frm.fields_dict["alternative_html"].wrapper);
		}
	},
	production_order(frm) {
		if (frm.doc.production_order) {
			frappe.call({
				method: "yrp_essdee.overrides.production_order.get_production_order_item",
				args: { production_order: frm.doc.production_order },
				callback: (r) => {
					if (r.message) {
						frm.set_value("item", r.message);
						frm.refresh_field("item");
					}
				},
			});
		}
	},
	validate(frm) {
		// Stuff Vue grid state onto the doc as transient fields; the Lot's
		// before_validate hook (server) parses these and writes to lot.items.
		if (frm.item) {
			const items = frm.item.get_data();
			frm.doc["item_details"] = JSON.stringify(items);
		}
		const order_items = frm.order_detail ? frm.order_detail.get_items() : [];
		frm.doc["order_item_details"] = JSON.stringify(order_items);
	},
	item(frm) {
		if (!frm.doc.item && frm.item) {
			frm.item.load_data([]);
		}
	},
	async production_detail(frm) {
		if (!frm.doc.production_detail) return;
		let ipd_item = frm.doc.item;
		await frappe.call({
			method: "yrp_essdee.yrp_essdee.doctype.lot.lot.get_isfinal_uom",
			args: {
				item_production_detail: frm.doc.production_detail,
				get_pack_stage: true,
			},
			callback: (r) => {
				if (!r.message) return;
				ipd_item = r.message.item || ipd_item;
				if (r.message.item && frm.doc.item !== r.message.item) {
					if (frm.doc.production_order && frm.doc.item) {
						frm.set_value("production_order", "");
					}
					frm.set_value("item", r.message.item);
				}
				frm.set_value("uom", r.message.uom);
				frm.set_value("pack_in_stage", r.message.pack_in_stage);
				frm.set_value("packing_uom", r.message.packing_uom);
				frm.set_value("pack_out_stage", r.message.pack_out_stage);
				frm.set_value("dependent_attribute_mapping", r.message.dependent_attr_mapping);
				frm.set_value("tech_pack_version", r.message.tech_pack_version);
				frm.set_value("pattern_version", r.message.pattern_version);
				frm.set_value("packing_combo", r.message.packing_combo);
			},
		});
		frappe.call({
			method: "yrp_essdee.yrp_essdee.doctype.lot.lot.get_item_details",
			args: {
				item_name: ipd_item || frm.doc.item,
				uom: frm.doc.uom,
				production_detail: frm.doc.production_detail,
				dependent_attr_mapping: frm.doc.dependent_attribute_mapping,
				ppo: frm.doc.production_order,
			},
			callback: (r) => {
				if (frm.item) {
					frm.item.load_data(r.message);
					if (frm.doc.production_order) {
						frm.item.show_inputs();
						frm.item.load_data(r.message);
					}
				}
			},
		});
	},
	calculate_bom(frm) {
		const run = () => {
			frappe.call({
				method: "yrp_essdee.yrp_essdee.doctype.lot.lot.calculate_bom",
				args: {
					lot_name: frm.doc.name,
				},
				freeze: true,
				freeze_message: __("Calculating BOM"),
				callback: (r) => {
					if (!r.exc) {
						const result = r.message || {};
						frappe.show_alert({
							message: __(
								"BOM calculated: {0} major rows, {1} accessory rows",
								[result.major_rows || 0, result.accessory_rows || 0]
							),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
			});
		};

		if (frm.is_dirty()) {
			frm.save().then(run);
		} else {
			run();
		}
	},
});
