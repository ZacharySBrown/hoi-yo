/**
 * HOI-YO Observer Dashboard -- Client-side application
 *
 * Connects via WebSocket for live turn updates and renders
 * agent decisions into the nation card grid.
 */

(function () {
    "use strict";

    // ─── Constants ───────────────────────────────────────────────────

    const MOOD_COLORS = {
        confident: "var(--mood-confident)",
        anxious: "var(--mood-anxious)",
        aggressive: "var(--mood-aggressive)",
        defensive: "var(--mood-defensive)",
        scheming: "var(--mood-scheming)",
        panicking: "var(--mood-panicking)",
        triumphant: "var(--mood-triumphant)",
        brooding: "var(--mood-brooding)",
    };

    const COUNTRY_NAMES = {
        GER: "Germany",
        SOV: "Soviet Union",
        USA: "United States",
        ENG: "United Kingdom",
        JAP: "Japan",
        ITA: "Italy",
    };

    const RECONNECT_DELAY_MS = 2000;
    const GAME_START_YEAR = 1936;
    const GAME_END_YEAR = 1948;

    // ─── State ───────────────────────────────────────────────────────

    let ws = null;
    let reconnectTimer = null;
    let currentSpeed = 3;
    let expandedTag = null;

    // ─── DOM References ──────────────────────────────────────────────

    const turnNumberEl = document.getElementById("turn-number");
    const gameDateEl = document.getElementById("game-date");
    const worldTensionEl = document.getElementById("world-tension");
    const timelineFill = document.getElementById("timeline-fill");
    const wsDot = document.getElementById("ws-dot");
    const wsStatus = document.getElementById("ws-status");
    const overlay = document.getElementById("connecting-overlay");
    const whisperTarget = document.getElementById("whisper-target");
    const whisperInput = document.getElementById("whisper-input");
    const whisperSend = document.getElementById("whisper-send");

    // ─── WebSocket Connection ────────────────────────────────────────

    function connectWebSocket() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        const url = proto + "//" + location.host + "/ws";

        ws = new WebSocket(url);

        ws.onopen = function () {
            setConnectionStatus(true);
            overlay.classList.remove("visible");
        };

        ws.onclose = function () {
            setConnectionStatus(false);
            scheduleReconnect();
        };

        ws.onerror = function () {
            setConnectionStatus(false);
        };

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data.type === "pong") return;
                handleTurnUpdate(data);
            } catch (e) {
                console.error("Failed to parse WS message:", e);
            }
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        overlay.classList.add("visible");
        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connectWebSocket();
        }, RECONNECT_DELAY_MS);
    }

    function setConnectionStatus(connected) {
        if (connected) {
            wsDot.classList.add("connected");
            wsStatus.textContent = "Live";
        } else {
            wsDot.classList.remove("connected");
            wsStatus.textContent = "Disconnected";
        }
    }

    // ─── Turn Update Handler ─────────────────────────────────────────

    function handleTurnUpdate(data) {
        // Update header info
        if (data.date) {
            gameDateEl.textContent = data.date;
            updateTimeline(data.date);
        }
        if (data.turn !== undefined) {
            turnNumberEl.textContent = data.turn;
        }
        if (data.world_tension !== undefined) {
            worldTensionEl.textContent = Math.round(data.world_tension) + "%";
        }

        // Update nation cards from decisions
        if (data.decisions) {
            for (var tag in data.decisions) {
                if (data.decisions.hasOwnProperty(tag)) {
                    updateNationCard(tag, data.decisions[tag]);
                }
            }
        }

        // Update nation cards from country states
        if (data.countries) {
            for (var tag in data.countries) {
                if (data.countries.hasOwnProperty(tag)) {
                    updateNationCountry(tag, data.countries[tag]);
                }
            }
        }

        // Update personas if included
        if (data.personas) {
            for (var i = 0; i < data.personas.length; i++) {
                var p = data.personas[i];
                var card = document.querySelector('.nation-card[data-tag="' + p.tag + '"]');
                if (card) {
                    var el = card.querySelector('[data-field="persona"]');
                    if (el) el.textContent = p.name;
                }
            }
        }
    }

    function updateNationCard(tag, decision) {
        var card = document.querySelector('.nation-card[data-tag="' + tag + '"]');
        if (!card) return;

        // Mood badge
        var moodEl = card.querySelector('[data-field="mood"]');
        var mood = (decision.mood || "").toLowerCase();
        if (moodEl) {
            moodEl.textContent = mood || "--";
            moodEl.style.background = MOOD_COLORS[mood] || "var(--text-muted)";
            moodEl.style.color = (mood === "anxious" || mood === "triumphant") ? "#000" : "#fff";
        }

        // Monologue preview (first 100 chars)
        var previewEl = card.querySelector('[data-field="monologue-preview"]');
        if (previewEl && decision.inner_monologue) {
            var text = decision.inner_monologue;
            previewEl.textContent = text.length > 100 ? text.substring(0, 100) + "..." : text;
        }

        // Full monologue in Mind Reader
        var fullEl = card.querySelector('[data-field="full-monologue"]');
        if (fullEl && decision.inner_monologue) {
            fullEl.textContent = decision.inner_monologue;
        }

        // Strategy changes
        var stratEl = card.querySelector('[data-field="strategies"]');
        if (stratEl) {
            renderStrategies(stratEl, decision);
        }

        // Threat assessment
        var threatEl = card.querySelector('[data-field="threats"]');
        if (threatEl && decision.threats) {
            renderThreats(threatEl, decision.threats);
        }

        // Model info
        var modelEl = card.querySelector('[data-field="model"]');
        if (modelEl && decision.model) {
            modelEl.textContent = decision.model;
        }
    }

    function updateNationCountry(tag, country) {
        var card = document.querySelector('.nation-card[data-tag="' + tag + '"]');
        if (!card) return;

        // Factory stats
        setField(card, "mic", country.mil_factories);
        setField(card, "cic", country.civ_factories);
        setField(card, "nic", country.dockyards);
        setField(card, "div", country.division_count);

        // War indicator
        var warEl = card.querySelector('[data-field="war-indicator"]');
        if (warEl) {
            if (country.at_war) {
                warEl.classList.add("visible");
            } else {
                warEl.classList.remove("visible");
            }
        }
    }

    function setField(card, field, value) {
        var el = card.querySelector('[data-field="' + field + '"]');
        if (el && value !== undefined) {
            el.textContent = value;
        }
    }

    // ─── Strategy Rendering ──────────────────────────────────────────

    function renderStrategies(container, decision) {
        var items = [];

        if (decision.diplomatic) {
            for (var i = 0; i < decision.diplomatic.length; i++) {
                var d = decision.diplomatic[i];
                items.push({ type: "DIP", text: d.strategy_type + " -> " + d.target });
            }
        }
        if (decision.military) {
            for (var i = 0; i < decision.military.length; i++) {
                var m = decision.military[i];
                items.push({ type: "MIL", text: m.strategy_type + ": " + m.id });
            }
        }
        if (decision.production) {
            for (var i = 0; i < decision.production.length; i++) {
                var p = decision.production[i];
                items.push({ type: "PRD", text: p.strategy_type + (p.id ? ": " + p.id : "") });
            }
        }

        if (items.length === 0) {
            container.innerHTML = "<li>No strategy changes</li>";
            return;
        }

        var html = "";
        for (var i = 0; i < items.length; i++) {
            html += '<li><span class="strategy-type">' + escapeHtml(items[i].type) +
                    '</span>' + escapeHtml(items[i].text) + '</li>';
        }
        container.innerHTML = html;
    }

    // ─── Threat Bar Rendering ────────────────────────────────────────

    function renderThreats(container, threats) {
        var tags = Object.keys(threats);
        if (tags.length === 0) {
            container.innerHTML = '<div class="threat-row"><span class="threat-label">--</span>' +
                '<div class="threat-bar-track"><div class="threat-bar-fill" style="width:0%"></div></div>' +
                '<span class="threat-value">0</span></div>';
            return;
        }

        // Sort by threat level descending
        tags.sort(function (a, b) { return threats[b] - threats[a]; });

        var html = "";
        for (var i = 0; i < tags.length; i++) {
            var tag = tags[i];
            var val = threats[tag];
            var pct = Math.min(val, 100);
            var cls = pct >= 80 ? "critical" : pct >= 50 ? "high" : pct >= 25 ? "medium" : "low";

            html += '<div class="threat-row">' +
                    '<span class="threat-label">' + escapeHtml(tag) + '</span>' +
                    '<div class="threat-bar-track">' +
                    '<div class="threat-bar-fill ' + cls + '" style="width:' + pct + '%"></div>' +
                    '</div>' +
                    '<span class="threat-value">' + val + '</span>' +
                    '</div>';
        }
        container.innerHTML = html;
    }

    // ─── Timeline ────────────────────────────────────────────────────

    function updateTimeline(dateStr) {
        // Date format: "1936.1.1" or "1936.01.01"
        var parts = dateStr.split(".");
        if (parts.length < 1) return;
        var year = parseInt(parts[0], 10);
        var month = parts.length > 1 ? parseInt(parts[1], 10) : 1;

        var totalMonths = (GAME_END_YEAR - GAME_START_YEAR) * 12;
        var elapsed = (year - GAME_START_YEAR) * 12 + (month - 1);
        var pct = Math.max(0, Math.min(100, (elapsed / totalMonths) * 100));

        timelineFill.style.width = pct + "%";
    }

    // ─── Card Expansion (Mind Reader) ────────────────────────────────

    function initCardClicks() {
        var cards = document.querySelectorAll(".nation-card");
        for (var i = 0; i < cards.length; i++) {
            cards[i].addEventListener("click", function (e) {
                // Don't toggle if clicking inside mind-reader panel links etc.
                if (e.target.closest(".mind-reader")) return;

                var tag = this.getAttribute("data-tag");
                if (expandedTag === tag) {
                    this.classList.remove("expanded");
                    expandedTag = null;
                } else {
                    // Collapse previous
                    if (expandedTag) {
                        var prev = document.querySelector('.nation-card[data-tag="' + expandedTag + '"]');
                        if (prev) prev.classList.remove("expanded");
                    }
                    this.classList.add("expanded");
                    expandedTag = tag;
                }
            });
        }
    }

    // ─── Speed Controls ──────────────────────────────────────────────

    function initSpeedControls() {
        var btns = document.querySelectorAll(".speed-btn");
        for (var i = 0; i < btns.length; i++) {
            btns[i].addEventListener("click", function (e) {
                e.stopPropagation();
                var speed = parseInt(this.getAttribute("data-speed"), 10);

                fetch("/api/speed/" + speed, { method: "POST" })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        currentSpeed = data.speed;
                        updateSpeedButtons(data.paused ? 0 : data.speed);
                    })
                    .catch(function (err) {
                        console.error("Speed change failed:", err);
                    });
            });
        }
    }

    function updateSpeedButtons(activeSpeed) {
        var btns = document.querySelectorAll(".speed-btn");
        for (var i = 0; i < btns.length; i++) {
            var s = parseInt(btns[i].getAttribute("data-speed"), 10);
            if (s === activeSpeed) {
                btns[i].classList.add("active");
            } else {
                btns[i].classList.remove("active");
            }
        }
    }

    // ─── Whisper ─────────────────────────────────────────────────────

    function initWhisper() {
        function sendWhisper() {
            var tag = whisperTarget.value;
            var msg = whisperInput.value.trim();
            if (!msg) return;

            fetch("/api/whisper", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tag: tag, message: msg }),
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                whisperInput.value = "";
                // Brief visual feedback
                whisperSend.textContent = "Sent!";
                setTimeout(function () { whisperSend.textContent = "Send"; }, 1000);
            })
            .catch(function (err) {
                console.error("Whisper failed:", err);
            });
        }

        whisperSend.addEventListener("click", sendWhisper);
        whisperInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") sendWhisper();
        });
    }

    // ─── Initial Data Load ───────────────────────────────────────────

    function loadInitialData() {
        // Fetch current status
        fetch("/api/status")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.date) gameDateEl.textContent = data.date;
                if (data.turn !== undefined) turnNumberEl.textContent = data.turn;
                if (data.speed !== undefined) updateSpeedButtons(data.paused ? 0 : data.speed);
            })
            .catch(function () {});

        // Fetch personas
        fetch("/api/personas")
            .then(function (r) { return r.json(); })
            .then(function (personas) {
                for (var i = 0; i < personas.length; i++) {
                    var p = personas[i];
                    var card = document.querySelector('.nation-card[data-tag="' + p.tag + '"]');
                    if (card) {
                        var el = card.querySelector('[data-field="persona"]');
                        if (el && p.name) el.textContent = p.name;
                    }
                }
            })
            .catch(function () {});
    }

    // ─── Utilities ───────────────────────────────────────────────────

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // ─── Boot ────────────────────────────────────────────────────────

    function init() {
        initCardClicks();
        initSpeedControls();
        initWhisper();
        loadInitialData();
        connectWebSocket();
    }

    // Run when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
