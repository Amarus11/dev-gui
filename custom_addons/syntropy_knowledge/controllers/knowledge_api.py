# -*- coding: utf-8 -*-

import json

from odoo import http, _
from odoo.http import request


class KnowledgeAPIController(http.Controller):
    """API endpoints for knowledge articles (public sharing, stats)."""

    @http.route('/knowledge/article/<string:token>', type='http', auth='public', website=False)
    def article_public_view(self, token):
        """Public article view via share token."""
        article = request.env['knowledge.article'].sudo().search([
            ('share_token', '=', token),
            ('is_published', '=', True),
        ], limit=1)
        if not article:
            return request.not_found()
        
        return request.render('syntropy_knowledge.article_public_template', {
            'article': article,
        })

    @http.route('/knowledge/article/increment_view', type='json', auth='user')
    def increment_view(self, article_id):
        """Increment view count and create view log."""
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return {'error': 'Article not found'}
        
        article.sudo().write({
            'views_count': article.views_count + 1,
        })
        request.env['knowledge.article.view.log'].sudo().create({
            'article_id': article_id,
            'user_id': request.env.uid,
        })
        return {'views_count': article.views_count}

    @http.route('/knowledge/article/toggle_like', type='json', auth='user')
    def toggle_like(self, article_id):
        """Toggle like on an article."""
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return {'error': 'Article not found'}
        
        result = article.action_toggle_like()
        return {
            'likes_count': article.likes_count,
            'is_liked': request.env.user.partner_id in article.liked_by_ids,
        }

    @http.route('/knowledge/article/<int:article_id>/messages', type='json', auth='user')
    def get_article_messages(self, article_id, limit=20, offset=0):
        """Get the comment thread for an article (chatter messages)."""
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return {'error': 'Article not found'}
        
        messages = article.message_ids[offset:offset + limit]
        return [{
            'id': msg.id,
            'body': msg.body,
            'author_id': msg.author_id.id,
            'author_name': msg.author_id.display_name,
            'author_avatar': f'/web/image/res.partner/{msg.author_id.id}/avatar_128',
            'date': msg.date.isoformat() if msg.date else '',
            'message_type': msg.message_type,
        } for msg in messages]

    @http.route('/knowledge/article/search', type='json', auth='user')
    def search_articles(self, search_term, limit=40):
        """Full-text search across articles."""
        articles = request.env['knowledge.article'].get_user_sorted_articles(
            search_term, limit=limit,
        )
        return articles
