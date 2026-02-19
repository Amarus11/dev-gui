# -*- coding: utf-8 -*-

import hashlib
import hmac

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KnowledgeArticleMember(models.Model):
    """Explicit permission grant for a partner on a knowledge article.

    Combined with the inherited_permission system, this allows fine-grained
    access control similar to the official Odoo knowledge module.
    """

    _name = 'knowledge.article.member'
    _description = 'Knowledge Article Member'
    _order = 'id'

    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Member",
        required=True,
        ondelete='cascade',
        index=True,
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
    article_permission = fields.Selection(
        related='article_id.inherited_permission',
        string="Article Permission",
        store=True,
    )

    _sql_constraints = [
        (
            'unique_article_partner',
            'UNIQUE(article_id, partner_id)',
            'A partner can only have one membership per article.',
        ),
    ]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('permission', 'article_id')
    def _check_is_writable(self):
        """Every article must always have at least one writer."""
        article_ids = self.mapped('article_id')
        for article in article_ids:
            writers = article.article_member_ids.filtered(
                lambda m: m.permission == 'write'
            )
            if not writers and article.internal_permission != 'write':
                raise ValidationError(
                    _("Article '%s' must have at least one user with write access.", article.display_name)
                )

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    def write(self, vals):
        """Block changing article_id / partner_id for non-system users."""
        if not self.env.is_superuser() and ('article_id' in vals or 'partner_id' in vals):
            raise ValidationError(
                _("You cannot change the article or partner of a membership. Remove and re-create instead.")
            )
        return super().write(vals)

    def unlink(self):
        """Prevent removing the last writer from an article."""
        for member in self:
            if member.permission == 'write':
                remaining_writers = member.article_id.article_member_ids.filtered(
                    lambda m: m.permission == 'write' and m.id != member.id
                )
                has_internal_write = member.article_id.internal_permission == 'write'
                if not remaining_writers and not has_internal_write:
                    raise ValidationError(
                        _("Cannot remove the last writer from article '%s'.", member.article_id.display_name)
                    )
        return super().unlink()

    # ------------------------------------------------------------------
    # Business methods
    # ------------------------------------------------------------------

    def _get_invitation_hash(self):
        """Generate an HMAC-based hash for email invitation validation."""
        self.ensure_one()
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret', '')
        message = f'{self.id}-{self.article_id.id}-{self.partner_id.id}'
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
