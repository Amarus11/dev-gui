# -*- coding: utf-8 -*-

import difflib

from markupsafe import Markup

from odoo import api, fields, models, _


class KnowledgeArticleVersion(models.Model):
    """Snapshots of a knowledge article body at a specific version."""

    _name = 'knowledge.article.version'
    _description = 'Knowledge Article Version'
    _order = 'version_number desc'

    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
        ondelete='cascade',
        index=True,
    )
    version_number = fields.Integer(
        string="Version",
        required=True,
    )
    content = fields.Html(
        string="Content",
        sanitize=False,
        prefetch=False,
    )
    user_id = fields.Many2one(
        'res.users',
        string="Author",
        default=lambda self: self.env.uid,
    )

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = _("Version %d", rec.version_number)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_compare_with_current(self):
        """Open a comparison wizard between this version and the current body."""
        self.ensure_one()
        wizard = self.env['knowledge.version.compare.wizard'].create({
            'article_id': self.article_id.id,
            'old_version_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Versions'),
            'res_model': 'knowledge.version.compare.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_compare_selected_versions(self):
        """Compare two selected versions (called from list view)."""
        if len(self) != 2:
            return
        versions = self.sorted('version_number')
        wizard = self.env['knowledge.version.compare.wizard'].create({
            'article_id': versions[0].article_id.id,
            'old_version_id': versions[0].id,
            'current_version_id': versions[1].id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Versions'),
            'res_model': 'knowledge.version.compare.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class KnowledgeVersionCompareWizard(models.TransientModel):
    """Transient wizard to display a visual diff between two article versions."""

    _name = 'knowledge.version.compare.wizard'
    _description = 'Version Compare Wizard'

    article_id = fields.Many2one(
        'knowledge.article',
        string="Article",
        required=True,
    )
    old_version_id = fields.Many2one(
        'knowledge.article.version',
        string="Old Version",
        required=True,
    )
    current_version_id = fields.Many2one(
        'knowledge.article.version',
        string="Current Version",
    )
    current_content = fields.Html(
        string="Current Content",
        compute='_compute_contents',
    )
    old_content = fields.Html(
        string="Old Content",
        compute='_compute_contents',
    )
    diff_html = fields.Html(
        string="Diff",
        compute='_compute_contents',
        sanitize=False,
    )

    @api.depends('old_version_id', 'current_version_id', 'article_id')
    def _compute_contents(self):
        for wizard in self:
            wizard.old_content = wizard.old_version_id.content or ''
            if wizard.current_version_id:
                wizard.current_content = wizard.current_version_id.content or ''
            else:
                wizard.current_content = wizard.article_id.body or ''
            wizard.diff_html = wizard._generate_diff_html()

    def _generate_diff_html(self):
        """Generate an HTML diff between old and current content."""
        self.ensure_one()
        old_text = (self.old_content or '').splitlines()
        new_text = (self.current_content or '').splitlines()

        diff = difflib.HtmlDiff(wrapcolumn=80)
        diff_table = diff.make_table(
            old_text,
            new_text,
            fromdesc=_("Version %d", self.old_version_id.version_number),
            todesc=(
                _("Version %d", self.current_version_id.version_number)
                if self.current_version_id
                else _("Current")
            ),
            context=True,
            numlines=3,
        )
        styles = Markup("""
        <style>
            .diff_header { background-color: #e0e0e0; padding: 4px 8px; }
            .diff_next { background-color: #c0c0c0; }
            .diff_add { background-color: #aaffaa; }
            .diff_chg { background-color: #ffff77; }
            .diff_sub { background-color: #ffaaaa; }
            table.diff { font-family: monospace; border-collapse: collapse; width: 100%; }
            table.diff td { padding: 2px 6px; white-space: pre-wrap; word-break: break-word; }
            table.diff th { padding: 4px 8px; text-align: left; }
        </style>
        """)
        return Markup(styles) + Markup(diff_table)
