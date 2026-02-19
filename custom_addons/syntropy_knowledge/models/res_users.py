# -*- coding: utf-8 -*-

from odoo import api, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals_list):
        """Generate a welcome / tutorial article for every new internal user."""
        users = super().create(vals_list)
        for user in users:
            if user.has_group('base.group_user'):
                self._generate_tutorial_article(user)
        return users

    def _generate_tutorial_article(self, user):
        """Create a private welcome article for *user*."""
        Article = self.env['knowledge.article'].sudo()
        Article.create({
            'name': _("Welcome %s!", user.name),
            'icon': '👋',
            'body': _(
                "<h1>Welcome to Syntropy Knowledge!</h1>"
                "<p>This is your private workspace. Here are some tips:</p>"
                "<ul>"
                "<li><b>Create articles</b> using the <em>+ New</em> button in the sidebar.</li>"
                "<li><b>Organize</b> articles by dragging them into folders.</li>"
                "<li><b>Share</b> articles with your team using the Share button.</li>"
                "<li><b>Search</b> across all articles using the search bar.</li>"
                "<li><b>Favorite</b> articles by clicking the star icon.</li>"
                "</ul>"
                "<p>Happy writing! 📝</p>"
            ),
            'internal_permission': 'none',
            'article_member_ids': [(0, 0, {
                'partner_id': user.partner_id.id,
                'permission': 'write',
            })],
        })
