from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductCategoryTechnical(models.Model):
    _name = "product.category.technical"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Technical Product Category"
    _rec_name = "name"
    _parent_name = "parent_id"
    _parent_store = True

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, required=True)
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)
    parent_path = fields.Char(index=True)
    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True, recursive=True)

    # Relationship Attributes
    parent_id = fields.Many2one("product.category.technical", string="Parent Category", ondelete="cascade")
    child_ids = fields.One2many(
        "product.category.technical", "parent_id", string="Child Categories", copy=False
    )
    tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_category_technical_product_tag_rel",
        column1="category_technical_id",
        column2="tag_id",
        string="Tags",
        tracking=True,
		)

    @api.depends("name", "parent_id.display_name")
    def _compute_display_name(self):
        """Compute the complete hierarchical name"""
        for category in self:
            if category.parent_id:
                category.display_name = f"{category.parent_id.display_name} / {category.name}"
            else:
                category.display_name = category.name