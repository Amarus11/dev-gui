/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class KnowledgeCommentsPanel extends Component {
    static template = "syntropy_knowledge.CommentsPanel";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");

        this.state = useState({
            threads: [],
            loading: true,
            filter: "open", // "open", "resolved", "all"
            newCommentText: "",
        });

        onMounted(() => this.loadThreads());
    }

    get articleId() {
        return this.props.record.resId;
    }

    get filteredThreads() {
        if (this.state.filter === "open") {
            return this.state.threads.filter(t => !t.is_resolved);
        } else if (this.state.filter === "resolved") {
            return this.state.threads.filter(t => t.is_resolved);
        }
        return this.state.threads;
    }

    async loadThreads() {
        this.state.loading = true;
        try {
            const threads = await this.orm.searchRead(
                "knowledge.article.thread",
                [["article_id", "=", this.articleId]],
                ["id", "article_anchor_text", "is_resolved", "write_date"],
                { order: "write_date desc" },
            );

            // Load messages for each thread
            if (threads.length > 0) {
                const threadIds = threads.map(t => t.id);
                const messagesData = await this.rpc("/knowledge/threads/messages", {
                    thread_ids: threadIds,
                    limit: 10,
                });
                for (const thread of threads) {
                    thread.messages = messagesData[thread.id]?.messages || [];
                }
            }

            this.state.threads = threads;
        } catch (e) {
            console.error("Failed to load threads:", e);
        }
        this.state.loading = false;
    }

    setFilter(filter) {
        this.state.filter = filter;
    }

    async createThread() {
        if (!this.state.newCommentText.trim()) return;
        await this.rpc("/knowledge/thread/create", {
            article_id: this.articleId,
            anchor_text: this.state.newCommentText,
        });
        this.state.newCommentText = "";
        await this.loadThreads();
    }

    async toggleResolve(threadId) {
        await this.rpc("/knowledge/thread/resolve", { thread_id: threadId });
        await this.loadThreads();
    }
}

registry.category("view_widgets").add("knowledge_comments_panel", {
    component: KnowledgeCommentsPanel,
});
