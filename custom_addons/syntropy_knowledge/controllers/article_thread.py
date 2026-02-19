# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class ArticleThreadController(http.Controller):
    """Controller for knowledge article comment threads."""

    @http.route('/knowledge/thread/create', type='json', auth='user')
    def create_thread(self, article_id, anchor_text=''):
        """Create a new comment thread anchored to text."""
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return {'error': 'Article not found'}
        
        thread = request.env['knowledge.article.thread'].create({
            'article_id': article_id,
            'article_anchor_text': anchor_text,
        })
        return {
            'thread_id': thread.id,
            'article_id': article_id,
            'anchor_text': thread.article_anchor_text,
            'is_resolved': False,
        }

    @http.route('/knowledge/thread/resolve', type='json', auth='user')
    def resolve_thread(self, thread_id):
        """Toggle resolved state on a thread."""
        thread = request.env['knowledge.article.thread'].browse(thread_id)
        if not thread.exists():
            return {'error': 'Thread not found'}
        thread.write({'is_resolved': not thread.is_resolved})
        return {'thread_id': thread_id, 'is_resolved': thread.is_resolved}

    @http.route('/knowledge/threads/messages', type='json', auth='user', methods=['POST'])
    def get_threads_messages(self, thread_ids, limit=30):
        """Fetch messages for multiple threads at once."""
        threads = request.env['knowledge.article.thread'].browse(thread_ids)
        result = {}
        for thread in threads.exists():
            messages = thread.message_ids[:limit]
            result[thread.id] = {
                'thread_id': thread.id,
                'anchor_text': thread.article_anchor_text,
                'is_resolved': thread.is_resolved,
                'messages': [{
                    'id': msg.id,
                    'body': msg.body,
                    'author_id': msg.author_id.id,
                    'author_name': msg.author_id.display_name,
                    'author_avatar': f'/web/image/res.partner/{msg.author_id.id}/avatar_128',
                    'date': msg.date.isoformat() if msg.date else '',
                } for msg in messages],
            }
        return result
