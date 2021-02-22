# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Tecnativa - Pedro M. Baeza

from lxml import etree

from odoo import api, fields, models

from ..util.odoo_context import get_email_sending_confirmation_message


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Sale Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=True,
    )

    @api.depends("partner_id", "company_id")
    def _compute_sale_type_id(self):
        self.sale_type_id = self.env["sale.order.type"]
        for record in self.filtered(
            lambda am: am.type in ["out_invoice", "out_refund"]
        ):
            if not record.partner_id:
                record.sale_type_id = self.env["sale.order.type"].search(
                    [("company_id", "in", [self.env.company.id, False])], limit=1
                )
            else:
                sale_type = (
                    record.partner_id.with_context(
                        force_company=record.company_id.id
                    ).sale_type
                    or record.partner_id.commercial_partner_id.with_context(
                        force_company=record.company_id.id
                    ).sale_type
                )
                if sale_type:
                    record.sale_type_id = sale_type

    @api.onchange("sale_type_id")
    def onchange_sale_type_id(self):
        # TODO: To be changed to computed stored readonly=False if possible in v14?
        sales_type = self.sale_type_id.sudo()
        if sales_type.payment_term_id:
            self.invoice_payment_term_id = sales_type.payment_term_id.id
        if sales_type.journal_id:
            self.journal_id = sales_type.journal_id.id

    def post(self):
        """Override to:
        - Send automatically an email at validation if specified.
        """

        ret = super(AccountMove, self).post()

        for invoice in self:
            if(
                invoice.sale_type_id
                and invoice.sale_type_id.send_invoice_mail_automatically
            ):
                invoice.action_invoice_sent()

        return ret

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
            return super(AccountMove, self).action_invoice_sent()

        # Refs: * addons/mail/models/mail_template.py, "send_mail" method.
        #       * addons/mail/models/ir_actions.py, "run_action_email" method.
        email_context = self.env.context.copy()
        email_context.pop("default_type", None)
        mail_template.with_context(email_context).send_mail(
            self.id, force_send=True, raise_exception=False
        )

        return True

    @api.model
    def fields_view_get(
        self, view_id=None, view_type='form', toolbar=False, submenu=False
    ):

        res = super(AccountMove, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu
        )

        doc = etree.XML(res["arch"])

        # Force the translation of a confirmation message, for a simple call
        # to '_' is not efficient.
        for f in doc.xpath("//button[@name='action_invoice_sent']"):
            f.attrib["confirm"] = get_email_sending_confirmation_message(
                self, f.attrib["confirm"]
            )

        res["arch"] = etree.tostring(doc)

        return res
