{
    "name": "SN AVCO",
    "category": "Sales",
    "summary": "Add another cost calculation method 'Serial Number AVCO'",
    "description":
    """
    - Product Category: Add another cost calculation method "Serial Number AVCO".
    - Product Template: Validate product settings for SN AVCO costing method.
    - Product Cost History: Implement SN AVCO costing method to track cost (standard_price) history of products over time.
    """,
    "depends": [
        "product",
        "stock",
        "account",
        "stock_account",
        "cost_tracking",
    ],
    "post_init_hook": "_hook_product_category",
    "author": "Nguyen Cao Hoang",
    "data": [
        "views/product_cost_history_views.xml",
        "data/product_category.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}  #type: ignore
