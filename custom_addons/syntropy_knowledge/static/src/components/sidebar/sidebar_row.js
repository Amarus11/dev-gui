/** @odoo-module **/

import { Component } from "@odoo/owl";

export class KnowledgeSidebarRow extends Component {
    static template = "syntropy_knowledge.SidebarRow";
    static components = { KnowledgeSidebarRow };  // Self-reference for recursion
    static props = {
        article: Object,
        articles: Object,
        activeArticleId: { type: [Number, Boolean] },
        unfoldedIds: Object,
        sidebar: Object,
        depth: Number,
        isFavoriteRow: { type: Boolean, optional: true },
    };

    get isActive() {
        return this.props.activeArticleId === this.props.article.id;
    }

    get isUnfolded() {
        return this.props.unfoldedIds.has(this.props.article.id);
    }

    get hasChildren() {
        return this.props.article.has_article_children;
    }

    get childrenIds() {
        return this.props.sidebar.getChildrenIds(this.props.article.id);
    }

    get indentStyle() {
        return `padding-left: ${12 + this.props.depth * 20}px`;
    }

    onToggleFold(ev) {
        ev.stopPropagation();
        this.props.sidebar.toggleFold(this.props.article.id);
    }

    onClick() {
        this.props.sidebar.openArticle(this.props.article.id);
    }

    onCreateChild(ev) {
        ev.stopPropagation();
        this.props.sidebar.createChildArticle(this.props.article.id);
    }

    onToggleFavorite(ev) {
        ev.stopPropagation();
        this.props.sidebar.toggleFavorite(this.props.article.id);
    }
}
