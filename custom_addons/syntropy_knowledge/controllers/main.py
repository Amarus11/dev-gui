# -*- coding: utf-8 -*-

import json
import werkzeug

from odoo import http, _
from odoo.http import request


class KnowledgeController(http.Controller):
    """Main controller for Syntropy Knowledge."""

    @http.route('/knowledge/home', type='http', auth='user')
    def knowledge_home(self):
        """Redirect to the first accessible article."""
        article = request.env['knowledge.article'].action_home_page()
        if article.get('res_id'):
            return request.redirect(f'/odoo/knowledge/{article["res_id"]}')
        # No articles: redirect to article list
        return request.redirect('/odoo/knowledge')

    @http.route('/knowledge/article/<int:article_id>', type='http', auth='user')
    def knowledge_article_redirect(self, article_id):
        """Redirect to backend form view for a specific article."""
        return request.redirect(f'/odoo/knowledge/{article_id}')

    @http.route('/knowledge/get_article_permission_panel_data', type='json', auth='user')
    def get_article_permission_panel_data(self, article_id):
        """Return comprehensive permission data for the permission panel."""
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return {'error': 'Article not found'}
        
        members_data = []
        for member in article.article_member_ids:
            members_data.append({
                'id': member.id,
                'partner_id': member.partner_id.id,
                'partner_name': member.partner_id.display_name,
                'partner_email': member.partner_id.email,
                'partner_avatar': f'/web/image/res.partner/{member.partner_id.id}/avatar_128',
                'permission': member.permission,
                'is_current_user': member.partner_id == request.env.user.partner_id,
            })
        
        # Department-based access
        view_departments = [{'id': d.id, 'name': d.name} for d in article.view_department_ids]
        edit_departments = [{'id': d.id, 'name': d.name} for d in article.edit_department_ids]
        view_users = [{'id': u.id, 'name': u.name} for u in article.view_user_ids]
        edit_users = [{'id': u.id, 'name': u.name} for u in article.edit_user_ids]

        return {
            'article_id': article.id,
            'name': article.display_name,
            'internal_permission': article.internal_permission,
            'inherited_permission': article.inherited_permission,
            'category': article.category,
            'is_desynchronized': article.is_desynchronized,
            'user_permission': article.user_permission,
            'parent_id': article.parent_id.id if article.parent_id else False,
            'parent_name': article.parent_id.display_name if article.parent_id else False,
            'members': members_data,
            'view_departments': view_departments,
            'edit_departments': edit_departments,
            'view_users': view_users,
            'edit_users': edit_users,
            'share_token': article.share_token,
            'is_published': article.is_published,
        }

    @http.route('/knowledge/article/set_member_permission', type='json', auth='user')
    def set_member_permission(self, article_id, member_id, permission):
        """Update member permission."""
        article = request.env['knowledge.article'].browse(article_id)
        article._set_member_permission(member_id, permission)
        return {'success': True}

    @http.route('/knowledge/article/remove_member', type='json', auth='user')
    def remove_member(self, article_id, member_id):
        """Remove a member from an article."""
        article = request.env['knowledge.article'].browse(article_id)
        article._remove_member(member_id)
        return {'success': True, 'new_category': article.category}

    @http.route('/knowledge/article/set_internal_permission', type='json', auth='user')
    def set_internal_permission(self, article_id, permission):
        """Update article's internal permission."""
        article = request.env['knowledge.article'].browse(article_id)
        article._set_internal_permission(permission)
        return {'success': True}
