/** @odoo-module **/

import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class MoveArticleDialog extends Component {
    static template = "syntropy_knowledge.MoveArticleDialog";
    static components = { Dialog };
    static props = {
        articleId: Number,
        articleName: { type: String, optional: true },
        onMoved: { type: Function, optional: true },
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.searchInputRef = useRef("searchInput");

        this.state = useState({
            articles: [],
            loading: true,
            selectedId: undefined,
            searchTerm: "",
        });

        onMounted(() => this.loadArticles());
    }

    async loadArticles(searchTerm = "") {
        this.state.loading = true;
        try {
            const domain = [
                ["id", "!=", this.props.articleId],
                ["is_article_item", "=", false],
            ];
            if (searchTerm) {
                domain.push(["name", "ilike", searchTerm]);
            }
            const articles = await this.orm.searchRead(
                "knowledge.article",
                domain,
                ["id", "name", "icon", "parent_id", "parent_path"],
                { limit: 100, order: "parent_path, sequence, id" },
            );
            // Compute display level from parent_path
            for (const article of articles) {
                const path = article.parent_path || "";
                const parts = path.split("/").filter(Boolean);
                article.level = Math.max(0, parts.length - 1);
            }
            this.state.articles = articles;
        } catch (e) {
            console.error("Failed to load articles:", e);
        }
        this.state.loading = false;
    }

    selectTarget(articleId) {
        this.state.selectedId = articleId;
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        this.loadArticles(this.state.searchTerm);
    }

    async onConfirm() {
        if (this.state.selectedId === undefined) return;
        try {
            const parentId = this.state.selectedId === false ? false : this.state.selectedId;
            await this.orm.write("knowledge.article", [this.props.articleId], {
                parent_id: parentId,
            });
            this.notificationService.add(_t("Article moved successfully"), { type: "success" });
            if (this.props.onMoved) {
                await this.props.onMoved();
            }
            this.props.close();
        } catch (e) {
            this.notificationService.add(_t("Failed to move article"), { type: "danger" });
        }
    }
}
