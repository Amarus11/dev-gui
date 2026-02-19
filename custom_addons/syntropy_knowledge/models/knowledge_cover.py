# -*- coding: utf-8 -*-

from odoo import api, fields, models


class KnowledgeCover(models.Model):
    """Cover images for knowledge articles.

    Wraps an ``ir.attachment`` to provide a stable URL and support
    for autovacuum of orphaned covers.
    """

    _name = 'knowledge.cover'
    _description = 'Knowledge Cover'
    _order = 'id desc'

    attachment_id = fields.Many2one(
        'ir.attachment',
        string="Attachment",
        required=True,
        ondelete='cascade',
    )
    article_ids = fields.One2many(
        'knowledge.article',
        'cover_image_id',
        string="Articles",
    )
    attachment_url = fields.Char(
        string="URL",
        compute='_compute_attachment_url',
        store=True,
    )

    @api.depends('attachment_id', 'attachment_id.local_url')
    def _compute_attachment_url(self):
        for cover in self:
            if cover.attachment_id:
                att = cover.attachment_id
                if att.url:
                    cover.attachment_url = att.url
                else:
                    cover.attachment_url = f'/web/image/{att.id}'
            else:
                cover.attachment_url = False

    @api.model
    def create(self, vals_list):
        """Link uploaded attachments as public covers."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        records = super().create(vals_list)
        for cover in records:
            if cover.attachment_id:
                cover.attachment_id.write({
                    'res_model': 'knowledge.cover',
                    'res_id': cover.id,
                    'public': True,
                })
        return records

    def _gc_unused_covers(self):
        """Autovacuum: remove covers not linked to any article."""
        orphaned = self.search([('article_ids', '=', False)])
        orphaned.unlink()
