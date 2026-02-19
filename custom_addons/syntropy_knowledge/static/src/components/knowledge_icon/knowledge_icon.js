/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
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
    static props = {
        ...standardFieldProps,
        allow_random_icon_selection: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            showPicker: false,
            searchTerm: "",
        });
    }

    get currentIcon() {
        return this.props.record.data[this.props.name] || "";
    }

    get emojiCategories() {
        return EMOJI_CATEGORIES;
    }

    togglePicker() {
        this.state.showPicker = !this.state.showPicker;
    }

    async selectEmoji(emoji) {
        await this.props.record.update({ [this.props.name]: emoji });
        this.state.showPicker = false;
    }

    async removeIcon() {
        await this.props.record.update({ [this.props.name]: false });
        this.state.showPicker = false;
    }

    async setRandomIcon() {
        await this.selectEmoji(getRandomEmoji());
    }
}

export const knowledgeIconField = {
    component: KnowledgeIcon,
    supportedTypes: ["char"],
    extractProps: ({ attrs }) => ({
        allow_random_icon_selection: attrs.allow_random_icon_selection,
    }),
};

registry.category("fields").add("knowledge_icon", knowledgeIconField);
