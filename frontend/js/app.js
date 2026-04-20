/**
 * CrowdPulse AI — Frontend Application Logic
 *
 * Responsibilities:
 *   - Polls /crowd/status every 5 seconds for live density updates.
 *   - Populates zone selects from the crowd status response.
 *   - Submits route requests to /navigate/suggest.
 *   - Renders route timeline, AI explanation, and scoring metrics.
 *   - Manages the chat widget interaction with /assistant/chat.
 *   - Fetches staff dashboard data from /analytics/dashboard.
 *   - Announces updates via aria-live regions for screen reader accessibility.
 *
 * @module app
 */

"use strict";

const API_BASE = "";
const POLL_INTERVAL_MS = 5000;

// ── DOM Handles ──────────────────────────────────────────────────────────────
const $  = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const routeForm      = $("#route-form");
const currentZoneSel = $("#current_zone");
const destinationSel = $("#destination");
const prioritySel    = $("#priority");
const submitBtn      = $("#submit-btn");
const btnText        = $("#btn-text");
const btnSpinner     = $("#btn-spinner");
const formError      = $("#form-error");
const emptyState     = $("#empty-state");
const resultsDisplay = $("#results-display");
const routeTimeline  = $("#route-timeline");
const aiExplanation  = $("#ai-explanation");
const waitTimeDisp   = $("#wait-time-display");
const distanceBadge  = $("#route-distance-badge");
const barDensity     = $("#bar-density");
const barTrend       = $("#bar-trend");
const barEvent       = $("#bar-event");
const statusGrid     = $("#status-grid");
const waitTimesGrid  = $("#wait-times-grid");
const insightText    = $("#insight-text");
const timeSlider     = $("#time-slider");
const timeDisplay    = $("#time-display");
const srAnnouncer    = $("#sr-announcer");
const mapContainer   = $("#map-venue-view");

// Chat
const chatToggle   = $("#chat-toggle-btn");
const chatWidget   = $("#chat-widget");
const chatClose    = $("#chat-close-btn");
const chatForm     = $("#chat-form");
const chatInput    = $("#chat-input");
const chatFeed     = $("#chat-feed");
const chatChips    = $$(".chat-chip");

// Staff
const staffToggle      = $("#staff-toggle-btn");
const staffContainer   = $("#staff-view-container");
const attendeeContainer= $("#attendee-view-container");

// ── State ────────────────────────────────────────────────────────────────────
let zonesPopulated = false;
const chatHistory  = [];
let currentRoute   = null;

// ── Accessible Announcer ─────────────────────────────────────────────────────
/**
 * Sends a message to the screen-reader live region.
 * Clears then re-sets the text so assistive tech re-announces it.
 * @param {string} msg - Text to announce.
 */
function announce(msg) {
    if (srAnnouncer) {
        srAnnouncer.textContent = "";
        requestAnimationFrame(() => { srAnnouncer.textContent = msg; });
    }
}

// ── API Helpers ──────────────────────────────────────────────────────────────
/**
 * Fetches JSON from the backend API.
 * @param {string} url - Endpoint path (e.g. "/crowd/status").
 * @param {RequestInit} [opts] - Optional fetch overrides (method, body, etc.).
 * @returns {Promise<Object>} Parsed JSON response.
 * @throws {Error} If the response is not OK.
 */
