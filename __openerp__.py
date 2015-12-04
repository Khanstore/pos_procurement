# -*- coding: utf-8 -*-
{
    'name': "pos_procurement",

    'summary': """
        Make the Odoo Point of Sale use procurement orders""",

    'description': """
        Right now, Odoo point of sales does not use procurement orders,
        but creates manual stock_move and picking database entries.
        It is equivalent to "force_availability" and does not trigger
        any routes, like automatic re-stock or manufacture. By making
        the PoS use procurement orders, the routes will be triggered
        while at the same time being able to keep the old behaviour if
        desired.
        
        Note that this module does not change how the PoS looks, but
        changes how it behaves "behind the scenes".
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale'],

    # always loaded
    'data': [
        'pos_procurement_views.xml',
    ],
}
