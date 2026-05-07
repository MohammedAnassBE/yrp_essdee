// yrp_essdee main bundle — registers Vue wrappers under frappe.production.ui.*
// mirroring production_api's namespace so the verbatim-ported Vue components
// and JS work without rebinding.

import {
	LotOrderWrapper,
	CutPlanItemsWrapper,
	OCRDetailWrapper,
	CadDetailWrapper,
	AlternativeDetailWrapper,
} from "./Lot";

import {
	CombinationItemDetailWrapper,
	EmblishmentDetailsWrapper,
	CuttingItemDetailWrapper,
	ClothAccessoryWrapper,
	ClothAccessoryCombinationWrapper,
	AccessoryItemsWrapper,
	BundleGroupWrapper,
} from "./Item_Po_detail";

frappe.provide("frappe.production");
frappe.provide("frappe.production.ui");

// Lot
frappe.production.ui.LotOrder = LotOrderWrapper;
frappe.production.ui.CutPlanItems = CutPlanItemsWrapper;
frappe.production.ui.OCRDetail = OCRDetailWrapper;
frappe.production.ui.CadDetail = CadDetailWrapper;
frappe.production.ui.AlternativeDetail = AlternativeDetailWrapper;

// Item Production Detail (tabs 2–8)
frappe.production.ui.CombinationItemDetail = CombinationItemDetailWrapper;
frappe.production.ui.EmblishmentDetails = EmblishmentDetailsWrapper;
frappe.production.ui.CuttingItemDetail = CuttingItemDetailWrapper;
frappe.production.ui.ClothAccessory = ClothAccessoryWrapper;
frappe.production.ui.ClothAccessoryCombination = ClothAccessoryCombinationWrapper;
frappe.production.ui.AccessoryItems = AccessoryItemsWrapper;
frappe.production.ui.BundleGroup = BundleGroupWrapper;

// Backward-compatible alias used by earlier yrp_essdee code paths.
frappe.provide("frappe.yrp_essdee");
frappe.provide("frappe.yrp_essdee.lot");
frappe.yrp_essdee.lot.LotOrder = LotOrderWrapper;
frappe.yrp_essdee.lot.CutPlanItems = CutPlanItemsWrapper;
frappe.yrp_essdee.lot.OCRDetail = OCRDetailWrapper;
frappe.yrp_essdee.lot.CadDetail = CadDetailWrapper;
frappe.yrp_essdee.lot.AlternativeDetail = AlternativeDetailWrapper;
