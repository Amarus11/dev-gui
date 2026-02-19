/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class PermissionPanel extends Component {
    static template = "syntropy_knowledge.PermissionPanel";
    static props = {
        articleId: Number,
        onClose: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        this.state = useState({
            loading: true,
            data: null,
            invitePartnerInput: "",
        });

        onMounted(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.rpc("/knowledge/get_article_permission_panel_data", {
                article_id: this.props.articleId,
            });
        } catch (e) {
            console.error("Failed to load permission data:", e);
        }
        this.state.loading = false;
    }

    get internalPermissionLabel() {
        if (!this.state.data) return "";
        const labels = {
            write: _t("Can write"),
            read: _t("Can read"),
            none: _t("No access"),
        };
        return labels[this.state.data.internal_permission] || "";
    }

    get members() {
        return this.state.data?.members || [];
    }

    get viewDepartments() {
        return this.state.data?.view_departments || [];
    }

    get editDepartments() {
        return this.state.data?.edit_departments || [];
    }

    // ------------------------------------------------------------------
    // Actions
    // ------------------------------------------------------------------

    async setInternalPermission(permission) {
        await this.rpc("/knowledge/article/set_internal_permission", {
            article_id: this.props.articleId,
            permission,
        });
        await this.loadData();
    }

    async setMemberPermission(memberId, permission) {
        await this.rpc("/knowledge/article/set_member_permission", {
            article_id: this.props.articleId,
            member_id: memberId,
            permission,
        });
        await this.loadData();
    }

    async removeMember(memberId) {
        await this.rpc("/knowledge/article/remove_member", {
            article_id: this.props.articleId,
            member_id: memberId,
        });
        await this.loadData();
    }

    onInviteMembers() {
        this.env.services.action.doAction("syntropy_knowledge.knowledge_invite_action", {
            additionalContext: {
                default_article_id: this.props.articleId,
            },
            onClose: () => this.loadData(),
        });
    }

    async onCopyShareLink() {
        const token = this.state.data?.share_token;
        if (token) {
            const url = `${window.location.origin}/knowledge/article/${token}`;
            try {
                await navigator.clipboard.writeText(url);
                this.notificationService.add(_t("Link copied!"), { type: "success" });
            } catch {
                this.notificationService.add(url, { title: _t("Share Link"), type: "info", sticky: true });
            }
        }
    }
}
