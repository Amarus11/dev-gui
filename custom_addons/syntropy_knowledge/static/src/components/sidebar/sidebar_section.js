/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { KnowledgeSidebarRow } from "./sidebar_row";

export class KnowledgeSidebarSection extends Component {
    static template = "syntropy_knowledge.SidebarSection";
    static components = { KnowledgeSidebarRow };
    static props = {
        title: String,
        icon: String,
        articleIds: Array,
        articles: Object,
        activeArticleId: { type: [Number, Boolean] },
        unfoldedIds: Object,
        sidebar: Object,
        canCreate: { type: Boolean, optional: true },
        createCategory: { type: String, optional: true },
        isFavoriteSection: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            collapsed: false,
        });
    }

    toggleCollapse() {
        this.state.collapsed = !this.state.collapsed;
    }

    onCreateClick() {
        if (this.props.sidebar && this.props.createCategory) {
            this.props.sidebar.createArticle(this.props.createCategory);
        }
    }
}
