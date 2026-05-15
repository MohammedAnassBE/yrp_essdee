frappe.ui.form.on("Work Order", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}
		frm.add_custom_button(__("Calculate"), () => {
			run_after_save(frm, () => open_lot_order_dialog(frm));
		});
	},
});

function run_after_save(frm, action) {
	if (frm.is_dirty()) {
		frm.save().then(action);
		return;
	}
	action();
}

function open_lot_order_dialog(frm) {
	frappe.call({
		method: "yrp_essdee.yrp_essdee.api.work_order.get_lot_order_details",
		args: {
			work_order: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Loading Lot Order Details"),
		callback(r) {
			const payload = r.message || {};
			const rows = payload.rows || [];
			if (!rows.length) {
				frappe.msgprint(__("No Lot Order Details found."));
				return;
			}
			show_lot_order_dialog(frm, payload);
		},
	});
}

function show_lot_order_dialog(frm, payload) {
	const dialog = new frappe.ui.Dialog({
		title: __("Lot Order Details"),
		size: "extra-large",
		fields: [
			{
				fieldname: "lot_order_header",
				fieldtype: "HTML",
				options: render_lot_order_header(payload),
			},
			{
				fieldname: "lot_order_html",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Submit"),
		primary_action() {
			const lot_order_payload = collect_lot_order_payload(dialog);
			if (!has_qty(lot_order_payload)) {
				frappe.msgprint(__("Enter Qty greater than zero."));
				return;
			}
			dialog.hide();
			calculate_deliverables(frm, lot_order_payload);
		},
	});
	dialog.show();
	mount_lot_order_details(dialog, payload);
}

function render_lot_order_header(payload) {
	return `
		<div class="text-muted small" style="margin-bottom: 10px;">
			${escape_html(payload.lot_name || payload.lot || "")}
			${payload.process_name ? " / " + escape_html(payload.process_name) : ""}
		</div>
	`;
}

function mount_lot_order_details(dialog, payload) {
	if (!frappe.production?.ui?.CutPlanItems) {
		frappe.throw(__("Lot Order Details component is not loaded. Please refresh and try again."));
	}

	const wrapper = dialog.fields_dict.lot_order_html.wrapper;
	$(wrapper).html(`<div class="yrp-essdee-work-order-lot-items"></div>`);
	const target = $(wrapper).find(".yrp-essdee-work-order-lot-items").get(0);
	dialog.order_detail = new frappe.production.ui.CutPlanItems(target);
	dialog.order_detail.load_data(payload.order_item_details || [], 0);
}

function collect_lot_order_payload(dialog) {
	return dialog.order_detail ? dialog.order_detail.get_items() || [] : [];
}

function has_qty(lot_order_payload) {
	return (lot_order_payload || []).some((group) => {
		return (group.items || []).some((item) => {
			return Object.values(item.values || {}).some((value) => flt(value.qty) > 0);
		});
	});
}

function calculate_deliverables(frm, lot_order_payload) {
	frappe.call({
		method: "yrp_essdee.yrp_essdee.api.work_order.calculate_deliverables",
		args: {
			work_order: frm.doc.name,
			rows: JSON.stringify(lot_order_payload),
		},
		freeze: true,
		freeze_message: __("Calculating Deliverables"),
		callback(r) {
			if (r.exc) {
				return;
			}
			const result = r.message || {};
			frappe.show_alert({
				message: __("Calculated {0} deliverable rows and {1} receivable rows", [
					result.deliverables || 0,
					result.receivables || 0,
				]),
				indicator: "green",
			});
			frm.reload_doc();
		},
	});
}

function escape_html(value) {
	return frappe.utils.escape_html(String(value || ""));
}
