from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductProduct(models.Model):
    _inherit = "product.product"
    
    technical_categ_id = fields.Many2one(
        "product.category.technical",
        string="Technical Category",
        related="product_tmpl_id.technical_categ_id",
        store=True,
        readonly=False,
        help="Technical category inherited from product template"
    )
