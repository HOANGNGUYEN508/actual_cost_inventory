from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore


class ProductCategory(models.Model):
    _inherit = "product.category"

    def _check_protected_modify(self):
        if self.env.context.get('bypass_protection') and self.env.context['bypass_protection'] == True:
            return
        protected_xmlids = [
            "sn_avco.product_category_account_standard",
            "sn_avco.product_category_account_fifo",
            "sn_avco.product_category_account_avco",
            "sn_avco.product_category_account_sn_avco",
            "sn_avco.product_category_account_standard_manual",
            "sn_avco.product_category_account_fifo_manual",
            "sn_avco.product_category_account_avco_manual",
            "sn_avco.product_category_account_sn_avco_manual",
        ]
        protected_ids = set()
        for xmlid in protected_xmlids:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec:
                protected_ids.add(rec.id)
        # if any of current records is protected -> raise
        if protected_ids.intersection(self.ids):
            raise UserError("This product category is protected by the module and cannot be modified or deleted.")
                        
    def write(self, vals):
        self._check_protected_modify()        
        return super().write(vals)

    def unlink(self):
        self._check_protected_modify()
        return super().unlink()
        