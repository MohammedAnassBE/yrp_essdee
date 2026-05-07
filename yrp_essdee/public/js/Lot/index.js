// Lot Vue wrappers — yrp_essdee.

import { createApp } from "vue";
import LotOrder from "./components/LotOrder.vue";
import CutPlanItems from "./components/CutPlanItems.vue";
import OCRDetail from "./components/OCRDetail.vue";
import CadDetail from "./components/CadDetail.vue";
import AlternativeDetail from "./components/AlternativeDetail.vue";

export class LotOrderWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() {
		this.app = createApp(LotOrder);
		SetVueGlobals(this.app);
		this.vue = this.app.mount(this.$wrapper.get(0));
	}
	get_data() { return JSON.parse(JSON.stringify(this.vue.list_item)); }
	show_inputs() { this.vue.show_add_items(); }
	load_data(item_details) { this.vue.load_data(JSON.parse(JSON.stringify(item_details))); }
}

export class CutPlanItemsWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() {
		this.app = createApp(CutPlanItems);
		SetVueGlobals(this.app);
		this.vue = this.app.mount(this.$wrapper.get(0));
	}
	load_data(items, t_and_a_len) { this.vue.load_data(JSON.parse(JSON.stringify(items)), t_and_a_len); }
	get_items() { return this.vue.get_items(); }
	update_status() { this.vue.update_docstatus(); }
}

export class OCRDetailWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() {
		this.app = createApp(OCRDetail);
		SetVueGlobals(this.app);
		this.vue = this.app.mount(this.$wrapper.get(0));
	}
}

export class CadDetailWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() {
		this.app = createApp(CadDetail);
		SetVueGlobals(this.app);
		this.vue = this.app.mount(this.$wrapper.get(0));
	}
	load_data(data) { this.vue.load_data(JSON.parse(JSON.stringify(data))); }
	get_data() { return this.vue.get_data(); }
}

export class AlternativeDetailWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() {
		this.app = createApp(AlternativeDetail);
		SetVueGlobals(this.app);
		this.vue = this.app.mount(this.$wrapper.get(0));
	}
}
