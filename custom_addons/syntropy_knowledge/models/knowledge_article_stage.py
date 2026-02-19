# -*- coding: utf-8 -*-

from odoo import fields, models


class KnowledgeArticleStage(models.Model):
    """Kanban stages for knowledge article items.

    Each stage belongs to a specific parent article, so multiple articles
    can have independent kanban pipelines.
    """

    _name = 'knowledge.article.stage'
    _description = 'Knowledge Article Stage'
    _order = 'parent_id, sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="Folded stages are hidden by default in the Kanban view.",
    )
    parent_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
        ondelete='cascade',
        index=True,
        help="The parent article that owns this stage pipeline.",
    )
