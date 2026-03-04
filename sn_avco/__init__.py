from . import models

def _hook_product_category(env):
    """Post-init hook to setup protected categories for ALL companies"""
    # Get all companies in the system
    companies = env['res.company'].search([])
    
    # Setup protected categories for each company
    for company in companies:
        company.sudo()._setup_protected_categories()