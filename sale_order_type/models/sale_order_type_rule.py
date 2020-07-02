# Copyright 2018 Simone Rubino - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleOrderTypeRule(models.Model):
    _name = 'sale.order.type.rule'
    _order = 'sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    order_type_id = fields.Many2one(
        comodel_name='sale.order.type', ondelete='cascade')
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products')
    product_category_ids = fields.Many2many(
        comodel_name='product.category',
        string='Product categories')

    def add_to_domain(self, domain):
        """Add conditions set on this rule to the specified product domain.
        :type domain: List
        :rtype: List
        """

        rule_domains = []

        categories = self.product_category_ids
        if categories:
            rule_domains.append(models.expression.normalize_domain([
                ('categ_id', 'in', categories.ids),
            ]))

        products = self.product_ids
        if products:
            rule_domains.append(models.expression.normalize_domain([
                ('id', 'in', products.ids),
            ]))

        if rule_domains:
            # OR between products & categories.
            # AND between the specified domain and the one we add.
            domain = models.expression.normalize_domain(domain)
            rule_domains = models.expression.OR(rule_domains)
            domain = models.expression.AND([domain, rule_domains])
        return domain

    @api.multi
    def matches_order(self, order):
        """Return True if the rule matches the order,
        False otherwise"""
        self.ensure_one()
        order_products = order.order_line.mapped('product_id')
        return self.matches_products(order_products) \
            or self.matches_product_categories(
            order_products.mapped('categ_id'))

    @api.multi
    def matches_products(self, products):
        """Return True if the rule matches any of the products,
        False otherwise"""
        self.ensure_one()
        return self.product_ids and any(
            [rule_product in products
             for rule_product in self.product_ids])

    @api.multi
    def matches_product_categories(self, categories):
        """Return True if the rule matches any of the categories,
        False otherwise"""
        self.ensure_one()
        return self.product_category_ids and any(
            [rule_category in categories
             for rule_category in self.product_category_ids])

    @api.multi
    def matches_invoice(self, invoice):
        """Return True if the rule matches the invoice,
        False otherwise"""
        self.ensure_one()
        invoice_products = invoice.invoice_line_ids.mapped('product_id')
        return self.matches_products(invoice_products) \
            or self.matches_product_categories(
            invoice_products.mapped('categ_id'))
