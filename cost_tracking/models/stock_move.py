from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        # Gather product ids involved and capture old standard_price
        products_data = {}
        for move in self:
            pid = move.product_id.id
            if not pid:
                continue
            if pid not in products_data:
                products_data[pid] = {
                    "move_ids": [],
                    "old_price": float(move.product_id.standard_price or 0.0),
                }
            products_data[pid]["move_ids"].append(move.id)

        # Process moves normally
        result = super(StockMove, self.with_context(skip_cost_history_log=True))._action_done(cancel_backorder=cancel_backorder)

        # After super(), for each product create a history log
        for product_id, data in products_data.items():
            try:
                moves = self.env["stock.move"].browse(data["move_ids"]).exists()
                if not moves:
                    _logger.warning(
                        "StockMove._action_done: moves %s no longer exist after processing, skipping history",
                        data["move_ids"]
                    )
                    continue

                # Choose the first done move for reasoning (prefer a "done" state move)
                done_moves = moves.filtered(lambda m: m.state == "done")
                if not done_moves:
                    _logger.warning(
                        "StockMove._action_done: no done moves found for product %s, skipping history",
                        product_id
                    )
                    continue

                first_move = done_moves[:1]
                product = first_move.product_id
                if not product:
                    _logger.warning(
                        "StockMove._action_done: product %s not found, skipping history", product_id
                    )
                    continue

                # Reference (prefer move.reference then picking name)
                reference = first_move.reference or (first_move.picking_id and first_move.picking_id.name) or False

                # Decide reason based on move type and location
                reason = "adjustment"  # default

                # Inventory adjustments use "inventory" location type
                is_inventory_adjustment = (
                    first_move.location_id.usage == "inventory" or 
                    first_move.location_dest_id.usage == "inventory" or
                    (reference and "Product Quantity Updated" in reference)
                )
                
                if is_inventory_adjustment:
                    reason = "adjustment"
                    
                elif first_move._is_in():
                    # Check if it"s a customer return (goods coming back from customer)
                    if first_move._is_returned("in"): 
                        reason = "return"
                    else:
                        reason = "receipt"
                        
                elif first_move._is_out():
                    # Check if it"s a return to supplier
                    if first_move._is_returned("out"):
                        reason = "return"
                    else:
                        reason = "delivery"

                # Compute current internal stock for the product AFTER moves were processed
                quants = self.env["stock.quant"].sudo().search([
                    ("product_id", "=", product.id),
                    ("quantity", ">", 0),
                    ("location_id.usage", "=", "internal"),
                    ("company_id", "=", first_move.company_id.id),
                ])
                total_qty = sum(quants.mapped("quantity")) if quants else 0.0
                new_price = float(product.standard_price or 0.0)
                total_value = new_price * total_qty

                # Call the centralized logger (creates the history record)
                self.env["product.cost.history"].sudo().log_cost_change(
                    product=product,
                    old_price=data.get("old_price", 0.0),
                    new_price=new_price,
                    reason=reason,
                    reference=reference,
                    units_in_stock=total_qty,
                    total_value=total_value,
                    company=first_move.company_id,
                )

            except Exception as e:
                _logger.exception(
                    "Error creating product.cost.history for product %s after _action_done: %s",
                    product_id, e
                )

        return result
