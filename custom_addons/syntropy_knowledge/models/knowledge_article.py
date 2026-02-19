# -*- coding: utf-8 -*-

import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from markupsafe import Markup
from bs4 import BeautifulSoup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import is_html_empty
from odoo.tools.sql import SQL

ARTICLE_PERMISSION_LEVEL = {'none': 0, 'read': 1, 'write': 2}


class KnowledgeArticle(models.Model):
    """Knowledge Article — core model for Syntropy Knowledge.

    Provides a hierarchical, permission-aware knowledge base with:
    * Partner-based membership (inherited from Odoo's knowledge module)
    * Department / user-based access (integrated with HR)
    * Favorites, likes, versioning, trash management
    """

    _name = 'knowledge.article'
    _description = 'Knowledge Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'favorite_count desc, write_date desc, id desc'
    _mail_post_access = 'read'
    _parent_store = True

    DEFAULT_ARTICLE_TRASH_LIMIT_DAYS = 30

    # ------------------------------------------------------------------
    # Fields — Core
    # ------------------------------------------------------------------

    active = fields.Boolean(default=True)
    name = fields.Char(
        string="Title",
        tracking=20,
        index=True,
    )
    body = fields.Html(
        string="Body",
        sanitize=False,
        prefetch=False,
    )
    icon = fields.Char(
        string="Icon",
        size=30,
        help="Emoji used as the article icon.",
    )
    cover_image_id = fields.Many2one(
        'knowledge.cover',
        string="Cover Image",
        ondelete='set null',
    )
    cover_image_url = fields.Char(
        string="Cover URL",
        related='cover_image_id.attachment_url',
    )
    cover_image_position = fields.Float(
        string="Cover Vertical Offset",
        default=50.0,
    )
    is_locked = fields.Boolean(
        string="Locked",
        help="When locked, users cannot write on the body or change the title, "
             "even if they have write access on the article.",
    )
    full_width = fields.Boolean(
        string="Full Width",
        help="When set, the article body will take the full width available.",
    )
    is_published = fields.Boolean(
        string="Published",
        default=False,
    )
    share_token = fields.Char(
        string="Share Token",
        copy=False,
        readonly=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Fields — Tree / Hierarchy
    # ------------------------------------------------------------------

    parent_id = fields.Many2one(
        'knowledge.article',
        string="Parent Article",
        tracking=30,
        index=True,
        ondelete='cascade',
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'knowledge.article',
        'parent_id',
        string="Child Articles",
        copy=True,
    )
    root_article_id = fields.Many2one(
        'knowledge.article',
        string="Root Article",
        compute='_compute_root_article_id',
        store=True,
        recursive=True,
        compute_sudo=True,
        tracking=10,
        index=True,
    )
    has_article_children = fields.Boolean(
        string="Has Children",
        compute='_compute_has_article_children',
    )
    sequence = fields.Integer(
        string="Sequence",
        default=0,
    )

    # ------------------------------------------------------------------
    # Fields — Article Items (Kanban)
    # ------------------------------------------------------------------

    is_article_item = fields.Boolean(
        string="Is Item",
        default=False,
        index=True,
    )
    stage_id = fields.Many2one(
        'knowledge.article.stage',
        string="Item Stage",
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    article_properties_definition = fields.PropertiesDefinition(
        string="Item Properties",
    )
    article_properties = fields.Properties(
        string="Properties",
        definition='parent_id.article_properties_definition',
        copy=True,
    )

    # ------------------------------------------------------------------
    # Fields — Permission (partner-based, Odoo-style)
    # ------------------------------------------------------------------

    internal_permission = fields.Selection(
        [('write', 'Can write'), ('read', 'Can read'), ('none', 'No access')],
        string="Internal Permission",
        help="Default permission for all internal users.",
    )
    inherited_permission = fields.Selection(
        [('write', 'Can write'), ('read', 'Can read'), ('none', 'No access')],
        string="Inherited Permission",
        compute='_compute_inherited_permission',
        compute_sudo=True,
        store=True,
        recursive=True,
        index=True,
    )
    inherited_permission_parent_id = fields.Many2one(
        'knowledge.article',
        string="Inherited Permission Source",
        compute='_compute_inherited_permission',
        compute_sudo=True,
        store=True,
        recursive=True,
    )
    article_member_ids = fields.One2many(
        'knowledge.article.member',
        'article_id',
        string="Members",
        copy=True,
    )
    is_desynchronized = fields.Boolean(
        string="Desynchronized",
        default=False,
        help="If set, this article won't inherit access rules from its parents.",
    )

    # ------------------------------------------------------------------
    # Fields — Permission (department / user-based, HR integration)
    # ------------------------------------------------------------------

    view_department_ids = fields.Many2many(
        'hr.department',
        relation='knowledge_article_view_dept_rel',
        column1='article_id',
        column2='department_id',
        string="View Departments",
        help="Departments whose members have read access to this article.",
    )
    edit_department_ids = fields.Many2many(
        'hr.department',
        relation='knowledge_article_edit_dept_rel',
        column1='article_id',
        column2='department_id',
        string="Edit Departments",
        help="Departments whose members have write access to this article.",
    )
    view_user_ids = fields.Many2many(
        'res.users',
        relation='knowledge_article_view_user_rel',
        column1='article_id',
        column2='user_id',
        string="View Users",
    )
    edit_user_ids = fields.Many2many(
        'res.users',
        relation='knowledge_article_edit_user_rel',
        column1='article_id',
        column2='user_id',
        string="Edit Users",
    )

    # ------------------------------------------------------------------
    # Fields — Computed access
    # ------------------------------------------------------------------

    user_has_access = fields.Boolean(
        string="Has Access",
        compute='_compute_user_access',
        search='_search_user_has_access',
    )
    user_has_write_access = fields.Boolean(
        string="Has Write Access",
        compute='_compute_user_access',
        search='_search_user_has_write_access',
    )
    user_permission = fields.Selection(
        [('write', 'write'), ('read', 'read'), ('none', 'none')],
        string="User Permission",
        compute='_compute_user_permission',
    )

    # ------------------------------------------------------------------
    # Fields — Category & tags
    # ------------------------------------------------------------------

    category = fields.Selection(
        [('workspace', 'Workspace'), ('private', 'Private'), ('shared', 'Shared')],
        string="Section",
        compute='_compute_category',
        compute_sudo=True,
        store=True,
        recursive=True,
        index=True,
    )
    category_id = fields.Many2one(
        'knowledge.category',
        string="Category",
    )
    tag_ids = fields.Many2many(
        'knowledge.tag',
        string="Tags",
    )

    # ------------------------------------------------------------------
    # Fields — Favorites
    # ------------------------------------------------------------------

    favorite_ids = fields.One2many(
        'knowledge.article.favorite',
        'article_id',
        string="Favorites",
        copy=False,
    )
    favorite_count = fields.Integer(
        string="Favorite Count",
        compute='_compute_favorite_count',
        store=True,
        copy=False,
        default=0,
    )
    is_user_favorite = fields.Boolean(
        string="Is Favorited",
        compute='_compute_is_user_favorite',
        search='_search_is_user_favorite',
    )
    user_favorite_sequence = fields.Integer(
        string="Favorite Sequence",
        compute='_compute_is_user_favorite',
    )

    # ------------------------------------------------------------------
    # Fields — Stats
    # ------------------------------------------------------------------

    views_count = fields.Integer(
        string="Views",
        default=0,
        readonly=True,
    )
    liked_by_ids = fields.Many2many(
        'res.partner',
        relation='knowledge_article_likes_rel',
        column1='article_id',
        column2='partner_id',
        string="Liked By",
    )
    likes_count = fields.Integer(
        string="Likes",
        compute='_compute_likes_count',
        store=True,
    )
    version = fields.Integer(
        string="Version",
        default=1,
    )

    # ------------------------------------------------------------------
    # Fields — Versioning / tracking
    # ------------------------------------------------------------------

    version_ids = fields.One2many(
        'knowledge.article.version',
        'article_id',
        string="Versions",
    )
    last_edition_uid = fields.Many2one(
        'res.users',
        string="Last Edited By",
        readonly=True,
        copy=False,
    )
    last_edition_date = fields.Datetime(
        string="Last Edited On",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Fields — Trash
    # ------------------------------------------------------------------

    to_delete = fields.Boolean(
        string="Trashed",
        default=False,
        tracking=100,
        help="When sent to trash, articles are flagged to be deleted days after "
             "last edit. knowledge_article_trash_limit_days config parameter can "
             "be used to modify the number of days (default is 30).",
    )
    deletion_date = fields.Date(
        string="Deletion Date",
        compute='_compute_deletion_date',
    )

    # ------------------------------------------------------------------
    # SQL Constraints
    # ------------------------------------------------------------------

    _sql_constraints = [
        (
            'check_root_internal_permission',
            "CHECK(parent_id IS NOT NULL OR internal_permission IS NOT NULL)",
            "Root articles must have an internal permission.",
        ),
        (
            'check_desync_permission',
            "CHECK(is_desynchronized IS NOT TRUE OR internal_permission IS NOT NULL)",
            "Desynchronized articles must have an internal permission.",
        ),
        (
            'check_root_not_desync',
            "CHECK(parent_id IS NOT NULL OR is_desynchronized IS NOT TRUE)",
            "Root articles cannot be desynchronized.",
        ),
        (
            'check_item_parent',
            "CHECK(is_article_item IS NOT TRUE OR parent_id IS NOT NULL)",
            "Article items must have a parent.",
        ),
        (
            'check_trash_archived',
            "CHECK(to_delete IS NOT TRUE OR active IS NOT TRUE)",
            "Trashed articles must be archived.",
        ),
    ]

    # ==================================================================
    # INIT — full-text search index
    # ==================================================================

    def init(self):
        super().init()

    # ==================================================================
    # CONSTRAINTS
    # ==================================================================

    @api.constrains('parent_id')
    def _check_parent_id_recursion(self):
        if self._has_cycle():
            raise ValidationError(
                _("Articles %s cannot be updated as this would create a recursive hierarchy.",
                  ', '.join(self.mapped('name')))
            )

    @api.constrains('internal_permission', 'article_member_ids')
    def _check_is_writable(self):
        """Articles must always have at least one writer."""
        for article in self:
            if article.inherited_permission != 'write' and not article._has_write_member():
                raise ValidationError(
                    _("The article '%s' needs at least one member with 'Write' access.",
                      article.display_name)
                )

    def _has_write_member(self):
        """Return True if the article has at least one member with write permission."""
        self.ensure_one()
        return any(m.permission == 'write' for m in self.article_member_ids)

    # ==================================================================
    # COMPUTED FIELDS
    # ==================================================================

    # ---- Root article ------------------------------------------------

    @api.depends('parent_id', 'parent_id.root_article_id')
    def _compute_root_article_id(self):
        """If no parent, root is self. Otherwise inherit from parent."""
        with_parent = self.filtered('parent_id')
        for article in self - with_parent:
            article.root_article_id = article

        if not with_parent:
            return

        articles_by_parent = defaultdict(lambda: self.env['knowledge.article'])
        for article in with_parent:
            articles_by_parent[article.parent_id] += article

        for parent, articles in articles_by_parent.items():
            ancestors = self.env['knowledge.article']
            while parent:
                if parent in ancestors:
                    raise ValidationError(
                        _("Articles %s cannot be updated as this would create a recursive hierarchy.",
                          ', '.join(articles.mapped('name')))
                    )
                ancestors += parent
                parent = parent.parent_id
            articles.root_article_id = ancestors[-1:]

    # ---- Inherited permission ----------------------------------------

    @api.depends('parent_id', 'parent_id.inherited_permission_parent_id', 'internal_permission')
    def _compute_inherited_permission(self):
        """Walk up the tree until finding an article with an internal_permission
        set, or a desynchronized article.  Store both the effective permission
        and the article it comes from.
        """
        self_inherit = self.filtered(lambda a: a.internal_permission)
        for article in self_inherit:
            article.inherited_permission = article.internal_permission
            article.inherited_permission_parent_id = False

        remaining = self - self_inherit
        if not remaining:
            return

        articles_by_parent = defaultdict(lambda: self.env['knowledge.article'])
        for article in remaining:
            articles_by_parent[article.parent_id] += article

        for parent, articles in articles_by_parent.items():
            ancestors = self.env['knowledge.article']
            while parent:
                if parent in ancestors:
                    raise ValidationError(
                        _("Articles %s cannot be updated as this would create a recursive hierarchy.",
                          ', '.join(articles.mapped('name')))
                    )
                ancestors += parent
                if parent.internal_permission or parent.is_desynchronized:
                    break
                parent = parent.parent_id
            articles.inherited_permission = ancestors[-1:].internal_permission
            articles.inherited_permission_parent_id = ancestors[-1:]

    # ---- User permission (hybrid) ------------------------------------

    @api.depends_context('uid')
    @api.depends('internal_permission', 'article_member_ids.partner_id',
                 'article_member_ids.permission',
                 'view_department_ids', 'edit_department_ids',
                 'view_user_ids', 'edit_user_ids')
    def _compute_user_permission(self):
        """Compute the effective permission for the current user.

        Priority order (highest wins):
        1.  Superuser → 'write'
        2.  Partner-based membership on this article + ancestors via parent_path
        3.  Department-based access (edit_department_ids > view_department_ids)
        4.  User-specific access (edit_user_ids > view_user_ids)
        5.  Inherited (internal) permission
        6.  Fallback → 'none'

        Among all sources the **highest** permission level wins.
        """
        if self.env.su:
            self.user_permission = 'write'
            return

        # Handle transient (unsaved) records
        transient = self.filtered(lambda a: not a.ids)
        transient.user_permission = 'write'
        to_update = self - transient
        if not to_update:
            return

        user = self.env.user
        partner = user.partner_id

        # ---- partner-based membership --------------------------------
        member_permissions = to_update._get_partner_member_permissions(partner)

        # ---- department-based ----------------------------------------
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1,
        )
        department = employee.department_id if employee else self.env['hr.department']

        for article in to_update:
            article_id = article.ids[0]
            highest = 'none'

            # 1. Partner-based membership
            member_perm = member_permissions.get(article_id)
            if member_perm:
                highest = self._highest_permission(highest, member_perm)

            # 2. Department-based
            if department:
                if department in article.edit_department_ids:
                    highest = self._highest_permission(highest, 'write')
                elif department in article.view_department_ids:
                    highest = self._highest_permission(highest, 'read')

            # 3. User-specific
            if user in article.edit_user_ids:
                highest = self._highest_permission(highest, 'write')
            elif user in article.view_user_ids:
                highest = self._highest_permission(highest, 'read')

            # 4. Inherited (internal) permission
            inherited = article.inherited_permission or 'none'
            if not user.share:
                highest = self._highest_permission(highest, inherited)

            article.user_permission = highest

    @staticmethod
    def _highest_permission(perm_a, perm_b):
        """Return the higher of two permission strings."""
        if ARTICLE_PERMISSION_LEVEL.get(perm_a, 0) >= ARTICLE_PERMISSION_LEVEL.get(perm_b, 0):
            return perm_a
        return perm_b

    # ---- User access booleans ----------------------------------------

    @api.depends_context('uid')
    @api.depends('user_permission')
    def _compute_user_access(self):
        """Compute boolean access flags from user_permission."""
        for article in self:
            perm = article.user_permission or 'none'
            article.user_has_access = perm in ('read', 'write')
            article.user_has_write_access = perm == 'write'

    # ---- Search methods for access fields ----------------------------

    def _search_user_has_access(self, operator, value):
        """Return a domain filtering articles accessible to the current user.

        Combines:
        * knowledge.article.member records for the current partner
        * Department membership via hr.employee
        * Explicit view_user_ids / edit_user_ids
        * inherited_permission
        """
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        is_positive = (value and operator == '=') or (not value and operator == '!=')
        accessible_ids = self._get_accessible_article_ids(permission_level='read')
        op = 'in' if is_positive else 'not in'
        return [('id', op, list(accessible_ids))]

    def _search_user_has_write_access(self, operator, value):
        """Return a domain filtering articles writable by the current user."""
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError("Unsupported search operator")

        is_positive = (value and operator == '=') or (not value and operator == '!=')
        writable_ids = self._get_accessible_article_ids(permission_level='write')
        op = 'in' if is_positive else 'not in'
        return [('id', op, list(writable_ids))]

    def _get_accessible_article_ids(self, permission_level='read'):
        """Return a set of article IDs accessible to the current user at the
        given *permission_level* ('read' or 'write').

        Uses raw SQL for performance.  Combines:
        1. Partner-based member permissions
        2. Department-based permissions
        3. User-specific permissions (M2M)
        4. Inherited (internal) permission
        """
        user = self.env.user
        partner_id = user.partner_id.id

        if permission_level == 'write':
            required_perms = ('write',)
            inherited_filter = "= 'write'"
        else:
            required_perms = ('read', 'write')
            inherited_filter = "IN ('read', 'write')"

        # 1. Member-based
        self.env.cr.execute(SQL("""
            SELECT DISTINCT kam.article_id
              FROM knowledge_article_member kam
             WHERE kam.partner_id = %(partner_id)s
               AND kam.permission IN %(perms)s
        """, partner_id=partner_id, perms=tuple(required_perms)))
        article_ids = {r[0] for r in self.env.cr.fetchall()}

        # Members with 'none' — exclude from inherited
        self.env.cr.execute(SQL("""
            SELECT DISTINCT kam.article_id
              FROM knowledge_article_member kam
             WHERE kam.partner_id = %(partner_id)s
               AND kam.permission = 'none'
        """, partner_id=partner_id))
        excluded_ids = {r[0] for r in self.env.cr.fetchall()}

        # 2. Department-based
        self.env.cr.execute(SQL("""
            SELECT he.department_id
              FROM hr_employee he
             WHERE he.user_id = %(user_id)s
             LIMIT 1
        """, user_id=user.id))
        dept_row = self.env.cr.fetchone()
        dept_id = dept_row[0] if dept_row else None

        if dept_id:
            if permission_level == 'write':
                self.env.cr.execute(SQL("""
                    SELECT article_id
                      FROM knowledge_article_edit_dept_rel
                     WHERE department_id = %(dept_id)s
                """, dept_id=dept_id))
            else:
                self.env.cr.execute(SQL("""
                    SELECT article_id FROM knowledge_article_edit_dept_rel
                     WHERE department_id = %(dept_id)s
                    UNION
                    SELECT article_id FROM knowledge_article_view_dept_rel
                     WHERE department_id = %(dept_id)s
                """, dept_id=dept_id))
            article_ids |= {r[0] for r in self.env.cr.fetchall()}

        # 3. User-specific M2M
        if permission_level == 'write':
            self.env.cr.execute(SQL("""
                SELECT article_id
                  FROM knowledge_article_edit_user_rel
                 WHERE user_id = %(user_id)s
            """, user_id=user.id))
        else:
            self.env.cr.execute(SQL("""
                SELECT article_id FROM knowledge_article_edit_user_rel
                 WHERE user_id = %(user_id)s
                UNION
                SELECT article_id FROM knowledge_article_view_user_rel
                 WHERE user_id = %(user_id)s
            """, user_id=user.id))
        article_ids |= {r[0] for r in self.env.cr.fetchall()}

        # 4. Inherited (internal) permission — only for internal users
        if not user.share:
            self.env.cr.execute(SQL("""
                SELECT id FROM knowledge_article
                 WHERE inherited_permission %s
            """ % inherited_filter))
            inherited_ids = {r[0] for r in self.env.cr.fetchall()}
            article_ids |= (inherited_ids - excluded_ids)

        return article_ids

    # ---- Category ----------------------------------------------------

    @api.depends('root_article_id.internal_permission',
                 'root_article_id.article_member_ids.permission')
    def _compute_category(self):
        """Categorise articles:
        * workspace — root internal_permission is not 'none'
        * shared   — root has >1 member with access, or has department/user grants
        * private  — root has 'none' internal_permission and at most one member
        """
        workspace = self.filtered(
            lambda a: a.root_article_id.internal_permission != 'none'
        )
        workspace.category = 'workspace'

        remaining = self - workspace
        if not remaining:
            return

        results = self.env['knowledge.article.member']._read_group(
            [('article_id', 'in', remaining.root_article_id.ids),
             ('permission', '!=', 'none')],
            ['article_id'],
            ['__count'],
        )
        access_count_by_root = {article.id: count for article, count in results}

        for article in remaining:
            root_id = article.root_article_id.id
            if access_count_by_root.get(root_id, 0) > 1:
                article.category = 'shared'
            else:
                article.category = 'private'

    # ---- Has children ------------------------------------------------

    @api.depends('child_ids', 'child_ids.is_article_item')
    def _compute_has_article_children(self):
        results = self.env['knowledge.article']._read_group(
            [('parent_id', 'in', self.ids), ('is_article_item', '=', False)],
            ['parent_id'],
            ['__count'],
        )
        parents_with_children = {parent.id for parent, _count in results}
        for article in self:
            article.has_article_children = article.id in parents_with_children

    # ---- Favorites ---------------------------------------------------

    @api.depends('favorite_ids')
    def _compute_favorite_count(self):
        favorites = self.env['knowledge.article.favorite']._read_group(
            [('article_id', 'in', self.ids)],
            ['article_id'],
            ['__count'],
        )
        count_by_article = {article.id: count for article, count in favorites}
        for article in self:
            article.favorite_count = count_by_article.get(article.id, 0)

    @api.depends_context('uid')
    @api.depends('favorite_ids.user_id')
    def _compute_is_user_favorite(self):
        if self.env.user._is_public():
            self.is_user_favorite = False
            self.user_favorite_sequence = -1
            return

        favorites = self.env['knowledge.article.favorite'].search([
            ('article_id', 'in', self.ids),
            ('user_id', '=', self.env.user.id),
        ])
        fav_map = {f.article_id.id: f.sequence for f in favorites}
        for article in self:
            if article.id in fav_map:
                article.is_user_favorite = True
                article.user_favorite_sequence = fav_map[article.id]
            else:
                article.is_user_favorite = False
                article.user_favorite_sequence = -1

    def _search_is_user_favorite(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError("Unsupported search operation on favorite articles")
        if (value and operator == '=') or (not value and operator == '!='):
            return [('favorite_ids', 'in', self.env['knowledge.article.favorite'].sudo()._search(
                [('user_id', '=', self.env.uid)]
            ))]
        return [('favorite_ids', 'not in', self.env['knowledge.article.favorite'].sudo()._search(
            [('user_id', '=', self.env.uid)]
        ))]

    # ---- Likes -------------------------------------------------------

    @api.depends('liked_by_ids')
    def _compute_likes_count(self):
        for article in self:
            article.likes_count = len(article.liked_by_ids)

    # ---- Deletion date -----------------------------------------------

    @api.depends('to_delete', 'write_date')
    def _compute_deletion_date(self):
        trashed = self.filtered(lambda a: a.to_delete)
        (self - trashed).deletion_date = False
        if trashed:
            limit_days = self.env['ir.config_parameter'].sudo().get_param(
                'knowledge.knowledge_article_trash_limit_days',
            )
            try:
                limit_days = int(limit_days)
            except (ValueError, TypeError):
                limit_days = self.DEFAULT_ARTICLE_TRASH_LIMIT_DAYS
            for article in trashed:
                article.deletion_date = article.write_date + timedelta(days=limit_days)

    # ---- Display name ------------------------------------------------

    @api.depends('name', 'icon')
    def _compute_display_name(self):
        for article in self:
            name = article.name or _('Untitled')
            article.display_name = f"{article.icon} {name}" if article.icon else name

    # ==================================================================
    # CRUD
    # ==================================================================

    @api.model
    def create(self, vals_list):
        """Create one or more articles.

        * Auto-generate a share_token (uuid4) for each article.
        * Set the body header from the name when no body is provided.
        * Track last_edition_uid / last_edition_date.
        * Auto-sequence based on parent's current max sequence.

        Odoo 18: create() natively accepts a list — no @api.model_create_multi.
        """
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        vals_by_parent = {}
        parent_ids = set()

        for vals in vals_list:
            # Share token
            if not vals.get('share_token'):
                vals['share_token'] = uuid.uuid4().hex

            # Body header
            if 'body' not in vals:
                vals['body'] = (
                    Markup('<h1>%s</h1>') % vals['name']
                    if vals.get('name')
                    else Markup('<h1 class="oe-hint"><br></h1>')
                )

            # Tracking
            vals.update({
                'last_edition_date': fields.Datetime.now(),
                'last_edition_uid': self.env.user.id,
            })

            # Sequencing
            parent_id = vals.get('parent_id', False)
            if parent_id:
                parent_ids.add(parent_id)
            if not vals.get('sequence'):
                vals_by_parent.setdefault(parent_id, []).append(vals)

            # Root articles must have internal_permission
            if not parent_id and not vals.get('internal_permission'):
                vals['internal_permission'] = 'write'

        # Check write access on parents
        if parent_ids:
            parents = self.browse(list(parent_ids))
            for parent in parents:
                if not parent.sudo().user_has_write_access and not self.env.su:
                    raise AccessError(
                        _("You cannot create an article under '%s' without write access.",
                          parent.display_name)
                    )

        # Compute max sequences per parent
        max_seq_by_parent = self._get_max_sequence_inside_parents(list(parent_ids)) if parent_ids else {}
        for parent_id, group_vals in vals_by_parent.items():
            current = max_seq_by_parent.get(parent_id, -1) + 1
            for v in group_vals:
                if 'sequence' not in v or not v['sequence']:
                    v['sequence'] = current
                    current += 1

        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle body versioning, parent change validation
        and automatic resequencing.
        """
        _resequence = False

        # Body change → version tracking
        if 'body' in vals:
            vals.update({
                'last_edition_date': fields.Datetime.now(),
                'last_edition_uid': self.env.user.id,
            })
            for article in self:
                if article.ids:
                    self.env['knowledge.article.version'].sudo().create({
                        'article_id': article.id,
                        'content': article.body or '',
                        'version_number': article.version,
                        'user_id': self.env.user.id,
                    })
                    # Increment version directly to avoid recursion
                    super(KnowledgeArticle, article).write({'version': article.version + 1})

        # Parent change → validate write access on new parent
        if 'parent_id' in vals:
            new_parent_id = vals.get('parent_id')
            if new_parent_id:
                new_parent = self.browse(new_parent_id)
                if not new_parent.sudo().user_has_write_access and not self.env.su:
                    raise AccessError(
                        _("You cannot move an article under '%s' without write access.",
                          new_parent.display_name)
                    )
            if 'sequence' not in vals:
                parent = self.browse(new_parent_id) if new_parent_id else self.env['knowledge.article']
                max_seq = self._get_max_sequence_inside_parents(parent.ids).get(parent.id, -1)
                vals['sequence'] = max_seq + 1
            else:
                _resequence = True

        result = super().write(vals)

        if _resequence:
            self.sudo()._resequence()

        return result

    def copy_data(self, default=None):
        """Append '(copy)' to the name when duplicating."""
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if default.get('name'):
            return vals_list
        for article, vals in zip(self, vals_list):
            if article.name:
                vals['name'] = _("%(article_name)s (copy)", article_name=article.name)
        return vals_list

    # ==================================================================
    # SEARCH / ORDERING
    # ==================================================================

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """Override to support ordering by ``is_user_favorite``.

        When ``is_user_favorite`` is part of the order, perform a two-step
        search: favorites first, then the rest.
        """
        if not order or 'is_user_favorite' not in order:
            return super().search_fetch(domain, field_names, offset, limit, order)

        order_items = [item.strip().lower() for item in (order or self._order).split(',')]
        favorite_asc = any('is_user_favorite asc' in item for item in order_items)

        # Step 1: user's favorites matching the domain
        fav_domain = expression.AND([
            [('favorite_ids.user_id', 'in', [self.env.uid])],
            domain,
        ])
        fav_order = ', '.join(item for item in order_items if 'is_user_favorite' not in item)
        fav_ids = super().search_fetch(fav_domain, field_names, order=fav_order).ids

        keep = fav_ids[offset:(offset + limit)] if limit else fav_ids[offset:]
        skip = fav_ids[:(offset + limit)] if limit else fav_ids

        if limit and len(keep) >= limit:
            return self.browse(keep)

        # Step 2: remaining articles
        other_limit = (limit - len(keep)) if limit else None
        other_offset = max(offset - len(fav_ids), 0) if offset else 0
        other_order = ', '.join(item for item in order_items if 'is_user_favorite' not in item)

        others = super().search_fetch(
            expression.AND([[('id', 'not in', skip)], domain]),
            field_names,
            other_offset,
            other_limit,
            other_order,
        )

        if favorite_asc:
            return others + self.browse(keep)
        return self.browse(keep) + others

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Group expand for kanban stages."""
        search_domain = [('id', 'in', stages.ids)]
        if self.env.context.get('default_parent_id'):
            search_domain = expression.OR([
                [('parent_id', '=', self.env.context['default_parent_id'])],
                search_domain,
            ])
        return stages.search(search_domain)

    # ==================================================================
    # ACTIONS
    # ==================================================================

    def action_toggle_favorite(self):
        """Toggle the favorite status for the current user."""
        to_fav_sudo = self.sudo().filtered(lambda a: not a.is_user_favorite)
        to_unfav = self - to_fav_sudo

        to_fav_sudo.write({
            'favorite_ids': [(0, 0, {'user_id': self.env.user.id})],
        })
        if to_unfav:
            self.env['knowledge.article.favorite'].sudo().search([
                ('article_id', 'in', to_unfav.ids),
                ('user_id', '=', self.env.user.id),
            ]).unlink()

        self.invalidate_recordset(fnames=['is_user_favorite', 'favorite_ids'])
        return self[0].is_user_favorite if self else False

    def action_toggle_like(self):
        """Add or remove the current user's partner from liked_by_ids."""
        self.ensure_one()
        partner = self.env.user.partner_id
        if partner in self.liked_by_ids:
            self.sudo().write({'liked_by_ids': [(3, partner.id)]})
        else:
            self.sudo().write({'liked_by_ids': [(4, partner.id)]})
        return {
            'you_liked': partner in self.liked_by_ids,
            'likes_count': len(self.liked_by_ids),
        }

    def action_send_to_trash(self):
        """Move article (and writable descendants) to trash."""
        articles = self + self._get_writable_descendants()
        articles.filtered('active').write({
            'active': False,
            'to_delete': True,
        })

    def action_unarchive(self):
        """Restore from trash."""
        self.write({
            'active': True,
            'to_delete': False,
        })

    def action_set_lock(self):
        self.is_locked = True

    def action_set_unlock(self):
        self.is_locked = False

    def action_make_private_copy(self):
        """Create a private copy: no members except current user, no children."""
        self.ensure_one()
        vals = {
            'name': _("%(article_name)s (copy)", article_name=self.name) if self.name else False,
            'body': self.body,
            'icon': self.icon,
            'cover_image_id': self.cover_image_id.id,
            'cover_image_position': self.cover_image_position,
            'full_width': self.full_width,
            'internal_permission': 'none',
            'parent_id': False,
            'is_desynchronized': False,
            'is_locked': False,
            'article_member_ids': [(0, 0, {
                'partner_id': self.env.user.partner_id.id,
                'permission': 'write',
            })],
        }
        return self.create(vals)

    def action_clone(self):
        """Duplicate with same parent / permissions."""
        self.ensure_one()
        if not self.user_has_write_access:
            return self.action_make_private_copy()

        vals = {
            'name': _("%(article_name)s (copy)", article_name=self.name) if self.name else False,
            'body': self.body,
            'icon': self.icon,
            'cover_image_id': self.cover_image_id.id,
            'cover_image_position': self.cover_image_position,
            'full_width': self.full_width,
            'internal_permission': self.internal_permission,
            'parent_id': self.parent_id.id,
            'is_article_item': self.is_article_item,
            'article_properties': self.article_properties,
            'is_desynchronized': False,
            'is_locked': False,
        }
        return self.create(vals)

    def action_home_page(self):
        """Return an action redirecting to the first accessible article."""
        article = self[0] if self else self._get_first_accessible_article()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'syntropy_knowledge.knowledge_article_action_form'
        )
        action['res_id'] = article.id if article else False
        return action

    def _get_first_accessible_article(self):
        """Find the first article the current user can access."""
        # Try favorites first
        favorite = self.env['knowledge.article.favorite'].search([
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if favorite and favorite.article_id.user_has_access:
            return favorite.article_id

        # Fall back to any accessible root article
        return self.search([
            ('parent_id', '=', False),
            ('user_has_access', '=', True),
        ], limit=1)

    # ==================================================================
    # MOVE / RESEQUENCE
    # ==================================================================

    def move_to(self, parent_id=False, before_article_id=False, category=False):
        """Move an article in the tree.

        :param int parent_id: id of the new parent article (0/False for root)
        :param int before_article_id: place the article before this sibling
        :param str category: target category ('workspace', 'private', 'shared')
        :return: True
        """
        self.ensure_one()
        before_article = (
            self.browse(before_article_id) if before_article_id
            else self.env['knowledge.article']
        )
        parent = (
            self.browse(parent_id) if parent_id
            else self.env['knowledge.article']
        )
        category = category or parent.category or before_article.category

        if not category:
            raise ValidationError(
                _("The destination placement of '%s' is ambiguous — specify the category.",
                  self.display_name)
            )

        if category == 'private' and not parent:
            return self._move_and_make_private(before_article=before_article)

        values = {'parent_id': parent_id}
        if before_article:
            values['sequence'] = before_article.sequence

        if parent_id and not self.parent_id:
            # Moving a root article under a parent: reset internal_permission
            values['internal_permission'] = False

        if not parent_id and category == 'workspace':
            values.update({
                'internal_permission': 'write',
                'is_desynchronized': False,
            })

        return self.write(values)

    def _move_and_make_private(self, before_article=False):
        """Convert article to a private root article."""
        vals = self._desync_access_from_parents_values()
        vals.update({
            'parent_id': False,
            'internal_permission': 'none',
            'is_desynchronized': False,
        })
        if before_article:
            vals['sequence'] = before_article.sequence

        # Remove all members except current user
        members_to_remove = self.article_member_ids.filtered(
            lambda m: m.partner_id != self.env.user.partner_id
        )
        member_cmds = [(2, m.id) for m in members_to_remove]
        if not self.article_member_ids.filtered(
            lambda m: m.partner_id == self.env.user.partner_id
        ):
            member_cmds.append((0, 0, {
                'partner_id': self.env.user.partner_id.id,
                'permission': 'write',
            }))
        vals['article_member_ids'] = member_cmds

        # Clear department/user grants
        vals.update({
            'view_department_ids': [(5, 0, 0)],
            'edit_department_ids': [(5, 0, 0)],
            'view_user_ids': [(5, 0, 0)],
            'edit_user_ids': [(5, 0, 0)],
        })

        return self.sudo().write(vals)

    def _desync_access_from_parents_values(self):
        """Return write values to desync an article from its parent's permissions."""
        self.ensure_one()
        return {
            'internal_permission': self.inherited_permission or 'write',
            'is_desynchronized': True,
        }

    def _resequence(self):
        """Resequence sibling articles when duplicates exist."""
        parent_ids = list(set(self.mapped('parent_id').ids))
        if any(not a.parent_id for a in self):
            parent_ids.append(False)

        all_children = self.search([('parent_id', 'in', parent_ids)])
        all_children = all_children.sorted(
            lambda a: (
                -1 * a.sequence,
                a in self,
                a.write_date,
                a.id,
            ),
            reverse=True,
        )

        for pid in parent_ids:
            siblings = all_children.filtered(lambda a: a.parent_id.id == pid)
            sequences = siblings.mapped('sequence')
            if len(sequences) == len(set(sequences)):
                continue
            # Find first duplicate
            dup_idx = next(
                idx for idx, s in enumerate(sequences) if s in sequences[:idx]
            )
            start_seq = sequences[dup_idx] + 1
            for i, child in enumerate(siblings[dup_idx:]):
                super(KnowledgeArticle, child).write({'sequence': i + start_seq})

    @api.model
    def _get_max_sequence_inside_parents(self, parent_ids):
        """Return a dict {parent_id: max_sequence} for the given parents."""
        if parent_ids:
            domain = [('parent_id', 'in', parent_ids)]
        else:
            domain = [('parent_id', '=', False)]
        results = self.env['knowledge.article'].sudo()._read_group(
            domain,
            ['parent_id'],
            ['sequence:max'],
        )
        return {parent.id: seq_max for parent, seq_max in results}

    # ==================================================================
    # SIDEBAR & SEARCH
    # ==================================================================

    def get_sidebar_articles(self, unfolded_ids=False):
        """Return structured data for the knowledge sidebar tree.

        :param list unfolded_ids: ids of articles whose children should be included
        :returns: dict with workspace_articles, shared_articles, private_articles,
                  favorite_articles
        """
        if unfolded_ids is False:
            unfolded_ids = []

        user = self.env.user
        Article = self.env['knowledge.article']

        # ---- Root articles by category --------------------------------
        root_domain = [
            ('parent_id', '=', False),
            ('user_has_access', '=', True),
        ]
        all_roots = Article.search(root_domain)

        workspace_roots = all_roots.filtered(lambda a: a.category == 'workspace')
        shared_roots = all_roots.filtered(lambda a: a.category == 'shared')
        private_roots = all_roots.filtered(lambda a: a.category == 'private')

        # ---- Favorites ------------------------------------------------
        favorites = self.env['knowledge.article.favorite'].search([
            ('user_id', '=', user.id),
        ])
        favorite_articles = favorites.article_id.filtered(lambda a: a.active and a.user_has_access)

        # ---- Children of unfolded articles ----------------------------
        unfolded_children = Article.browse()
        if unfolded_ids:
            unfolded_children = Article.search([
                ('parent_id', 'in', unfolded_ids),
                ('is_article_item', '=', False),
                ('user_has_access', '=', True),
            ])

        # If current article is set, also unfold ancestors
        if self and self.parent_id:
            ancestor_ids = self._get_ancestor_ids()
            extra_children = Article.search([
                ('parent_id', 'in', list(ancestor_ids)),
                ('is_article_item', '=', False),
                ('user_has_access', '=', True),
            ])
            unfolded_children |= extra_children

        # ---- Build result sets ----------------------------------------
        all_articles = workspace_roots | shared_roots | private_roots | favorite_articles | unfolded_children

        fields_to_read = [
            'id', 'name', 'icon', 'parent_id', 'has_article_children',
            'is_user_favorite', 'category', 'sequence', 'user_favorite_sequence',
        ]

        return {
            'articles': all_articles.read(fields_to_read, load=None),
            'favorite_ids': favorite_articles.ids,
        }

    def get_user_sorted_articles(self, search_term, limit=40):
        """Full-text search on name and body using simple ILIKE.

        :param str search_term: search terms
        :param int limit: max number of results
        :returns: list of dicts with id, name, icon, body_snippet
        """
        if not search_term:
            return self.search([
                ('is_user_favorite', '=', True),
            ], limit=limit).read(['id', 'name', 'icon'])

        # Escape ILIKE special characters
        pattern = '%' + re.sub(r'(%|_|\\)', r'\\\1', search_term) + '%'

        domain = [
            ('user_has_access', '=', True),
            '|',
            ('name', 'ilike', search_term),
            ('body', 'ilike', search_term),
        ]
        articles = self.search(domain, limit=limit)

        result = []
        for article in articles:
            snippet = ''
            if article.body and not is_html_empty(article.body):
                text = BeautifulSoup(article.body, 'html.parser').get_text(' ', strip=True)
                lower_text = text.lower()
                pos = lower_text.find(search_term.lower())
                if pos >= 0:
                    start = max(0, pos - 40)
                    end = min(len(text), pos + len(search_term) + 40)
                    snippet = ('...' if start > 0 else '') + text[start:end] + ('...' if end < len(text) else '')

            result.append({
                'id': article.id,
                'name': article.name,
                'icon': article.icon,
                'body_snippet': snippet,
            })
        return result

    # ==================================================================
    # MEMBERS / PERMISSIONS HELPERS
    # ==================================================================

    def invite_members(self, partner_ids, permission='read'):
        """Invite partners as members with the given permission.

        :param list partner_ids: list of res.partner ids
        :param str permission: 'read' or 'write'
        """
        self.ensure_one()
        self._add_members(partner_ids, permission)

    def _add_members(self, partner_ids, permission='read'):
        """Create or update member records for the given partners."""
        if isinstance(partner_ids, int):
            partner_ids = [partner_ids]
        if isinstance(partner_ids, models.BaseModel):
            partner_ids = partner_ids.ids

        existing = self.env['knowledge.article.member'].sudo().search([
            ('article_id', '=', self.id),
            ('partner_id', 'in', partner_ids),
        ])
        existing_partner_ids = existing.mapped('partner_id').ids

        # Update existing
        for member in existing:
            if ARTICLE_PERMISSION_LEVEL.get(permission, 0) > ARTICLE_PERMISSION_LEVEL.get(member.permission, 0):
                member.permission = permission

        # Create new
        new_partners = set(partner_ids) - set(existing_partner_ids)
        for pid in new_partners:
            self.env['knowledge.article.member'].sudo().create({
                'article_id': self.id,
                'partner_id': pid,
                'permission': permission,
            })

    def _set_internal_permission(self, permission):
        """Set the internal_permission and desync if this is a child article."""
        self.ensure_one()
        vals = {'internal_permission': permission}
        if self.parent_id and not self.is_desynchronized:
            vals['is_desynchronized'] = True
        self.write(vals)

    def _set_member_permission(self, member_id, permission):
        """Update a specific member's permission."""
        member = self.env['knowledge.article.member'].browse(member_id)
        if member.article_id != self:
            raise ValidationError(_("Member does not belong to this article."))
        member.sudo().write({'permission': permission})

    def _remove_member(self, member_id):
        """Remove a member record."""
        member = self.env['knowledge.article.member'].browse(member_id)
        if member.article_id != self:
            raise ValidationError(_("Member does not belong to this article."))
        member.sudo().unlink()

    def _get_partner_member_permissions(self, partner):
        """Return a dict {article_id: permission} for the given partner,
        considering membership defined on the article or any of its ancestors
        (via parent_path).

        The closest (most specific) membership wins.
        """
        if not self.ids:
            return {}

        self.env.cr.execute(SQL("""
            WITH article_ancestors AS (
                SELECT a.id AS article_id,
                       unnest(string_to_array(trim(trailing '/' from a.parent_path), '/'))::int AS ancestor_id
                  FROM knowledge_article a
                 WHERE a.id IN %(article_ids)s
            )
            SELECT aa.article_id,
                   kam.permission,
                   aa.ancestor_id
              FROM article_ancestors aa
              JOIN knowledge_article_member kam
                ON kam.article_id = aa.ancestor_id
               AND kam.partner_id = %(partner_id)s
        """, article_ids=tuple(self.ids), partner_id=partner.id))

        rows = self.env.cr.fetchall()
        if not rows:
            return {}

        # For each article, pick the closest ancestor's permission
        # (the one with the highest ancestor_id — closer in the tree)
        result = {}
        for article_id, permission, ancestor_id in rows:
            if article_id not in result or ancestor_id > result[article_id][1]:
                result[article_id] = (permission, ancestor_id)

        return {aid: perm for aid, (perm, _) in result.items()}

    # ==================================================================
    # HIERARCHY HELPERS
    # ==================================================================

    def get_article_hierarchy(self):
        """Return the ancestor chain from root to immediate parent.

        :returns: list of dicts with display_name and user_has_access
        """
        self.ensure_one()
        ancestor_ids = self._get_ancestor_ids()
        return self.sudo().browse(reversed(list(ancestor_ids))).read(
            ['display_name', 'user_has_access']
        )

    def _get_ancestor_ids(self):
        """Return a set of ancestor article IDs from parent_path, excluding self."""
        self.ensure_one()
        if not self.parent_path:
            return set()
        parts = self.parent_path.strip('/').split('/')
        ids = {int(p) for p in parts if p}
        ids.discard(self.id)
        return ids

    def _get_writable_descendants(self):
        """Return all descendant articles the current user can write on."""
        return self.search([
            ('id', 'child_of', self.ids),
            ('id', 'not in', self.ids),
            ('user_has_write_access', '=', True),
        ])

    # ==================================================================
    # ACCESS HELPERS
    # ==================================================================

    def can_view(self):
        """Check if current user can view this article (combining all systems)."""
        self.ensure_one()
        if self.env.su or self.env.user.has_group('base.group_system'):
            return True
        return self.user_has_access

    def can_edit(self):
        """Check if current user can edit this article (combining all systems)."""
        self.ensure_one()
        if self.env.su or self.env.user.has_group('base.group_system'):
            return True
        return self.user_has_write_access

    def has_access(self, mode='read'):
        """Check access for a recordset.

        :param str mode: 'read' or 'write'
        :returns: True if all articles in self are accessible
        """
        if self.env.su:
            return True
        for article in self:
            perm = article.user_permission or 'none'
            if mode == 'write' and perm != 'write':
                return False
            if mode == 'read' and perm not in ('read', 'write'):
                return False
        return True

    # ==================================================================
    # CONTENT HELPERS
    # ==================================================================

    @staticmethod
    def clean_article_content(content):
        """Sanitize HTML content using BeautifulSoup.

        Removes file:// images and other potentially dangerous elements.
        """
        if not content:
            return content
        soup = BeautifulSoup(content, 'html.parser')
        # Remove file:// protocol images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.startswith('file://'):
                img.decompose()
        return str(soup)

    # ==================================================================
    # CRON / AUTOVACUUM
    # ==================================================================

    @api.autovacuum
    def _gc_trashed_articles(self):
        """Delete articles that have been in trash beyond the configured limit."""
        limit_days = self.env['ir.config_parameter'].sudo().get_param(
            'knowledge.knowledge_article_trash_limit_days',
        )
        try:
            limit_days = int(limit_days)
        except (ValueError, TypeError):
            limit_days = self.DEFAULT_ARTICLE_TRASH_LIMIT_DAYS

        cutoff = datetime.utcnow() - timedelta(days=limit_days)
        domain = [
            ('write_date', '<', cutoff),
            ('to_delete', '=', True),
        ]
        return self.with_context(active_test=False).search(domain, limit=100).unlink()
