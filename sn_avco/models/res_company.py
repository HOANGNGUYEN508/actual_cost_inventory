from odoo import models, api # type: ignore
import logging
import json

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _setup_protected_categories(self):
        """Set property_cost_method and real_time valuation for protected categories
        
        This method is called:
        - When creating a new company (via create method with postcommit)
        - During module installation (via post_init_hook)
        - After fiscal localization is configured (via res.config.settings)
        """
        self.ensure_one()
        company = self
        
        # Get all protected categories
        categories = {
            'standard': self.env.ref('sn_avco.product_category_account_standard', raise_if_not_found=False),
            'standard_manual': self.env.ref('sn_avco.product_category_account_standard_manual', raise_if_not_found=False),
            'fifo': self.env.ref('sn_avco.product_category_account_fifo', raise_if_not_found=False),
            'fifo_manual': self.env.ref('sn_avco.product_category_account_fifo_manual', raise_if_not_found=False),
            'avco': self.env.ref('sn_avco.product_category_account_avco', raise_if_not_found=False),
            'avco_manual': self.env.ref('sn_avco.product_category_account_avco_manual', raise_if_not_found=False),
            'sn_avco': self.env.ref('sn_avco.product_category_account_sn_avco', raise_if_not_found=False),
            'sn_avco_manual': self.env.ref('sn_avco.product_category_account_sn_avco_manual', raise_if_not_found=False),
        }
        
        # Define batches for processing
        # Format: (cost_method, [category_keys], enable_realtime)
        batches = [
            ('standard', ['standard_manual'], False),
            ('standard', ['standard'], True),
            ('fifo', ['fifo_manual', 'sn_avco_manual'], False),
            ('fifo', ['fifo', 'sn_avco'], True),
            ('average', ['avco_manual'], False),
            ('average', ['avco'], True),
        ]
        
        # Determine if we should check stock accounts in parent's context
        check_company = company
        if company.parent_id and not self.env['account.account'].with_context(
            allowed_company_ids=[company.id]
        ).search([], limit=1):
            check_company = company.parent_id
        
        # Check fiscal localization status
        effective_company = company
        if company.parent_id and not company.account_fiscal_country_id:
            effective_company = company.parent_id
        
        has_fiscal = bool(effective_company.account_fiscal_country_id)
        is_anglo_saxon = effective_company.anglo_saxon_accounting
        
        # Check if accounts exist
        has_accounts = False
        if has_fiscal:
            company_accounts = self.env['account.account'].with_context(
                allowed_company_ids=[company.id]
            ).search([], limit=1)
            has_accounts = bool(company_accounts)
            
            if not has_accounts and company.parent_id:
                parent_accounts = self.env['account.account'].with_context(
                    allowed_company_ids=[company.parent_id.id]
                ).search([], limit=1)
                if parent_accounts:
                    has_accounts = True
        
        # Determine if real-time valuation can be enabled
        can_enable_realtime = has_fiscal and is_anglo_saxon and has_accounts
        
        # Log fiscal status (only if not ready for real-time)
        if not has_fiscal:
            if company.parent_id:
                _logger.info(
                    f"Company '{company.name}' (child of '{company.parent_id.name}') has no fiscal localization set "
                    f"(neither on itself nor inherited from parent). Real-time valuation will not be enabled."
                )
            else:
                _logger.info(
                    f"Company '{company.name}' has no fiscal localization set. "
                    f"Real-time valuation will not be enabled. Set fiscal localization in Accounting settings to enable it."
                )
        elif not is_anglo_saxon:
            _logger.info(
                f"Company '{company.name}' uses Continental Accounting. "
                f"Real-time valuation requires Anglo-Saxon Accounting and will not be enabled."
            )
        elif not has_accounts:
            _logger.info(
                f"Company '{company.name}' has fiscal localization set but chart of accounts not yet loaded. "
                f"Real-time valuation will be enabled later when accounts are available."
            )
        
        # Process each batch
        for cost_method, cat_keys, enable_realtime in batches:
            # Collect categories for this batch
            batch_categories = self.env['product.category']
            for key in cat_keys:
                if categories[key]:
                    batch_categories |= categories[key]
            
            if not batch_categories:
                continue
            
            # For categories that should have real-time valuation (enable_realtime=True)
            if enable_realtime:
                if can_enable_realtime:
                    # Check each category for stock accounts
                    check_env = self.env(context=dict(
                        self.env.context,
                        allowed_company_ids=[check_company.id]
                    ))
                    
                    for category in batch_categories:
                        cat_check = category.with_env(check_env)
                        has_stock_accounts = (
                            cat_check.property_stock_account_input_categ_id and
                            cat_check.property_stock_account_output_categ_id and
                            cat_check.property_stock_valuation_account_id
                        )
                        
                        # Always set cost method
                        self._set_company_dependent_field_jsonb(
                            'product_category',
                            category.id,
                            'property_cost_method',
                            cost_method,
                            company.id
                        )
                        
                        if has_stock_accounts:
                            # Set real_time valuation
                            self._set_company_dependent_field_jsonb(
                                'product_category',
                                category.id,
                                'property_valuation',
                                'real_time',
                                company.id
                            )
                        else:
                            # Set manual_periodic if stock accounts missing
                            self._set_company_dependent_field_jsonb(
                                'product_category',
                                category.id,
                                'property_valuation',
                                'manual_periodic',
                                company.id
                            )
                            
                            missing = []
                            if not cat_check.property_stock_account_input_categ_id:
                                missing.append('stock input account')
                            if not cat_check.property_stock_account_output_categ_id:
                                missing.append('stock output account')
                            if not cat_check.property_stock_valuation_account_id:
                                missing.append('stock valuation account')
                            
                            _logger.warning(
                                f"⚠️ Cannot enable real_time valuation for category '{category.name}' "
                                f"in company '{company.name}'. Missing: {', '.join(missing)}"
                            )
                else:
                    # Conditions not met for real-time - set to manual_periodic
                    for category in batch_categories:
                        self._set_company_dependent_field_jsonb(
                            'product_category',
                            category.id,
                            'property_cost_method',
                            cost_method,
                            company.id
                        )
                        self._set_company_dependent_field_jsonb(
                            'product_category',
                            category.id,
                            'property_valuation',
                            'manual_periodic',
                            company.id
                        )
            else:
                # Manual categories - only set cost method
                for category in batch_categories:
                    self._set_company_dependent_field_jsonb(
                        'product_category',
                        category.id,
                        'property_cost_method',
                        cost_method,
                        company.id
                    )

    def _set_company_dependent_field_jsonb(self, table_name, record_id, field_name, value, company_id):
        """Set company-dependent field value by updating JSONB column
        
        This bypasses ORM write() and its constraints by directly updating the JSONB column.
        In Odoo 18, company-dependent fields are stored as JSONB with format: {company_id: value}
        """
        company_id_str = str(company_id)
        
        # Read current JSONB value
        self.env.cr.execute(f"""
            SELECT {field_name}
            FROM {table_name}
            WHERE id = %s
        """, (record_id,))
        
        result = self.env.cr.fetchone()
        if not result:
            _logger.warning(f"Record {record_id} not found in {table_name}")
            return
        
        # Get current JSONB dict (or create new one if None)
        current_jsonb = result[0] or {}
        
        # Check if value already set correctly
        if current_jsonb.get(company_id_str) == value:
            return  # No change needed
        
        # Update the JSONB dict for this company
        current_jsonb[company_id_str] = value
        
        # Write back to database
        self.env.cr.execute(f"""
            UPDATE {table_name}
            SET {field_name} = %s
            WHERE id = %s
        """, (json.dumps(current_jsonb), record_id))
        
        # Invalidate ORM cache so it reads the new value
        self.env['product.category'].invalidate_model([field_name])

    def _setup_protected_categories_postcommit(self):
        """Setup protected categories after transaction commit
        
        This method is called via postcommit callback to ensure:
        - All enrichment modules have finished
        - Fiscal settings are fully visible
        - Chart of accounts is loaded
        """
        with self.env.registry.cursor() as cr:
            # Create new environment with the new cursor
            env = api.Environment(cr, self.env.uid, self.env.context)
            
            for company_id in self.ids:
                try:
                    # Fetch fresh company record in new transaction
                    company = env['res.company'].browse(company_id)
                    company.sudo()._setup_protected_categories()
                        
                except Exception as e:
                    _logger.error(
                        f"Error in post-commit setup for company {company_id}: {e}",
                        exc_info=True
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Set property_cost_method for protected categories when creating a new company"""
        companies = super().create(vals_list)
        
        # Schedule post-commit callback for ALL companies
        # This ensures all modules have finished their setup
        if companies:
            self.env.cr.postcommit.add(
                companies._setup_protected_categories_postcommit
            )
        
        return companies