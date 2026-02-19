# -*- coding: utf-8 -*-

from odoo import fields, models


class KnowledgeArticleViewLog(models.Model):
    """Tracks individual article views for analytics."""

    _name = 'knowledge.article.view.log'
    _description = 'Knowledge Article View Log'
    _order = 'viewed_on desc'

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
        default=lambda self: self.env.uid,
    )
    viewed_on = fields.Datetime(
        string="Viewed On",
        default=fields.Datetime.now,
    )
