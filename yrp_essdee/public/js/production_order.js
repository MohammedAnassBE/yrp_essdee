// yrp_essdee — cap Production Order's items table at 1 row.
// Mirrors the server-side single-item rule in
// yrp_essdee.overrides.production_order.enforce_single_item.

frappe.ui.form.on("Production Order", {
	refresh(frm) {
		_apply_single_row_lock(frm);
	},
	production_order_details_add(frm) {
		_apply_single_row_lock(frm);
	},
	production_order_details_remove(frm) {
		_apply_single_row_lock(frm);
	},
});

function _apply_single_row_lock(frm) {
	const rows = (frm.doc.production_order_details || []).length;
	const grid = frm.fields_dict.production_order_details && frm.fields_dict.production_order_details.grid;
	if (!grid) return;
	// Disallow adding more rows once one exists
	frm.set_df_property("production_order_details", "cannot_add_rows", rows >= 1);
	grid.refresh();
}
