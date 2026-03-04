from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductTemplate(models.Model):
    _inherit = "product.template"

    template_cost_history_ids = fields.One2many(
        "product.cost.history", "product_tmpl_id", string="All Cost History",
        help="Cost history for all variants of this template"
    )

    def action_view_template_cost_history(self):
        """Smart button to view cost history for ALL variants of this template"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": f"Cost History: {self.name}",
            "res_model": "product.cost.history",
            "view_mode": "list,form,graph,pivot",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "default_product_tmpl_id": self.id,
                "group_by": "product_id",
            },
        }

    def action_view_all_variants_cost(self):
        """Smart button to view all variants with their costs"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": f"Variant Costs: {self.name}",
            "res_model": "product.product",
            "view_mode": "list,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {
                "search_default_product_tmpl_id": self.id,
            },
        }