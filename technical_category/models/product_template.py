from odoo import models, api, fields  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductTemplate(models.Model):
    _inherit = "product.template"

    technical_categ_id = fields.Many2one(
        "product.category.technical", string="Technical Category"
    )