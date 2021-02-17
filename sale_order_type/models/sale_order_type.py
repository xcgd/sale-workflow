# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderTypology(models.Model):
    _name = "sale.order.type"
    _description = "Type of sale order"

    def init(self):

        super(SaleOrderTypology, self).init()

        modifications = {
            "mail_template_id": dict(
                field_description="Modèle d'email devis/commandes",
                help="Choisir un modèle d'email de devis/commande.",
            ),
            "ir_actions_report_id": dict(
                field_description="Modèle de document devis/commandes",
                help="Choisir un modèle de document.",
            ),
            "invoice_mail_template_id": dict(
                field_description="Modèle d'email factures",
                help="Choisir un modèle d'email de facture.",
            ),
            "send_invoice_mail_automatically": dict(
                field_description="Envoyer l'email de facture automatiquement",
                help=(
                    "Si cochée, envoyer automatiquement le modèle d'email de "
                    "facture"
                ),
            ),
        }

        field_obj = self.env["ir.model.fields"]
        model_fields = field_obj.search([
            ("model", "=", self._name),
            ("name", "in", [
                "mail_template_id", "ir_actions_report_id",
                "invoice_mail_template_id",
                "send_invoice_mail_automatically",
            ]),
        ])
        field_map = {
            model_field.id: model_field.name
            for model_field in model_fields
        }

        for field_label in ["field_description", "help"]:
            self.env["ir.translation"].insert_missing(
                field_obj._fields.get(field_label), model_fields
            )

        self.env.cr.execute(
            """
            SELECT name, lang, res_id, src, type, module, state, comments
            FROM ir_translation
            WHERE (
                name IN (
                    'ir.model.fields,field_description',
                    'ir.model.fields,help'
                )
                AND lang = 'fr_FR'
                AND module = 'sale_order_type'
                AND res_id IN %s
            )
            """,
            (tuple(model_fields.ids),)
        )

        vals_list = [
            dict(
                new_translation,
                value=(
                    modifications.get(
                        field_map.get(new_translation.get('res_id'))
                    )
                    .get(new_translation.get("name").split(",")[1])
                )
            )
            for new_translation in self.env.cr.dictfetchall()
        ]

        for vals in vals_list:
            self.env["ir.translation"]._update_translations([vals])

    @api.model
    def _get_domain_sequence_id(self):
        seq_type = self.env.ref("sale.seq_sale_order")
        return [("code", "=", seq_type.code)]

    @api.model
    def _get_selection_picking_policy(self):
        return self.env["sale.order"].fields_get(allfields=["picking_policy"])[
            "picking_policy"
        ]["selection"]

    def default_picking_policy(self):
        default_dict = self.env["sale.order"].default_get(["picking_policy"])
        return default_dict.get("picking_policy")

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Entry Sequence",
        copy=False,
        domain=_get_domain_sequence_id,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Billing Journal",
        domain=[("type", "=", "sale")],
    )
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Warehouse")
    picking_policy = fields.Selection(
        selection="_get_selection_picking_policy",
        string="Shipping Policy",
        default=default_picking_policy,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="warehouse_id.company_id",
        store=True,
        readonly=True,
    )
    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term", string="Payment Term"
    )
    pricelist_id = fields.Many2one(comodel_name="product.pricelist", strint="Pricelist")
    incoterm_id = fields.Many2one(comodel_name="account.incoterms", string="Incoterm")
    route_id = fields.Many2one(
        "stock.location.route",
        string="Route",
        domain=[("sale_selectable", "=", True)],
        ondelete="restrict",
        check_company=True,
    )

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Quotation/Order mail template",
        help="Choose a mail template for quotations/orders.",
    )

    ir_actions_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Quotation/order document template",
        help="Choose a document template.",
    )

    invoice_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Invoice mail template",
        help="Choose a mail template for the invoice.",
    )

    send_invoice_mail_automatically = fields.Boolean(
        string="Send invoice mail automatically",
        help="If checked, send the invoice mail template automatically",
    )
