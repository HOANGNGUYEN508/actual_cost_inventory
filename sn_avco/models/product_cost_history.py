from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductCostHistory(models.Model):
    _inherit = "product.cost.history"
    
    cost_method = fields.Selection(
        selection_add=[("sn_avco", "SN AVCO")],
    )
    
    def _get_cost_method(self, product):
        cost_method = super(ProductCostHistory, self)._get_cost_method(product)

        # Check if this is Serial Number AVCO
        if cost_method == "fifo" and product.lot_valuated:
            return "sn_avco"

        return cost_method