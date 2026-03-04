{
    "name": "Cost Tracking",
    "category": "Sales",
		"summary": "Track cost (standard_price) history of products over time",
    "description":
    """
    - Product Cost History: Track cost (standard_price) history of products over time.
		- Product Product + Product Template: Log standard_price changes to cost history when changed manually.
    """,
    "depends": [
        "product",
        "stock",
        "account",
        "stock_account",
    ],
    "author": "Nguyen Cao Hoang",
    "data": [
        "data/res_groups.xml",
        "security/ir.model.access.csv",
        "views/product_cost_history_views.xml",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}  #type: ignore