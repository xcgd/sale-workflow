def add_lang_info(recset):
    """Add lang info from the current user regardless of what the context may
    already contain. It so happens the context often has wrong lang info by
    default.

    Useful when running automated tasks.

    :type recset: Odoo record set.
    :return: That same Odoo record set with added lang info.
    """

    return recset.with_context(lang=recset.env.user.lang)


def get_email_sending_confirmation_message(recset, source):

    recset = add_lang_info(recset)

    return recset.env['ir.translation']._get_source(
        None, ('code',), recset.env.context.get("lang"), source
    )
