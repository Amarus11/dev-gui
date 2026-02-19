/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class KnowledgeTopbar extends Component {
    static template = "syntropy_knowledge.Topbar";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        this.state = useState({
            showSharePanel: false,
            showMoreMenu: false,
        });
    }

    get record() {
        return this.props.record;
    }

    get articleId() {
        return this.record.resId;
    }

    get articleName() {
        return this.record.data.name || _t("Untitled");
    }

    get articleIcon() {
        return this.record.data.icon || "";
    }

    get isLocked() {
        return this.record.data.is_locked;
    }

    get isFavorite() {
        return this.record.data.is_user_favorite;
    }

    get category() {
        return this.record.data.category;
    }

    get categoryLabel() {
        const labels = {
            workspace: _t("Workspace"),
            shared: _t("Shared"),
            private: _t("Private"),
        };
        return labels[this.category] || "";
    }

    get categoryIcon() {
        const icons = {
            workspace: "fa-globe",
            shared: "fa-users",
            private: "fa-lock",
        };
        return icons[this.category] || "fa-file";
    }

    get hasWriteAccess() {
        return this.record.data.user_has_write_access;
    }

    // ------------------------------------------------------------------
    // Actions
    // ------------------------------------------------------------------

    async onNewArticle() {
        if (this.env.createArticle) {
            await this.env.createArticle({ category: "private" });
        }
    }

    toggleSharePanel() {
        this.state.showSharePanel = !this.state.showSharePanel;
    }

    toggleMoreMenu() {
        this.state.showMoreMenu = !this.state.showMoreMenu;
    }

    async onToggleFavorite() {
        await this.orm.call("knowledge.article", "action_toggle_favorite", [[this.articleId]]);
        await this.record.load();
    }

    async onToggleLock() {
        if (this.isLocked) {
            await this.orm.call("knowledge.article", "action_set_unlock", [[this.articleId]]);
        } else {
            await this.orm.call("knowledge.article", "action_set_lock", [[this.articleId]]);
        }
        await this.record.load();
    }

    async onToggleFullWidth() {
        const current = this.record.data.full_width;
        await this.orm.write("knowledge.article", [this.articleId], { full_width: !current });
        await this.record.load();
    }

    async onTrash() {
        await this.orm.call("knowledge.article", "action_send_to_trash", [[this.articleId]]);
        // Navigate to home
        if (this.env.openArticle) {
            const result = await this.orm.call("knowledge.article", "action_home_page", []);
            if (result.res_id) {
                await this.env.openArticle(result.res_id);
            }
        }
        this.state.showMoreMenu = false;
    }

    async onDuplicate() {
        const newIds = await this.orm.call("knowledge.article", "copy", [[this.articleId]]);
        const newId = Array.isArray(newIds) ? newIds[0] : newIds;
        if (this.env.openArticle && newId) {
            await this.env.openArticle(newId);
        }
        this.state.showMoreMenu = false;
    }

    async onExportPdf() {
        // Use html2pdf.js to export the article body
        const bodyEl = document.querySelector(".o_knowledge_body .o_field_html .odoo-editor-editable, .o_knowledge_body .o_field_html .o_readonly");
        if (!bodyEl) {
            this.notificationService.add(_t("Nothing to export"), { type: "warning" });
            return;
        }
        if (typeof html2pdf !== "undefined") {
            const opt = {
                margin: [10, 10],
                filename: `${this.articleName}.pdf`,
                image: { type: "jpeg", quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
            };
            html2pdf().set(opt).from(bodyEl).save();
        } else {
            this.notificationService.add(_t("PDF export not available"), { type: "warning" });
        }
        this.state.showMoreMenu = false;
    }

    onMoveArticle() {
        this.state.showMoreMenu = false;
        // Open move dialog via the dialog service
        import("../move_article_dialog/move_article_dialog").then(({ MoveArticleDialog }) => {
            this.dialogService.add(MoveArticleDialog, {
                articleId: this.articleId,
                articleName: this.articleName,
                onMoved: () => this.record.load(),
            });
        });
    }

    async onCopyShareLink() {
        const token = this.record.data.share_token;
        if (token) {
            const url = `${window.location.origin}/knowledge/article/${token}`;
            try {
                await navigator.clipboard.writeText(url);
                this.notificationService.add(_t("Share link copied to clipboard"), { type: "success" });
            } catch {
                this.notificationService.add(url, { title: _t("Share Link"), type: "info", sticky: true });
            }
        }
        this.state.showMoreMenu = false;
    }

    async onTogglePublish() {
        const current = this.record.data.is_published;
        await this.orm.write("knowledge.article", [this.articleId], { is_published: !current });
        await this.record.load();
        this.notificationService.add(
            current ? _t("Article unpublished") : _t("Article published"),
            { type: "success" },
        );
    }

    onViewVersionHistory() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Version History"),
            res_model: "knowledge.article.version",
            view_mode: "list,form",
            domain: [["article_id", "=", this.articleId]],
            context: { default_article_id: this.articleId },
        });
        this.state.showMoreMenu = false;
    }
}

registry.category("view_widgets").add("knowledge_topbar", {
    component: KnowledgeTopbar,
});
