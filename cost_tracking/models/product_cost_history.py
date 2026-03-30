from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from datetime import datetime, timedelta, time
import pytz  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class ProductCostHistory(models.Model):
    _name = "product.cost.history"
    _description = "Product Cost History"
    _order = "create_date desc"
    _rec_name = "display_name"

    display_name = fields.Char(related="product_id.name", string="Template name", store=False)

    # Cost change tracking
    old_price = fields.Monetary("Old Cost", currency_field="currency_id", aggregator="avg")
    new_price = fields.Monetary("New Cost", currency_field="currency_id", aggregator="avg")

    # Why it changed (the EVENT, not the calculation method)
    reason = fields.Selection([
        ("receipt", "Goods Receipt"),
        ("delivery", "Goods Delivery"),
        ("adjustment", "Inventory Adjustment"),
        ("return", "Customer Return"),
        ("manual", "Manual Update"),
    ], string="Reason", required=True)
    reference = fields.Char("Reference", help="Stock picking or document reference")

    # Context at time of change
    units_in_stock = fields.Float("Units in Stock", help="Number of units for this variant", aggregator="avg")
    total_value = fields.Monetary("Total Inventory Value", currency_field="currency_id", aggregator="avg")

    # Cost method used - NEW: SN AVCO for FIFO + lot_valuated
    cost_method = fields.Selection([
        ("standard", "Standard Price"),
        ("average", "AVCO"),
        ("fifo", "FIFO"),
    ], string="Cost Method", help="Cost calculation method apply to product at time of change")

    # Relationships - ALWAYS link to both product and template
    product_id = fields.Many2one(
        "product.product", "Product Variant", required=True,
        help="The specific variant whose standard_price changed"
    )
    product_tmpl_id = fields.Many2one(
        "product.template", "Product Template", required=True,
        help="Template of the variant (for filtering/grouping)"
    )

    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    user_id = fields.Many2one("res.users", "Changed By", default=lambda self: self.env.user)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
    )

    # Computed fields
    price_change = fields.Monetary(
        "Price Change", compute="_compute_price_change", currency_field="currency_id", store=True, aggregator="avg"
    )
    price_change_percent = fields.Float("Change %", compute="_compute_price_change_percent", store=False, aggregator="avg")

    # Date filters for reporting
    is_last_7_days = fields.Boolean("Last 7 Days", search="_search_last_7_days", store=False)
    is_last_30_days = fields.Boolean("Last 30 Days", search="_search_last_30_days", store=False)
    is_this_month = fields.Boolean("This Month", search="_search_this_month", store=False)
    is_this_year = fields.Boolean("This Year", search="_search_this_year", store=False)
    is_increase = fields.Boolean("Price Increased", search="_search_is_increase", store=False)
    is_decrease = fields.Boolean("Price Decreased", search="_search_is_decrease", store=False)
    is_no_change = fields.Boolean("No Price Change", search="_search_is_no_change", store=False)
    
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
    )

    @api.depends("old_price", "new_price")
    def _compute_price_change(self):
        """Calculate price change amount and percentage"""
        for record in self:
            record.price_change = record.new_price - record.old_price
                
    @api.depends("old_price", "new_price")
    def _compute_price_change_percent(self):
        """Calculate price change percent amount and percentage"""
        for record in self:
            if record.old_price:
                record.price_change_percent = (
                    record.new_price - record.old_price
                ) / record.old_price
            else:
                record.price_change_percent = 0.0

    def _build_utc_start_for_date(self, start_date):
        """Return a server-UTC datetime string for the start of start_date in user tz."""
        tz_name = self.env.context.get("tz") or self.env.user.tz or "UTC"
        user_tz = pytz.timezone(tz_name)
        local_dt = user_tz.localize(datetime.combine(start_date, time.min))
        utc_dt = local_dt.astimezone(pytz.UTC)
        return fields.Datetime.to_string(utc_dt)

    def _search_last_7_days(self, operator, value):
        today = fields.Date.context_today(self)
        start_date = today - timedelta(days=7)
        start_dt_str = self._build_utc_start_for_date(start_date)
        if operator == "!=":
            value = not value
        if value:
            return [("create_date", ">=", start_dt_str)]
        else:
            return [("create_date", "<", start_dt_str)]

    def _search_last_30_days(self, operator, value):
        today = fields.Date.context_today(self)
        start_date = today - timedelta(days=30)
        start_dt_str = self._build_utc_start_for_date(start_date)
        if operator == "!=":
            value = not value
        if value:
            return [("create_date", ">=", start_dt_str)]
        else:
            return [("create_date", "<", start_dt_str)]

    def _search_this_month(self, operator, value):
        today = fields.Date.context_today(self)
        start_date = today.replace(day=1)
        start_dt_str = self._build_utc_start_for_date(start_date)
        if operator == "!=":
            value = not value
        if value:
            return [("create_date", ">=", start_dt_str)]
        else:
            return [("create_date", "<", start_dt_str)]

    def _search_this_year(self, operator, value):
        today = fields.Date.context_today(self)
        start_date = today.replace(month=1, day=1)
        start_dt_str = self._build_utc_start_for_date(start_date)
        if operator == "!=":
            value = not value
        if value:
            return [("create_date", ">=", start_dt_str)]
        else:
            return [("create_date", "<", start_dt_str)]

    def _search_is_increase(self, operator, value):
        if operator == "!=":
            value = not value
        
        self.env.cr.execute("""
            SELECT id 
            FROM product_cost_history 
            WHERE (new_price - old_price) > 0
        """)
        ids = [r[0] for r in self.env.cr.fetchall()]
        
        if value:
            return [("id", "in", ids if ids else [0])]
        else:
            return [("id", "not in", ids if ids else [0])]

    def _search_is_decrease(self, operator, value):
        if operator == "!=":
            value = not value
        
        self.env.cr.execute("""
            SELECT id 
            FROM product_cost_history 
            WHERE (new_price - old_price) < 0
        """)
        ids = [r[0] for r in self.env.cr.fetchall()]
        
        if value:
            return [("id", "in", ids if ids else [0])]
        else:
            return [("id", "not in", ids if ids else [0])]
        
    def _search_is_no_change(self, operator, value):
        if operator == "!=":
            value = not value
        
        self.env.cr.execute("""
            SELECT id 
            FROM product_cost_history 
            WHERE (new_price - old_price) = 0
        """)
        ids = [r[0] for r in self.env.cr.fetchall()]
        
        if value:
            return [("id", "in", ids if ids else [0])]
        else:
            return [("id", "not in", ids if ids else [0])]

    def _get_cost_method(self, product):
        return product.categ_id.property_cost_method or "standard"

    @api.model
    def log_cost_change(
        self, product, old_price, new_price, reason, reference=None, units_in_stock=0.0,
        total_value=0.0, company=None
    ):
        if not product or len(product) != 1:
            _logger.warning("log_cost_change requires exactly one product, got: %s", product)
            return self.env["product.cost.history"]

        try:
            # Get cost method - special handling for SN AVCO
            cost_method = self._get_cost_method(product)

            # ALWAYS create history entry for complete audit trail
            history = self.sudo().create({
                "product_id": product.id,
                "product_tmpl_id": product.product_tmpl_id.id,
                "old_price": old_price,
                "new_price": new_price,
                "reason": reason,
                "reference": reference,
                "units_in_stock": units_in_stock,
                "total_value": total_value,
                "cost_method": cost_method,
                "company_id": (company or product.company_id or self.env.company).id,
            })

            # Log based on whether price actually changed (debugging purposes)
            # currency = product.currency_id or self.env.company.currency_id
            # price_changed = abs(new_price - old_price) > 0.01

            # if price_changed:
            #     _logger.info(
            #         "Cost history: %s | %s → %s | reason: %s | method: %s | ref: %s",
            #         product.display_name, currency.format(old_price), currency.format(new_price),
            #         reason, cost_method, reference or "N/A"
            #     )
            # else:
            #     _logger.info(
            #         "Cost history: %s | %s (no change) | reason: %s | method: %s | ref: %s",
            #         product.display_name, currency.format(old_price), reason, cost_method,
            #         reference or "N/A"
            #     )

            return history

        except Exception as e:
            _logger.error(
                "Error logging cost history for %s: %s", product.display_name, str(e), exc_info=True
            )
            return self.env["product.cost.history"]
