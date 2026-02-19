# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class KnowledgeArticleThread(models.Model):
    """Discussion thread anchored to highlighted text in a knowledge article.

    Each thread represents a comment / conversation pinned to a specific
    passage.  The anchor text is stored for display purposes even if the
    original passage is later modified.
    """

    _name = 'knowledge.article.thread'
    _description = 'Knowledge Article Thread'
    _inherit = ['mail.thread']
    _order = 'write_date desc, id desc'

    article_anchor_text = fields.Text(
        string="Anchor Text",
        help="Original highlighted text this thread is attached to.",
    )
    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
        ondelete='cascade',
        index=True,
    )
    is_resolved = fields.Boolean(
        string="Resolved",
        default=False,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @api.model
    def create(self, vals_list):
        """Truncate anchor text to avoid bloating the DB."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get('article_anchor_text'):
                vals['article_anchor_text'] = vals['article_anchor_text'][:1200]
        return super().create(vals_list)

    def write(self, vals):
        if 'is_resolved' in vals and len(self) > 1:
            # batch resolve/unresolve is fine
            pass
        return super().write(vals)

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------

    def _get_access_action(self, access_uid=None, force_website=False):
        """Return an action pointing to the parent article."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/odoo/knowledge/{self.article_id.id}',
        }

    def _message_compute_subject(self):
        self.ensure_one()
        return _("New Comment in %s", self.article_id.display_name)
