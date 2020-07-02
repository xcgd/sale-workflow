# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Product(models.Model):
    """Apply sales type rules when looking up products.
    """

    _inherit = "product.product"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Override to:
        * Apply sales type rules when looking up products.
        """

        # Sent by sales order & client invoice views.
        sale_type_id = self.env.context.get("sale_type")
        if sale_type_id:
            sale_type = self.env["sale.order.type"].browse(sale_type_id)
            if sale_type:
                args = sale_type.add_rules_to_domain(args)

        return super(Product, self).search(
            args, offset=offset, limit=limit, order=order, count=count
        )
