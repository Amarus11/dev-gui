/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class KnowledgeCover extends Component {
    static template = "syntropy_knowledge.KnowledgeCover";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.state = useState({ dragging: false, startY: 0, startPos: 0 });
    }

    get coverUrl() {
        return this.props.record.data.cover_image_url;
    }

    get coverPosition() {
        return this.props.record.data.cover_image_position || 50;
    }

    get hasCover() {
        return !!this.coverUrl;
    }

    async onRemoveCover() {
        await this.orm.write("knowledge.article", [this.props.record.resId], {
            cover_image_id: false,
        });
        await this.props.record.load();
    }

    onChangeCover() {
        import("./knowledge_cover_dialog").then(({ KnowledgeCoverDialog }) => {
            this.dialogService.add(KnowledgeCoverDialog, {
                articleId: this.props.record.resId,
                onSelected: () => this.props.record.load(),
            });
        });
    }

    // Cover position drag
    onPointerDown(ev) {
        if (!this.hasCover) return;
        this.state.dragging = true;
        this.state.startY = ev.clientY;
        this.state.startPos = this.coverPosition;
        document.addEventListener("pointermove", this._onPointerMove);
        document.addEventListener("pointerup", this._onPointerUp);
    }

    _onPointerMove = (ev) => {
        if (!this.state.dragging) return;
        const delta = ev.clientY - this.state.startY;
        const newPos = Math.max(0, Math.min(100, this.state.startPos + delta * 0.5));
        // Live update via style
        const coverEl = ev.target.closest(".o_knowledge_cover_image");
        if (coverEl) {
            coverEl.style.objectPosition = `center ${newPos}%`;
        }
    };

    _onPointerUp = async (ev) => {
        if (!this.state.dragging) return;
        this.state.dragging = false;
        const delta = ev.clientY - this.state.startY;
        const newPos = Math.max(0, Math.min(100, this.state.startPos + delta * 0.5));
        document.removeEventListener("pointermove", this._onPointerMove);
        document.removeEventListener("pointerup", this._onPointerUp);
        await this.orm.write("knowledge.article", [this.props.record.resId], {
            cover_image_position: newPos,
        });
    };
}

registry.category("view_widgets").add("knowledge_cover", {
    component: KnowledgeCover,
});
