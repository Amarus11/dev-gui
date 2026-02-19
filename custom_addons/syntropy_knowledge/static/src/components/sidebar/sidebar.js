/** @odoo-module **/

import { Component, useState, useRef, useEffect, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { KnowledgeSidebarSection } from "./sidebar_section";
import { useDebounced } from "@web/core/utils/timing";

export class KnowledgeSidebar extends Component {
    static template = "syntropy_knowledge.Sidebar";
    static components = { KnowledgeSidebarSection };
    static props = {
        record: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.sidebarRef = useRef("sidebar");

        this.state = useState({
            articles: {},               // flat map: id -> article data
            favoriteIds: [],
            workspaceIds: [],
            sharedIds: [],
            privateIds: [],
            unfoldedIds: new Set(JSON.parse(localStorage.getItem("knowledge_unfolded") || "[]")),
            searchTerm: "",
            searchResults: [],
            isSearching: false,
            loading: true,
            sidebarWidth: parseInt(localStorage.getItem("knowledge_sidebar_width")) || 280,
        });

        this.debouncedSearch = useDebounced(this._performSearch.bind(this), 300);

        onMounted(() => {
            this.loadArticles();
            this._initResizer();
        });

        // Persist unfolded IDs on cleanup
        onWillUnmount(() => {
            localStorage.setItem("knowledge_unfolded", JSON.stringify([...this.state.unfoldedIds]));
        });

        // Watch for record changes to highlight active article
        useEffect(
            () => {
                const resId = this.props.record?.resId;
                if (resId && this.state.articles[resId]) {
                    this._ensureVisible(resId);
                }
            },
            () => [this.props.record?.resId],
        );
    }

    get activeArticleId() {
        return this.props.record?.resId || false;
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------

    async loadArticles() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "knowledge.article",
                "get_sidebar_articles",
                [],
                { unfolded_ids: [...this.state.unfoldedIds] },
            );
            // data = { articles: {id: {...}}, workspace_ids, shared_ids, private_ids, favorite_ids }
            this.state.articles = data.articles || {};
            this.state.workspaceIds = data.workspace_ids || [];
            this.state.sharedIds = data.shared_ids || [];
            this.state.privateIds = data.private_ids || [];
            this.state.favoriteIds = data.favorite_ids || [];
        } catch (e) {
            console.error("Failed to load sidebar articles:", e);
        }
        this.state.loading = false;
    }

    async loadChildren(articleId) {
        const children = await this.orm.call(
            "knowledge.article",
            "search_read",
            [[["parent_id", "=", articleId], ["is_article_item", "=", false]]],
            {
                fields: ["id", "name", "icon", "parent_id", "category", "sequence", "is_user_favorite", "child_ids"],
                order: "sequence, id",
            },
        );
        for (const child of children) {
            this.state.articles[child.id] = {
                ...child,
                parent_id: child.parent_id ? child.parent_id[0] : false,
                has_article_children: child.child_ids && child.child_ids.length > 0,
                children_loaded: false,
            };
        }
        if (this.state.articles[articleId]) {
            this.state.articles[articleId].children_loaded = true;
        }
    }

    // ------------------------------------------------------------------
    // Fold / unfold
    // ------------------------------------------------------------------

    async toggleFold(articleId) {
        if (this.state.unfoldedIds.has(articleId)) {
            this.state.unfoldedIds.delete(articleId);
        } else {
            this.state.unfoldedIds.add(articleId);
            const article = this.state.articles[articleId];
            if (article && !article.children_loaded && article.has_article_children) {
                await this.loadChildren(articleId);
            }
        }
        localStorage.setItem("knowledge_unfolded", JSON.stringify([...this.state.unfoldedIds]));
    }

    isUnfolded(articleId) {
        return this.state.unfoldedIds.has(articleId);
    }

    // ------------------------------------------------------------------
    // Article actions
    // ------------------------------------------------------------------

    openArticle(articleId) {
        if (this.env.createArticle) {
            // We're inside a knowledge form view
            this.env.openArticle(articleId);
        } else {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "knowledge.article",
                res_id: articleId,
                views: [[false, "form"]],
                view_mode: "form",
            }, {
                clearBreadcrumbs: true,
            });
        }
    }

    async createArticle(category = "private", parentId = false) {
        if (this.env.createArticle) {
            await this.env.createArticle({ category, parentId });
        }
        await this.loadArticles();
    }

    async createChildArticle(parentId) {
        await this.createArticle(false, parentId);
    }

    async toggleFavorite(articleId) {
        await this.orm.call("knowledge.article", "action_toggle_favorite", [[articleId]]);
        await this.loadArticles();
    }

    // ------------------------------------------------------------------
    // Search
    // ------------------------------------------------------------------

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        if (this.state.searchTerm.length >= 2) {
            this.state.isSearching = true;
            this.debouncedSearch();
        } else {
            this.state.isSearching = false;
            this.state.searchResults = [];
        }
    }

    async _performSearch() {
        if (!this.state.searchTerm || this.state.searchTerm.length < 2) return;
        const results = await this.orm.call(
            "knowledge.article",
            "get_user_sorted_articles",
            [this.state.searchTerm],
            { limit: 20 },
        );
        this.state.searchResults = results;
    }

    clearSearch() {
        this.state.searchTerm = "";
        this.state.isSearching = false;
        this.state.searchResults = [];
    }

    // ------------------------------------------------------------------
    // Resizer
    // ------------------------------------------------------------------

    _initResizer() {
        const resizer = this.sidebarRef?.el?.parentElement?.querySelector(".o_knowledge_sidebar_resizer");
        if (!resizer) return;

        let startX, startWidth;

        const onPointerMove = (e) => {
            const newWidth = Math.max(200, Math.min(500, startWidth + e.clientX - startX));
            this.state.sidebarWidth = newWidth;
            if (this.sidebarRef.el) {
                this.sidebarRef.el.style.width = newWidth + "px";
            }
        };

        const onPointerUp = () => {
            document.removeEventListener("pointermove", onPointerMove);
            document.removeEventListener("pointerup", onPointerUp);
            localStorage.setItem("knowledge_sidebar_width", String(this.state.sidebarWidth));
        };

        resizer.addEventListener("pointerdown", (e) => {
            startX = e.clientX;
            startWidth = this.state.sidebarWidth;
            document.addEventListener("pointermove", onPointerMove);
            document.addEventListener("pointerup", onPointerUp);
        });
    }

    _ensureVisible(articleId) {
        // Auto-expand parents to make this article visible
        const article = this.state.articles[articleId];
        if (!article) return;
        let parentId = article.parent_id;
        while (parentId) {
            if (!this.state.unfoldedIds.has(parentId)) {
                this.state.unfoldedIds.add(parentId);
            }
            const parent = this.state.articles[parentId];
            parentId = parent ? parent.parent_id : false;
        }
    }

    // ------------------------------------------------------------------
    // Getters for sections
    // ------------------------------------------------------------------

    getChildrenIds(parentId) {
        return Object.values(this.state.articles)
            .filter(a => a.parent_id === parentId)
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0))
            .map(a => a.id);
    }
}
