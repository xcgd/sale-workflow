import logging

from odoo import api, SUPERUSER_ID

log = logging.getLogger(__name__)


def migrate(cr, installed_version):
    """Insert missing translations, after update to version 13.0.1.3.8.
    """

    log.info("Start...")

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

    cr.execute(
        """
        SELECT id
        FROM ir_model_fields
        WHERE (
            model = 'sale.order.type'
            AND name IN (
                'mail_template_id',
                'ir_actions_report_id',
                'invoice_mail_template_id',
                'send_invoice_mail_automatically'
            )
        )
        """
    )

    env = api.Environment(cr, SUPERUSER_ID, {})

    field_obj = env["ir.model.fields"]
    model_fields = field_obj.browse([tpl[0] for tpl in cr.fetchall()])

    field_map = {
        model_field.id: model_field.name for model_field in model_fields
    }

    for field_label in ["field_description", "help"]:
        env["ir.translation"].insert_missing(
            field_obj._fields.get(field_label), model_fields
        )

    for res_id, fieldname in field_map.items():
        for name, value in modifications.get(fieldname).items():

            cr.execute(
                """
                UPDATE ir_translation
                SET value = %(value)s
                WHERE (
                    name = %(name)s
                    AND lang = 'fr_FR'
                    AND module = 'sale_order_type'
                    AND res_id = %(res_id)s
                )
                """,
                {"value": value, "name": name, "res_id": res_id}
            )

    log.info("Done.")