async function fetchJSON(url, opts = {}) {
    const resp = await fetch(API_BASE + url, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
}

// ── Populate Zone Selects ────────────────────────────────────────────────────
/**
 * Populates the origin and destination select elements with zone options.
 * Called once when the first crowd status response arrives.
 * @param {Array<{zone_id: string, name: string}>} zones - Zone list from the API.
 */
function populateSelects(zones) {
    if (zonesPopulated) return;
    zonesPopulated = true;

    [currentZoneSel, destinationSel].forEach((sel) => {
        sel.innerHTML = '<option value="" disabled selected>Choose zone...</option>';
        zones.forEach((z) => {
            const opt = document.createElement("option");
            opt.value = z.zone_id;
            opt.textContent = z.name;
            sel.appendChild(opt);
        });
    });
}

// ── Live Telemetry Polling ───────────────────────────────────────────────────
async function pollCrowdStatus() {
    try {
        const data = await fetchJSON("/crowd/status");
        populateSelects(data.zones);
        renderStatusGrid(data.zones);
        updateInsightBanner(data.zones);
        announce("Telemetry updated");
    } catch (err) {
        console.error("Poll failed:", err);
    }
}

function renderStatusGrid(zones) {
    statusGrid.innerHTML = zones
        .map((z) => `
            <div class="zone-status-card glass-panel status-${z.status}" role="region" aria-label="${z.name}">
                <div class="zone-name">${z.name}</div>
                <div class="zone-density status-${z.status}">${z.density}%</div>
                <div class="zone-status-label">${z.status}</div>
            </div>
        `)
        .join("");
}

function updateInsightBanner(zones) {
    const critical = zones.filter((z) => z.status === "CRITICAL" || z.status === "HIGH");
    if (critical.length > 0) {
        insightText.textContent = `⚠ ${critical.length} zone(s) at elevated density — AI recommends alternative routes.`;
    } else {
        insightText.textContent = "All zones nominal — optimal conditions for navigation.";
    }
}

// ── Wait Times ───────────────────────────────────────────────────────────────
async function pollWaitTimes() {
    try {
        const data = await fetchJSON("/crowd/wait-times");
        waitTimesGrid.innerHTML = data.services
            .map((s) => `
                <div class="zone-status-card glass-panel status-${s.status === 'HIGH' ? 'HIGH' : s.status === 'MODERATE' ? 'MEDIUM' : 'LOW'}" role="region" aria-label="${s.name}">
                    <div class="zone-name">${s.name}</div>
                    <div class="zone-density status-${s.status === 'HIGH' ? 'HIGH' : s.status === 'MODERATE' ? 'MEDIUM' : 'LOW'}">${s.wait_minutes} min</div>
                    <div class="zone-status-label">${s.trend}</div>
                </div>
            `)
            .join("");
    } catch (err) {
        console.error("Wait times poll failed:", err);
    }
}

// ── Route Submission ─────────────────────────────────────────────────────────
routeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    formError.classList.add("d-none");

    const current = currentZoneSel.value;
    const dest = destinationSel.value;
    const priority = prioritySel.value;

    if (!current || !dest) {
        formError.textContent = "Please select both origin and destination.";
        formError.classList.remove("d-none");
        return;
    }

    // UI loading state
    btnText.textContent = "Computing...";
    btnSpinner.classList.remove("d-none");
    submitBtn.disabled = true;

    const constraints = [];
    if ($("#constraint-avoid")?.checked) constraints.push("avoid_crowd");
    if ($("#constraint-fastest")?.checked) constraints.push("prefer_fastest");

    try {
        const data = await fetchJSON("/navigate/suggest", {
            method: "POST",
            body: JSON.stringify({
                user_id: "web-" + Date.now(),
                current_zone: current,
                destination: dest,
                priority: priority,
                constraints: constraints,
            }),
        });

        currentRoute = data;
        renderResults(data);
        announce(`Route computed: ${data.recommended_route.length} steps, about ${data.estimated_wait_minutes} minutes.`);
    } catch (err) {
        formError.textContent = err.message;
        formError.classList.remove("d-none");
        announce("Route computation failed.");
    } finally {
        btnText.textContent = "Compute Optimal Path";
        btnSpinner.classList.add("d-none");
        submitBtn.disabled = false;
    }
});

// ── Render Results ───────────────────────────────────────────────────────────
/**
 * Renders the full navigation result: route timeline, AI explanation,
 * scoring metrics, and SVG map visualisation.
 * @param {Object} data - NavigationResponse from the backend.
 */
function renderResults(data) {
    emptyState.classList.add("d-none");
    resultsDisplay.classList.remove("d-none");

    waitTimeDisp.textContent = `${data.estimated_wait_minutes} mins`;
    distanceBadge.textContent = `${data.total_walking_distance_meters} m`;

    // Route timeline
    routeTimeline.innerHTML = data.recommended_route
        .map((zoneId) => {
            const score = data.zone_scores[zoneId];
            const density = 100 - (score?.score || 50);
            const status = density >= 80 ? "CRITICAL" : density >= 60 ? "HIGH" : density >= 35 ? "MEDIUM" : "LOW";
            return `
                <div class="route-step">
                    <div class="route-dot status-${status}" aria-label="${status} density">${density}%</div>
                    <div class="route-info">
                        <h4>${zoneId}</h4>
                        <p>Score: ${score?.score || 0}/100 • Confidence: ${score?.confidence_score || 0}%</p>
                    </div>
                </div>
            `;
        })
        .join("");

    // AI explanation
    aiExplanation.textContent = data.ai_explanation || "No AI explanation available.";

    // Metrics bars
    const rs = data.reasoning_summary;
    animateBar(barDensity, rs.density_factor * 100);
    animateBar(barTrend, rs.trend_factor * 100);
    animateBar(barEvent, rs.event_factor * 100);

    // Map visualization
    renderRouteMap(data);
}

/**
 * Animates a progress bar element to the given percentage.
 * @param {HTMLElement} el - The progress bar fill element.
 * @param {number} pct - Target percentage (0–100).
 */
function animateBar(el, pct) {
    el.style.width = "0%";
    requestAnimationFrame(() => {
        el.style.width = `${Math.min(100, Math.round(pct))}%`;
        el.setAttribute("aria-valuenow", Math.round(pct));
    });
}

