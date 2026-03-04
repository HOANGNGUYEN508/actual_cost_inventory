from odoo import models, fields, api  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    cost_history_ids = fields.One2many(
        "product.cost.history", "product_id", string="Cost History",
        help="History of standard_price changes for this variant"
    )

    def write(self, vals):
        # Check if standard_price is being changed manually or via internal process
        if "standard_price" not in vals or self.env.context.get("skip_cost_history_log"):
            return super(ProductProduct, self).write(vals)
      
        # Capture old prices before the change
        products_old_prices = {}
        for product in self:
            products_old_prices[product.id] = {
                "old_price": float(product.standard_price or 0.0),
                "product": product,
            }
        
        # Perform the actual write
        result = super(ProductProduct, self).write(vals)
        
        # After write, log the manual changes
        for product_id, data in products_old_prices.items():
            try:
                product = data["product"]
                if not product.exists():
                    continue
                
                old_price = data["old_price"]
                new_price = float(product.standard_price or 0.0)
                
                # Skip if price didn"t actually change
                if abs(new_price - old_price) < 0.01:
                    continue
                
                # Compute current stock
                quants = self.env["stock.quant"].search([
                    ("product_id", "=", product.id),
                    ("quantity", ">", 0),
                    ("location_id.usage", "=", "internal"),
                ])
                total_qty = sum(quants.mapped("quantity")) if quants else 0.0
                total_value = new_price * total_qty
                
                # Log as manual change
                self.env["product.cost.history"].log_cost_change(
                    product=product,
                    old_price=old_price,
                    new_price=new_price,
                    reason="manual",
                    reference="Manual Price Update",
                    units_in_stock=total_qty,
                    total_value=total_value,
                )
                
            except Exception as e:
                _logger.exception(
                    "Error logging manual price change for product %s: %s",
                    product_id, e
                )
        
        return result
    
    def action_view_cost_history(self):
        """Smart button to view THIS variant"s cost history"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": f"Cost History: {self.display_name}",
            "res_model": "product.cost.history",
            "view_mode": "list,form,graph,pivot",
            "domain": [("product_id", "=", self.id)],
            "context": {
                "default_product_id": self.id,
                "default_product_tmpl_id": self.product_tmpl_id.id,
            },
        }

    def action_view_serial_costs(self):
        """Smart button to view all serials for THIS variant with their costs"""
        self.ensure_one()

        lots = self.env["stock.lot"].search([
            ("product_id", "=", self.id),
        ])

        return {
            "type": "ir.actions.act_window",
            "name": f"Serial Numbers: {self.display_name}",
            "res_model": "stock.lot",
            "view_mode": "list,form",
            "domain": [("id", "in", lots.ids)],
            "context": {
                "search_default_product_id": self.id,
                "default_product_id": self.id,
            },
        }