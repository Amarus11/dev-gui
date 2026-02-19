/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class KnowledgeCoverDialog extends Component {
    static template = "syntropy_knowledge.KnowledgeCoverDialog";
    static components = { Dialog };
    static props = {
        articleId: Number,
        onSelected: { type: Function, optional: true },
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notificationService = useService("notification");
        this.state = useState({
            uploading: false,
        });
    }

    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        this.state.uploading = true;
        try {
            // Upload as attachment
            const reader = new FileReader();
            const dataPromise = new Promise((resolve) => {
                reader.onload = () => resolve(reader.result.split(",")[1]);
            });
            reader.readAsDataURL(file);
            const data = await dataPromise;

            const attachmentIds = await this.orm.call("ir.attachment", "create", [[{
                name: file.name,
                type: "binary",
                datas: data,
                res_model: "knowledge.cover",
            }]]);
            const attachmentId = Array.isArray(attachmentIds) ? attachmentIds[0] : attachmentIds;

            // Create cover record
            const coverIds = await this.orm.call("knowledge.cover", "create", [[{
                attachment_id: attachmentId,
            }]]);
            const coverId = Array.isArray(coverIds) ? coverIds[0] : coverIds;

            // Link to article
            await this.orm.write("knowledge.article", [this.props.articleId], {
                cover_image_id: coverId,
            });

            if (this.props.onSelected) {
                await this.props.onSelected();
            }
            this.props.close();
        } catch (e) {
            this.notificationService.add(_t("Failed to upload cover image"), { type: "danger" });
        }
        this.state.uploading = false;
    }

    async onUrlSubmit() {
        const urlInput = document.querySelector(".o_knowledge_cover_url_input");
        const url = urlInput?.value;
        if (!url) return;

        this.state.uploading = true;
        try {
            const attachmentIds = await this.orm.call("ir.attachment", "create", [[{
                name: "Cover Image",
                type: "url",
                url: url,
                res_model: "knowledge.cover",
            }]]);
            const attachmentId = Array.isArray(attachmentIds) ? attachmentIds[0] : attachmentIds;

            const coverIds = await this.orm.call("knowledge.cover", "create", [[{
                attachment_id: attachmentId,
            }]]);
            const coverId = Array.isArray(coverIds) ? coverIds[0] : coverIds;

            await this.orm.write("knowledge.article", [this.props.articleId], {
                cover_image_id: coverId,
            });

            if (this.props.onSelected) {
                await this.props.onSelected();
            }
            this.props.close();
        } catch (e) {
            this.notificationService.add(_t("Failed to set cover from URL"), { type: "danger" });
        }
        this.state.uploading = false;
    }
}
