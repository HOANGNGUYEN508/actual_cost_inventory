{
    "name": "Technical Category",
    "category": "Sales",
		"summary": "Add technical category to products for better classification",
    "description":
    """
    - Technical Category: separate product category into 
		+ Account category: cost calculation, accounting.
		+ Technical category: for technical classification.
    """,
    "depends": [
        "mail",
        "product",
    ],
    "author": "Nguyen Cao Hoang",
    "data": [
        "data/res_groups.xml",
        "security/ir.model.access.csv",
        "views/product_category_technical_views.xml",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}  #type: ignore