// ── SVG Map ──────────────────────────────────────────────────────────────────
function renderRouteMap(data) {
    if (!mapContainer) return;
    const waypoints = data.route_waypoints || [];
    if (waypoints.length === 0) { mapContainer.innerHTML = '<p style="padding:2rem;color:var(--text-dim);text-align:center;">No waypoint data</p>'; return; }

    const lats = waypoints.map((w) => w.lat);
    const lngs = waypoints.map((w) => w.lng);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
    const padLat = (maxLat - minLat) * 0.3 || 0.001;
    const padLng = (maxLng - minLng) * 0.3 || 0.001;

    const toX = (lng) => ((lng - (minLng - padLng)) / ((maxLng + padLng) - (minLng - padLng))) * 100;
    const toY = (lat) => (1 - (lat - (minLat - padLat)) / ((maxLat + padLat) - (minLat - padLat))) * 100;

    let pathD = "";
    const circles = [];
    waypoints.forEach((wp, i) => {
        const x = toX(wp.lng);
        const y = toY(wp.lat);
        pathD += (i === 0 ? `M${x},${y}` : ` L${x},${y}`);
        const isStart = i === 0;
        const isEnd = i === waypoints.length - 1;
        const fill = isStart ? "#4ade80" : isEnd ? "#f87171" : "#38bdf8";
        const r = (isStart || isEnd) ? 4 : 2.5;
        circles.push(`<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" opacity="0.9"><title>${wp.zone_id}</title></circle>`);
    });

    mapContainer.innerHTML = `
        <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
            <path d="${pathD}" fill="none" stroke="url(#routeGrad)" stroke-width="1.2" stroke-linecap="round" stroke-dasharray="2,1" opacity="0.7"/>
            <defs><linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#4ade80"/><stop offset="100%" stop-color="#f87171"/></linearGradient></defs>
            ${circles.join("")}
        </svg>
    `;
}

// ── Time Slider ──────────────────────────────────────────────────────────────
timeSlider.addEventListener("input", () => {
    const val = parseInt(timeSlider.value, 10);
    timeDisplay.textContent = val === 0 ? "Live Now" : `+${val} min`;
});

// ── Chat Widget ──────────────────────────────────────────────────────────────
chatToggle.addEventListener("click", () => {
    const open = chatWidget.classList.toggle("d-none");
    chatToggle.setAttribute("aria-expanded", !open);
    if (!open) chatInput.focus();
});
chatClose.addEventListener("click", () => {
    chatWidget.classList.add("d-none");
    chatToggle.setAttribute("aria-expanded", "false");
    chatToggle.focus();
});

chatChips.forEach((chip) => {
    chip.addEventListener("click", () => {
        chatInput.value = chip.textContent.trim();
        chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
    });
});

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;

    appendChatMsg(msg, "user-msg");
    chatHistory.push({ role: "user", content: msg });
    chatInput.value = "";

    try {
        const data = await fetchJSON("/assistant/chat", {
            method: "POST",
            body: JSON.stringify({
                user_id: "web-chat-" + Date.now(),
                message: msg,
                history: chatHistory.slice(-6),
            }),
        });
        appendChatMsg(data.reply, "ai-msg");
        chatHistory.push({ role: "assistant", content: data.reply });
    } catch (err) {
        appendChatMsg("Sorry, something went wrong. Please try again.", "ai-msg");
    }
});

/**
 * Appends a chat message bubble to the chat feed and scrolls to bottom.
 * @param {string} text - Message text to display.
 * @param {string} cls - CSS class: 'user-msg' or 'ai-msg'.
 */
function appendChatMsg(text, cls) {
    const div = document.createElement("div");
    div.className = `chat-msg ${cls}`;
    div.textContent = text;
    chatFeed.appendChild(div);
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

// ── Staff Dashboard Toggle ───────────────────────────────────────────────────
let staffLoaded = false;
staffToggle.addEventListener("click", () => {
    const isActive = staffContainer.classList.toggle("d-none");
    attendeeContainer.classList.toggle("d-none");
    staffToggle.setAttribute("aria-pressed", !isActive);
    staffToggle.textContent = isActive ? "Operations Control" : "Attendee View";
    if (!isActive && !staffLoaded) {
        loadStaffDashboard();
        staffLoaded = true;
    }
});

async function loadStaffDashboard() {
    try {
        const data = await fetchJSON("/analytics/dashboard");

        const hotspotsList = $("#staff-hotspots-list");
        hotspotsList.innerHTML = data.historical_hotspots
            .map((h) => `<li>${h}</li>`)
            .join("");

        const recList = $("#staff-recommendations-list");
        recList.innerHTML = data.ai_recommendations
            .map((r) => `<li>${r}</li>`)
            .join("");

        const briefing = $("#staff-briefing");
        briefing.textContent = data.operational_briefing;

        const leaderboard = $("#staff-leaderboard-list");
        leaderboard.innerHTML = data.live_leaderboard
            .map((z) => `<li><span>${z.name}</span><span style="font-weight:700;color:${z.current_density >= 60 ? 'var(--accent-red)' : 'var(--accent-green)'}">${z.current_density}%</span></li>`)
            .join("");
    } catch (err) {
        console.error("Staff dashboard failed:", err);
    }
}

// ── Init ─────────────────────────────────────────────────────────────────────
pollCrowdStatus();
pollWaitTimes();
setInterval(pollCrowdStatus, POLL_INTERVAL_MS);
setInterval(pollWaitTimes, POLL_INTERVAL_MS * 2);
