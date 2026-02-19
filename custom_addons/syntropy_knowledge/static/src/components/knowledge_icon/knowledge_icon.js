/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { getRandomEmoji } from "../../js/knowledge_utils";

const EMOJI_CATEGORIES = {
    "Smileys": ["😀","😃","😄","😁","😆","😅","🤣","😂","🙂","😊","😇","🥰","😍"],
    "Objects": ["📄","📝","📋","📌","📎","📂","📁","🗂️","📚","📖","✏️","🖊️","📐","📏","🔖","🏷️"],
    "Symbols": ["💡","🎯","⭐","🌟","✅","❌","❓","❗","💬","💭","🔔","🔒","🔑","⚡","🔥"],
    "Nature": ["🌍","🌎","🌏","🌲","🌳","🌴","🌺","🌻","🌸","🍀","🌈","☀️","⛅","🌙"],
    "Tech": ["💻","🖥️","📱","⌨️","🖱️","💾","📡","🔧","🔨","⚙️","🧪","🔬","🧲","🎮"],
    "Misc": ["🚀","🏗️","🎨","📊","📈","🎵","🎶","🏆","🎪","🎭","🎬","🎤"],
};

export class KnowledgeIcon extends Component {
    static template = "syntropy_knowledge.KnowledgeIcon";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            showPicker: false,
            searchTerm: "",
        });
    }

    get currentIcon() {
        return this.props.record.data.icon || "";
    }

    get emojiCategories() {
        return EMOJI_CATEGORIES;
    }

    togglePicker() {
        this.state.showPicker = !this.state.showPicker;
    }

    async selectEmoji(emoji) {
        await this.orm.write("knowledge.article", [this.props.record.resId], { icon: emoji });
        await this.props.record.load();
        this.state.showPicker = false;
    }

    async removeIcon() {
        await this.orm.write("knowledge.article", [this.props.record.resId], { icon: false });
        await this.props.record.load();
        this.state.showPicker = false;
    }

    async setRandomIcon() {
        await this.selectEmoji(getRandomEmoji());
    }
}

registry.category("view_widgets").add("knowledge_icon", {
    component: KnowledgeIcon,
});
