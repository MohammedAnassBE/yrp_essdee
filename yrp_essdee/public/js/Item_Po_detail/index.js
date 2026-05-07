// Item Production Detail Vue wrappers — verbatim port of production_api's
// vue_plugins.js wrappers for the IPD form.

import { createApp } from "vue";
import CombinationItemDetail from "./CombinationItemDetail.vue";
import EmblishmentDetails from "./EmblishmentDetails.vue";
import CuttingItemDetail from "./CuttingItemDetail.vue";
import ClothAccessory from "./ClothAccessory.vue";
import ClothAccessoryCombination from "./ClothAccessoryCombination.vue";
import AccessoryItems from "./AccessoryItems.vue";
import BundleGroup from "./BundleGroup.vue";

export class CombinationItemDetailWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(CombinationItemDetail); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_data(JSON.parse(JSON.stringify(items))); }
	set_attributes() { this.vue.set_attributes(); }
	get_data() { return JSON.parse(JSON.stringify(this.vue.get_data())); }
}

export class EmblishmentDetailsWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(EmblishmentDetails); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_items(JSON.parse(JSON.stringify(items))); }
	get_items() { return JSON.parse(JSON.stringify(this.vue.get_items())); }
}

export class CuttingItemDetailWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(CuttingItemDetail); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_data(items); }
	set_attributes() { this.vue.set_attributes(); }
	get_data() { return JSON.parse(JSON.stringify(this.vue.get_data())); }
}

export class ClothAccessoryWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(ClothAccessory); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_data(items); }
	set_attributes() { this.vue.set_attributes(); }
	get_data() { return JSON.parse(JSON.stringify(this.vue.get_data())); }
}

export class ClothAccessoryCombinationWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(ClothAccessoryCombination); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_data(items); }
	set_attributes() { this.vue.set_attributes(); }
	get_data() { return JSON.parse(JSON.stringify(this.vue.get_data())); }
}

export class AccessoryItemsWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_body(); }
	make_body() { this.app = createApp(AccessoryItems); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	load_data(items) { this.vue.load_data(JSON.parse(items)); }
	get_data() { return JSON.parse(JSON.stringify(this.vue.get_items())); }
}

export class BundleGroupWrapper {
	constructor(wrapper) { this.$wrapper = $(wrapper); this.make_app(); }
	make_app() { this.app = createApp(BundleGroup); SetVueGlobals(this.app); this.vue = this.app.mount(this.$wrapper.get(0)); }
	get_items() { return this.vue.get_items(); }
	load_data(data) { if (this.vue.load_data) this.vue.load_data(data); }
}
