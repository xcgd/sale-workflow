# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_order_type(self):
        """Keep the method to default in case the partner doesn't have any"""
        default_type_id = self.env.context.get('default_type_id')
        if default_type_id:
            return self.env['sale.order.type'].browse(default_type_id)
        return self.env['sale.order.type'].search([], limit=1)

    type_id = fields.Many2one(
        comodel_name='sale.order.type',
        string='Type',
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'sent': [('readonly', False)],
        },
    )

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        sale_type = (self.partner_id.sale_type or
                     self.partner_id.commercial_partner_id.sale_type)
        if sale_type:
            self.type_id = sale_type
        else:
            self.type_id = self._get_order_type()

    @api.multi
    @api.onchange('type_id')
    def onchange_type_id(self):
        for order in self:
            if order.type_id.warehouse_id:
                order.warehouse_id = order.type_id.warehouse_id
            if order.type_id.picking_policy:
                order.picking_policy = order.type_id.picking_policy
            if order.type_id.payment_term_id:
                order.payment_term_id = order.type_id.payment_term_id.id
            if order.type_id.pricelist_id:
                order.pricelist_id = order.type_id.pricelist_id.id
            if order.type_id.incoterm_id:
                order.incoterm = order.type_id.incoterm_id.id

    @api.multi
    def match_order_type(self):
        order_types = self.env['sale.order.type'].search([])
        for order in self:
            for order_type in order_types:
                if order_type.matches_order(order):
                    order.type_id = order_type
                    order.onchange_type_id()
                    break

    @api.model
    def create(self, vals):
        """We trigger onchanges on create to ensure the type mechanics is
           applied even if the creation of the order isn't invoked from ui
           as is the case for website orders. We also ensure this way that
           a contact will be getting his commercial partner type if no
           type is set on his record"""
        fields_from_sale_type = [
            'type_id', 'warehouse_id', 'picking_policy',
            'payment_term_id', 'incoterm', 'pricelist_id',
        ]
        if not vals.get('type_id'):
            sale = self.new(vals)
            sale.onchange_partner_id()
            sale.onchange_type_id()
            for field in fields_from_sale_type:
                vals[field] = sale._fields[field].convert_to_write(
                    sale[field], sale,
                )
        if vals.get('name', '/') == '/' and vals.get('type_id'):
            sale_type = self.env['sale.order.type'].browse(vals['type_id'])
            if sale_type.sequence_id:
                vals['name'] = sale_type.sequence_id.next_by_id()
        return super().create(vals)

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.type_id.journal_id:
            res['journal_id'] = self.type_id.journal_id.id
        if self.type_id:
            res['sale_type_id'] = self.type_id.id
        return res

    @api.multi
    def action_quotation_send(self):
        """Send an email about this quotation / sales order.

        By default in the "sale" module, this opens a preview dialog box; we
        bypass that to directly send the right email.
        We have added a confirmation dialog box view-side though.
        """

        self.ensure_one()  # Ref: * addons/sale/sale.py

        mail_template = None
        if self.type_id.mail_template_id:
            mail_template = self.type_id.mail_template_id

        if not mail_template:
            return super(SaleOrder, self).action_quotation_send()

        # Refs: * addons/mail/models/mail_template.py, "send_mail" method.
        #       * addons/mail/models/ir_actions.py, "run_action_email" method.
        email_context = self.env.context.copy()
        email_context.pop("default_type", None)
        mail_template.with_context(email_context).send_mail(
            self.id, force_send=True, raise_exception=True
        )

        return True

    @api.multi
    def print_quotation(self):
        """Print the quotation / sales order and mark it as sent.

        Override this method defined in the "sale" module:
        - "Print" button: Use our own reports & don't mark as sent.
        """
        for so in self:
            report_xml = None
            if so.type_id.ir_actions_report_id:
                report_xml = so.type_id.ir_actions_report_id

            if report_xml:
                return report_xml.report_action(self)

        # Default case: Still call the parent (won't actually happen in the
        # production env).
        return super(SaleOrder, self).print_quotation()
