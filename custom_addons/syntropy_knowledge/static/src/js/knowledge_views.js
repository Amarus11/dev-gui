/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { KnowledgeArticleFormController } from "./knowledge_controller";
import { KnowledgeArticleFormRenderer } from "./knowledge_renderers";

export const knowledgeArticleFormView = {
    ...formView,
    Controller: KnowledgeArticleFormController,
    Renderer: KnowledgeArticleFormRenderer,
    display: {
        controlPanel: false,
    },
};

registry.category("views").add("knowledge_article_view_form", knowledgeArticleFormView);
