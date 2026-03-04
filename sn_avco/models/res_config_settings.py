from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    def execute(self):
        """Override execute to enable real_time valuation after fiscal localization is installed"""
        company = self.company_id or self.env.company
        
        # Capture OLD values before super().execute() changes them
        old_fiscal = company.account_fiscal_country_id
        old_anglo = company.anglo_saxon_accounting
        
        # Execute the parent method (this saves the changes)
        res = super().execute()
        
        # Get NEW values after super().execute()
        new_fiscal = company.account_fiscal_country_id
        new_anglo = company.anglo_saxon_accounting
        
        # Check if fiscal-related settings actually changed
        fiscal_changed = old_fiscal != new_fiscal
        anglo_saxon_changed = old_anglo != new_anglo
        
        # Only re-run setup if fiscal-related settings actually changed
        if fiscal_changed or anglo_saxon_changed:
            if new_fiscal:
                company_accounts = self.env['account.account'].with_context(
                    allowed_company_ids=[company.id]
                ).search([], limit=1)
                
                if company_accounts:
                    # Get all companies that need setup: parent + all child companies
                    companies_to_setup = company
                    
                    # If this is a parent company, include all its children
                    # Children inherit fiscal settings from parent
                    child_companies = self.env['res.company'].search([
                        ('parent_id', '=', company.id)
                    ])
                    companies_to_setup |= child_companies
                    
                    _logger.info(
                        f"Fiscal settings changed for company '{company.name}'. "
                        f"Re-running protected categories setup for {len(companies_to_setup)} company(ies)..."
                    )
                    
                    # Run setup for parent and all children
                    for comp in companies_to_setup:
                        comp.sudo()._setup_protected_categories()
                else:
                    _logger.warning(
                        f"Fiscal localization configured for company '{company.name}', "
                        f"but chart of accounts not yet loaded. Real-time valuation will be "
                        f"enabled automatically once accounts are available."
                    )
        
        return res