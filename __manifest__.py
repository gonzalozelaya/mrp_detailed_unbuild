# -*- coding: utf-8 -*-
{
    'name': "Detailed unbuild MRP",
    
    'summary': """
        This module allows to detail unbild items and quantities""",

    'description': """
        This module allows to detail unbild items and quantities
    """,

    'author': "OutsourceArg",
    'website': "https://www.outsourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'MRP',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','mrp'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        #'views/templates.xml',
    ],

}
