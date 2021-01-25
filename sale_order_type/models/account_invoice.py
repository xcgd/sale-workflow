# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _get_order_type(self):
        return self.env['sale.order.type'].search([], limit=1)

    sale_type_id = fields.Many2one(
        comodel_name='sale.order.type',
        string='Sale Type',
        default=_get_order_type,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        sale_type = (self.partner_id.sale_type or
                     self.partner_id.commercial_partner_id.sale_type)
        if sale_type:
            self.sale_type_id = sale_type
        return res

    @api.onchange('sale_type_id')
    def onchange_sale_type_id(self):
        if self.sale_type_id.payment_term_id:
            self.payment_term_id = self.sale_type_id.payment_term_id.id
        if self.sale_type_id.journal_id:
            self.journal_id = self.sale_type_id.journal_id.id

    @api.multi
    def match_order_type(self):
        order_types = self.env['sale.order.type'].search([])
        for invoice in self:
            for order_type in order_types:
                if order_type.matches_invoice(invoice):
                    invoice.sale_type_id = order_type
                    invoice.onchange_sale_type_id()
                    break

    @api.multi
    def invoice_validate(self):
        """Override to:
        - Send automatically an email at validation if specified.
        """

        for invoice in self:
            if(
                invoice.sale_type_id
                and invoice.sale_type_id.send_invoice_mail_automatically
            ):
                invoice.action_invoice_sent()

        return super(AccountInvoice, self).invoice_validate()

    @api.multi
    def action_invoice_sent(self):
        """Send an email about this invoice.

        By default in the "account" module, this opens a preview dialog box; we
        bypass that to directly send the right email (mustached so no
        previews). We have added a confirmation dialog box view-side though.
        """

        self.ensure_one()

        mail_template = None
        if self.sale_type_id and self.sale_type_id.invoice_mail_template_id:
            mail_template = self.sale_type_id.invoice_mail_template_id

        if not mail_template:
            return super(AccountInvoice, self).action_invoice_sent()

        # Refs: * addons/mail/models/mail_template.py, "send_mail" method.
        #       * addons/mail/models/ir_actions.py, "run_action_email" method.
        email_context = self.env.context.copy()
        email_context.pop("default_type", None)
        mail_template.with_context(email_context).send_mail(
            self.id, force_send=True, raise_exception=True
        )

        return True

    def _get_refund_common_fields(self):
        """Provide fields to copy when a new invoice is created upon refund.
        Called from the refund dialog box, see
        ``account/wizard/account_invoice.refund.py``.
        :rtype: List.
        """

        return super(AccountInvoice, self)._get_refund_common_fields() + [
            "sale_type_id",
        ]
