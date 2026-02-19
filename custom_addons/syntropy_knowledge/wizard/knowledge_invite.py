# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KnowledgeInvite(models.TransientModel):
    """Wizard to invite new members to a knowledge article."""

    _name = 'knowledge.invite'
    _description = 'Knowledge Invite Wizard'

    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
    )
    permission = fields.Selection(
        [
            ('write', 'Can write'),
            ('read', 'Can read'),
            ('none', 'No access'),
        ],
        string="Permission",
        required=True,
        default='read',
    )
    message = fields.Html(
        string="Message",
        help="Optional message to include in the invitation email.",
    )

    def action_invite(self):
        """Send invitations and create member records."""
        self.ensure_one()
        if not self.partner_ids:
            raise ValidationError(_("Please select at least one recipient."))

        article = self.article_id
        article.invite_members(
            partner_ids=self.partner_ids.ids,
            permission=self.permission,
        )
        return {'type': 'ir.actions.act_window_close'}
