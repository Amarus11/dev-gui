/** @odoo-module **/

// Random emoji selection for new articles
const EMOJIS = [
    "📄", "📝", "📋", "📌", "📎", "📂", "📁", "🗂️", "📚", "📖",
    "✏️", "🖊️", "📐", "📏", "🔖", "🏷️", "💡", "🎯", "⭐", "🌟",
    "🚀", "💻", "🔧", "🎨", "📊", "📈", "🔬", "🧪", "🏗️", "🌍",
];

/**
 * Get a random emoji suitable for article icons.
 * @returns {string}
 */
export function getRandomEmoji() {
    return EMOJIS[Math.floor(Math.random() * EMOJIS.length)];
}

/**
 * Extract a snippet from HTML content.
 * @param {string} html
 * @param {number} maxLength
 * @returns {string}
 */
export function htmlToSnippet(html, maxLength = 200) {
    if (!html) return "";
    const div = document.createElement("div");
    div.innerHTML = html;
    const text = div.textContent || div.innerText || "";
    return text.length > maxLength ? text.substring(0, maxLength) + "…" : text;
}

/**
 * Debounce helper (not needed if using Odoo's useDebounced, but useful standalone).
 * @param {Function} fn
 * @param {number} delay
 * @returns {Function}
 */
export function debounce(fn, delay = 300) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
