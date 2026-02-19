# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KnowledgeArticleFavorite(models.Model):
    """Per-user bookmark for a knowledge article with (drag) ordering."""

    _name = 'knowledge.article.favorite'
    _description = 'Knowledge Article Favorite'
    _order = 'sequence, id'

    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string="User",
        required=True,
        ondelete='cascade',
        index=True,
        default=lambda self: self.env.uid,
    )
    is_article_active = fields.Boolean(
        related='article_id.active',
        store=True,
    )
    sequence = fields.Integer(default=0)

    _sql_constraints = [
        (
            'unique_article_user',
            'UNIQUE(article_id, user_id)',
            'An article can only be favorited once per user.',
        ),
    ]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model
    def create(self, vals_list):
        """Auto-assign sequence as max + 1 for each user."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if 'sequence' not in vals:
                user_id = vals.get('user_id', self.env.uid)
                max_seq = self.sudo().search(
                    [('user_id', '=', user_id)],
                    order='sequence desc',
                    limit=1,
                ).sequence or 0
                vals['sequence'] = max_seq + 1
        return super().create(vals_list)

    def write(self, vals):
        """Block changing article_id / user_id for non-admin."""
        if not self.env.is_superuser() and ('article_id' in vals or 'user_id' in vals):
            raise ValidationError(
                _("You cannot change the article or user of a favorite. Remove and re-create instead.")
            )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Business methods
    # ------------------------------------------------------------------

    def resequence_favorites(self, article_ids):
        """Reorder favorites for the current user based on article id list."""
        favorites = self.sudo().search([
            ('user_id', '=', self.env.uid),
            ('article_id', 'in', article_ids),
        ])
        fav_by_article = {f.article_id.id: f for f in favorites}
        for idx, article_id in enumerate(article_ids):
            fav = fav_by_article.get(article_id)
            if fav:
                fav.sequence = idx
