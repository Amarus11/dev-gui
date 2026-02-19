# -*- coding: utf-8 -*-

from odoo import fields, models


class KnowledgeTag(models.Model):
    """Tags for labeling knowledge articles."""

    _name = 'knowledge.tag'
    _description = 'Knowledge Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Color Index")
    description = fields.Text()
