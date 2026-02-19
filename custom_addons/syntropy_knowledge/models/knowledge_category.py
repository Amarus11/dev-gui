# -*- coding: utf-8 -*-

from odoo import fields, models


class KnowledgeCategory(models.Model):
    """Categories for organizing knowledge articles."""

    _name = 'knowledge.category'
    _description = 'Knowledge Category'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one(
        'knowledge.category',
        string="Parent Category",
        ondelete='cascade',
        index=True,
    )
    child_ids = fields.One2many(
        'knowledge.category',
        'parent_id',
        string="Sub-categories",
    )

    def _compute_display_name(self):
        for rec in self:
            names = []
            current = rec
            while current:
                names.append(current.name or '')
                current = current.parent_id
            rec.display_name = ' / '.join(reversed(names))
