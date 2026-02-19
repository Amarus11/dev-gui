/** @odoo-module */

/**
 * Compute elapsed seconds from a UTC datetime value to now.
 * Handles both string ("2025-01-15 10:30:00") and Luxon DateTime objects.
 *
 * @param {string|Object} dateTimeValue - UTC datetime string or Luxon DateTime
 * @returns {number} elapsed seconds (0 if invalid or future)
 */
export function computeElapsedSeconds(dateTimeValue) {
    if (!dateTimeValue) {
        return 0;
    }
    let startMs;
    if (typeof dateTimeValue === "string") {
        // Odoo stores datetimes as UTC strings like "2025-01-15 10:30:00"
        const normalized = dateTimeValue.includes("T")
            ? dateTimeValue
            : dateTimeValue.replace(" ", "T") + "Z";
        startMs = new Date(normalized).getTime();
    } else if (dateTimeValue.toMillis) {
        // Luxon DateTime object
        startMs = dateTimeValue.toMillis();
    } else if (dateTimeValue.ts) {
        // Luxon DateTime internal timestamp
        startMs = dateTimeValue.ts;
    } else {
        return 0;
    }
    if (isNaN(startMs)) {
        return 0;
    }
    const diff = Math.floor((Date.now() - startMs) / 1000);
    return diff > 0 ? diff : 0;
}

/**
 * Format seconds into adaptive display string.
 * 45 → "45s"
 * 125 → "2m 05s"
 * 3725 → "1h 02m 05s"
 *
 * @param {number} totalSeconds
 * @returns {string}
 */
export function formatAdaptiveTimer(totalSeconds) {
    if (!totalSeconds || totalSeconds < 0) {
        totalSeconds = 0;
    }
    totalSeconds = Math.floor(totalSeconds);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
        return `${hours}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
    }
    if (minutes > 0) {
        return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
    }
    return `${seconds}s`;
}

/**
 * Format float hours into display string (e.g. 1.5 → "1h 30m").
 *
 * @param {number} floatHours
 * @returns {string}
 */
export function formatFloatTime(floatHours) {
    if (!floatHours || floatHours <= 0) {
        return "0h 00m";
    }
    const hours = Math.floor(floatHours);
    const minutes = Math.round((floatHours - hours) * 60);
    return `${hours}h ${String(minutes).padStart(2, "0")}m`;
}
