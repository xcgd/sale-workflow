# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Tecnativa - Pedro M. Baeza

from lxml import etree

from odoo import _, api, fields, models

from ..util.odoo_context import get_email_sending_confirmation_message


class SaleOrder(models.Model):
    _inherit = "sale.order"

    type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'sent': [('readonly', False)],
        },
        default=lambda so: so._default_type_id(),
        ondelete="restrict",
        copy=True,
    )

    @api.model
    def _default_type_id(self):
        return self.load_default_type_id() or self.env[
            "sale.order.type"
        ].search([], limit=1)

    @api.model
    def load_default_type_id(self):
        default_type_id = self.env.context.get("default_type_id")
        if default_type_id:
            type_id = self.env["sale.order.type"].browse(default_type_id)
        else:
            type_id = False
        return type_id

    @api.depends("partner_id", "company_id")
    def _compute_sale_type_id(self):
        for record in self:
            default_sale_type = self.load_default_type_id()
            if not record.partner_id:
                record.type_id = default_sale_type or self.env[
                    "sale.order.type"
                ].search(
                    [("company_id", "in", [self.env.company.id, False])],
                    limit=1,
                )
            else:
                sale_type = (
                    record.partner_id.with_context(
                        force_company=record.company_id.id
                    ).sale_type
                    or record.partner_id.commercial_partner_id.with_context(
                        force_company=record.company_id.id
                    ).sale_type
                    or default_sale_type
                )
                if sale_type:
                    record.type_id = sale_type

    @api.onchange("type_id")
    def onchange_type_id(self):
        # TODO: To be changed to computed stored readonly=False if possible in v14?
        vals = {}
        for order in self:
            order_type = order.type_id
            # Order values
            vals = {}
            if order_type.warehouse_id:
                vals.update({"warehouse_id": order_type.warehouse_id})
            if order_type.picking_policy:
                vals.update({"picking_policy": order_type.picking_policy})
            if order_type.payment_term_id:
                vals.update({"payment_term_id": order_type.payment_term_id})
            if order_type.pricelist_id:
                vals.update({"pricelist_id": order_type.pricelist_id})
            if order_type.incoterm_id:
                vals.update({"incoterm": order_type.incoterm_id})
            if vals:
                order.update(vals)
            # Order line values
            line_vals = {}
            line_vals.update({"route_id": order_type.route_id.id})
            order.order_line.update(line_vals)

    @api.model
    def create(self, vals):
        if vals.get("name", "/") == "/" and vals.get("type_id"):
            sale_type = self.env["sale.order.type"].browse(vals["type_id"])
            if sale_type.sequence_id:
                vals["name"] = sale_type.sequence_id.next_by_id()
        return super(SaleOrder, self).create(vals)

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.type_id.journal_id:
            res["journal_id"] = self.type_id.journal_id.id
        if self.type_id:
            res["sale_type_id"] = self.type_id.id
        return res

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
            self.id, force_send=True, raise_exception=False
        )

        return True

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

        # Default case: Nothing is done. (won't actually happen in the
        # production env).
        return True

    @api.model
    def fields_view_get(
        self, view_id=None, view_type='form', toolbar=False, submenu=False
    ):

        res = super(SaleOrder, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu
        )

        doc = etree.XML(res["arch"])

        for f in doc.xpath("//button[@name='print_quotation']"):
            f.set("string", _("Print"))

        # Force the translation of a confirmation message, for a simple call
        # to '_' is not efficient.
        for g in doc.xpath("//button[@name='action_quotation_send']"):
            g.attrib["confirm"] = get_email_sending_confirmation_message(
                self, g.attrib["confirm"]
            )

        res["arch"] = etree.tostring(doc)

        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_id")
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.order_id.type_id.route_id:
            self.update({"route_id": self.order_id.type_id.route_id})
        return res
