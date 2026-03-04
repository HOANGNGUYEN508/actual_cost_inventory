from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        # Early exit if no SN AVCO-related changes
        if "categ_id" not in vals and not any(
            k in vals for k in ("tracking", "type", "lot_valuated")
        ):
            return super().write(vals)

        # Cache SN AVCO category lookup for entire write operation
        sn_avco_categ = self.env.ref("sn_avco.product_category_account_sn_avco", raise_if_not_found=False)
        sn_avco_manual_categ = self.env.ref("sn_avco.product_category_account_sn_avco_manual", raise_if_not_found=False)
        
        # Collect valid SN AVCO category IDs
        sn_avco_ids = set()
        if sn_avco_categ:
            sn_avco_ids.add(sn_avco_categ.id)
        if sn_avco_manual_categ:
            sn_avco_ids.add(sn_avco_manual_categ.id)
        
        # Early exit if no SN AVCO categories exist
        if not sn_avco_ids:
            return super().write(vals)
        
        # Check if moving TO any SN AVCO category
        if "categ_id" in vals and vals["categ_id"] in sn_avco_ids:
            self._validate_sn_avco_requirements(vals)
        
        # Check if ALREADY in any SN AVCO category and trying to change locked fields
        current_sn_avco_products = self.filtered(lambda t: t.categ_id.id in sn_avco_ids)
        if current_sn_avco_products and not self.env.context.get('force_sn_avco'):
            self._validate_sn_avco_locks(current_sn_avco_products, vals)
        
        return super().write(vals)

    def _validate_sn_avco_requirements(self, vals):
        """Validate prerequisites when moving products to SN AVCO category"""
        invalid_products = []
        
        for template in self:
            tracking = vals.get("tracking", template.tracking)
            product_type = vals.get("type", template.type)
            
            issues = []
            if tracking != "serial":
                issues.append("Tracking must be 'By Unique Serial Number'")
            if product_type != "consu":
                issues.append("Product Type must be 'Consumable'")
            
            if issues:
                invalid_products.append((template.name, issues))
        
        if invalid_products:
            error_lines = []
            for name, issues in invalid_products:
                error_lines.append(f"\n{name}:")
                error_lines.extend(f"  • {issue}" for issue in issues)
            
            raise ValidationError(
                "Cannot move products to SN AVCO category.\n"
                "".join(error_lines)
            )

    def _validate_sn_avco_locks(self, sn_avco_products, vals):
        """Validate that locked fields aren't changed for SN AVCO products"""
        product_names = ", ".join(sn_avco_products.mapped("name"))
        
        # Check tracking lock
        if "tracking" in vals and vals["tracking"] != "serial":
            raise ValidationError(
                f"Cannot change Tracking for SN AVCO products: {product_names}\n\n"
                "Products in SN AVCO category must maintain Serial Number tracking."
            )
        
        # Check type lock
        if "type" in vals and vals["type"] != "consu":
            raise ValidationError(
                f"Cannot change Product Type for SN AVCO products: {product_names}\n\n"
                "Products in SN AVCO category must remain Consumable type."
            )
        
        # Check lot_valuated lock
        if "lot_valuated" in vals and not vals["lot_valuated"]:
            raise ValidationError(
                f"Cannot disable Lot Valuated for SN AVCO products: {product_names}"
            )
    
    @api.onchange("categ_id")
    def _onchange_categ_sn_avco(self):
        """Auto-enable lot_valuated when any SN AVCO category is selected"""
        sn_avco_categ = self.env.ref("sn_avco.product_category_account_sn_avco", raise_if_not_found=False)
        sn_avco_manual_categ = self.env.ref("sn_avco.product_category_account_sn_avco_manual", raise_if_not_found=False)

        is_sn_avco = False
        if sn_avco_categ and self.categ_id == sn_avco_categ:
            is_sn_avco = True
        elif sn_avco_manual_categ and self.categ_id == sn_avco_manual_categ:
            is_sn_avco = True
        
        if is_sn_avco:
            self.lot_valuated = True