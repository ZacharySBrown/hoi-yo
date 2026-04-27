/**
 * HOI-YO Observer Dashboard v3 -- Client Application
 *
 * Diplomatic web SVG (with minor powers), nation intelligence cards,
 * agent minds tabs, icon-rich event timeline, and real-time WebSocket.
 */
(function () {
    "use strict";

    // ─── Constants ──────────────────────────────────────────────────

    const TAGS = ["GER", "SOV", "USA", "ENG", "JAP", "ITA"];

    const NATIONS = {
        GER: { name: "Germany",        flag: "\u{1F1E9}\u{1F1EA}", accent: "#6b7280" },
        SOV: { name: "Soviet Union",   flag: "\u{1F1F7}\u{1F1FA}", accent: "#dc2626" },
        USA: { name: "United States",  flag: "\u{1F1FA}\u{1F1F8}", accent: "#2563eb" },
        ENG: { name: "United Kingdom", flag: "\u{1F1EC}\u{1F1E7}", accent: "#16a34a" },
        JAP: { name: "Japan",          flag: "\u{1F1EF}\u{1F1F5}", accent: "#dc2626" },
        ITA: { name: "Italy",          flag: "\u{1F1EE}\u{1F1F9}", accent: "#ca8a04" },
    };

    const MINOR_POWERS = {
        FRA: { name: "France",          flag: "\u{1F1EB}\u{1F1F7}", accent: "#2563eb" },
        POL: { name: "Poland",          flag: "\u{1F1F5}\u{1F1F1}", accent: "#dc2626" },
        CHI: { name: "China",           flag: "\u{1F1E8}\u{1F1F3}", accent: "#eab308" },
        PRC: { name: "Comm. China",     flag: "\u{1F1E8}\u{1F1F3}", accent: "#dc2626" },
        CAN: { name: "Canada",          flag: "\u{1F1E8}\u{1F1E6}", accent: "#ef4444" },
        RAJ: { name: "British Raj",     flag: "\u{1F1EE}\u{1F1F3}", accent: "#f97316" },
        AUS: { name: "Austria",         flag: "\u{1F1E6}\u{1F1F9}", accent: "#ef4444" },
        CZE: { name: "Czechoslovakia",  flag: "\u{1F1E8}\u{1F1FF}", accent: "#2563eb" },
        HUN: { name: "Hungary",         flag: "\u{1F1ED}\u{1F1FA}", accent: "#16a34a" },
        ROM: { name: "Romania",         flag: "\u{1F1F7}\u{1F1F4}", accent: "#2563eb" },
        YUG: { name: "Yugoslavia",      flag: "\u{1F1F7}\u{1F1F8}", accent: "#2563eb" },
        BUL: { name: "Bulgaria",        flag: "\u{1F1E7}\u{1F1EC}", accent: "#16a34a" },
        GRE: { name: "Greece",          flag: "\u{1F1EC}\u{1F1F7}", accent: "#2563eb" },
        TUR: { name: "Turkey",          flag: "\u{1F1F9}\u{1F1F7}", accent: "#dc2626" },
        SPA: { name: "Nat. Spain",      flag: "\u{1F1EA}\u{1F1F8}", accent: "#eab308" },
        SPR: { name: "Rep. Spain",      flag: "\u{1F1EA}\u{1F1F8}", accent: "#a855f7" },
        POR: { name: "Portugal",        flag: "\u{1F1F5}\u{1F1F9}", accent: "#16a34a" },
        FIN: { name: "Finland",         flag: "\u{1F1EB}\u{1F1EE}", accent: "#2563eb" },
        NOR: { name: "Norway",          flag: "\u{1F1F3}\u{1F1F4}", accent: "#dc2626" },
        SWE: { name: "Sweden",          flag: "\u{1F1F8}\u{1F1EA}", accent: "#eab308" },
        DEN: { name: "Denmark",         flag: "\u{1F1E9}\u{1F1F0}", accent: "#dc2626" },
        BEL: { name: "Belgium",         flag: "\u{1F1E7}\u{1F1EA}", accent: "#eab308" },
        HOL: { name: "Netherlands",     flag: "\u{1F1F3}\u{1F1F1}", accent: "#f97316" },
        MAN: { name: "Manchukuo",       flag: "\u{1F3F4}",          accent: "#eab308" },
        SIA: { name: "Siam",            flag: "\u{1F1F9}\u{1F1ED}", accent: "#2563eb" },
        MEX: { name: "Mexico",          flag: "\u{1F1F2}\u{1F1FD}", accent: "#16a34a" },
        BRA: { name: "Brazil",          flag: "\u{1F1E7}\u{1F1F7}", accent: "#16a34a" },
        SAF: { name: "South Africa",    flag: "\u{1F1FF}\u{1F1E6}", accent: "#16a34a" },
        ETH: { name: "Ethiopia",        flag: "\u{1F1EA}\u{1F1F9}", accent: "#16a34a" },
        IRQ: { name: "Iraq",            flag: "\u{1F1EE}\u{1F1F6}", accent: "#16a34a" },
        PER: { name: "Persia",          flag: "\u{1F1EE}\u{1F1F7}", accent: "#16a34a" },
        PHI: { name: "Philippines",     flag: "\u{1F1F5}\u{1F1ED}", accent: "#2563eb" },
        AST: { name: "Australia",       flag: "\u{1F1E6}\u{1F1FA}", accent: "#2563eb" },
        NZL: { name: "New Zealand",     flag: "\u{1F1F3}\u{1F1FF}", accent: "#2563eb" },
    };

    const ALL_NATIONS = { ...NATIONS, ...MINOR_POWERS };

    const MOODS = {
        confident:  "#22c55e", anxious:    "#eab308", aggressive: "#ef4444",
        defensive:  "#3b82f6", scheming:   "#a855f7", panicking:  "#f97316",
        triumphant: "#fbbf24", brooding:   "#6b7280",
    };

    const DARK_TEXT_MOODS = new Set(["anxious", "triumphant"]);

    const STRATEGY_COLORS = {
        befriend: "befriend", antagonize: "antagonize", conquer: "conquer",
        contain: "contain", protect: "protect", support: "support",
        alliance: "alliance", build_army: "military", role_ratio: "military",
        front: "military", garrison: "military",
        added_military_to_civilian_factory_ratio: "production",
        equipment_production_factor: "production", wanted_divisions: "production",
    };

    const LINE_COLORS = {
        befriend: "#22c55e", antagonize: "#ef4444", conquer: "#ef4444",
        contain: "#f97316", protect: "#eab308", support: "#eab308",
        alliance: "#3b82f6",
    };

    const EVENT_ICONS = {
        declare_war:     "\u2694\uFE0F",
        conquer:         "\u{1F5E1}\uFE0F",
        antagonize:      "\u26A1",
        prepare_for_war: "\u{1F3AF}",
        contain:         "\u{1F6E1}\uFE0F",
        alliance:        "\u{1F91D}",
        support:         "\u{1F91D}",
        protect:         "\u{1F6E1}\uFE0F",
        befriend:        "\u{1F54A}\uFE0F",
        war_ongoing:     "\u{1F4A5}",
        capitulation:    "\u{1F3F3}\uFE0F",
        panicking:       "\u{1F630}",
        aggressive_mood: "\u{1F4A2}",
        production:      "\u{1F3ED}",
        military:        "\u2699\uFE0F",
        scheming:        "\u{1F9E0}",
    };

    const SVG_NS = "http://www.w3.org/2000/svg";
    const RECONNECT_MS = 2000;

    // ─── State ──────────────────────────────────────────────────────

    let ws = null;
    let reconnectTimer = null;
    let expandedTag = null;
    let timelineCollapsed = false;
    let latestDecisions = {};
    let latestCountries = {};
    let personas = {};
    let nodePositions = {};
    let agentHistory = {};
    let activeAgentTab = "GER";
    let visibleMinors = new Set();
    let latestWars = [];
    let playerTag = null;  // set when user plays as a country

    // ─── DOM Refs ───────────────────────────────────────────────────

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ─── Boot ───────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", () => {
        buildNationCards();
        buildDiploNodes();
        buildAgentMinds();
        initSpeedControls();
        initWhisper();
        initTimeline();
        initAudioQueue();
        loadInitialData();
        connectWebSocket();
    });

    // ─── WebSocket ──────────────────────────────────────────────────

    function connectWebSocket() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(proto + "//" + location.host + "/ws");

        ws.onopen = () => {
            setConnected(true);
            $("#connecting-overlay").classList.remove("visible");
        };
        ws.onclose = () => { setConnected(false); scheduleReconnect(); };
        ws.onerror = () => setConnected(false);
        ws.onmessage = (e) => {
            try {
                const d = JSON.parse(e.data);
                if (d.type === "pong") return;
                handleUpdate(d);
            } catch (err) { console.error("WS parse error:", err); }
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        $("#connecting-overlay").classList.add("visible");
        reconnectTimer = setTimeout(() => { reconnectTimer = null; connectWebSocket(); }, RECONNECT_MS);
    }

    function setConnected(ok) {
        const dot = $("#ws-dot"), label = $("#ws-status");
        dot.classList.toggle("connected", ok);
        label.textContent = ok ? "Live" : "Disconnected";
    }

    // ─── Update Handler ─────────────────────────────────────────────

    function handleUpdate(data) {
        if (data.player_tag && !playerTag) {
            playerTag = data.player_tag;
            applyPlayerMode();
        }
        if (data.date) {
            $("#game-date").textContent = data.date;
        }
        if (data.turn !== undefined) $("#turn-number").textContent = data.turn;
        if (data.world_tension !== undefined) {
            const wt = Math.round(data.world_tension);
            $("#world-tension").textContent = wt + "%";
            $("#tension-fill").style.width = Math.min(wt, 100) + "%";
        }
        if (data.personas) {
            data.personas.forEach((p) => {
                personas[p.tag] = p.name;
                const el = document.querySelector(`.nation-card[data-tag="${p.tag}"] .card-persona`);
                if (el) el.textContent = p.name;
            });
        }
        if (data.decisions) {
            for (const tag of TAGS) {
                if (data.decisions[tag]) {
                    latestDecisions[tag] = data.decisions[tag];
                    updateCard(tag, data.decisions[tag]);
                    updateAgentMind(tag, data.decisions[tag], data.turn, data.date);
                }
            }
            discoverMinorPowers(data.decisions);
            updateDiploWeb();
            addTimelineEntry(data.turn, data.date, data.decisions);
            // Queue up TTS audio for sequential playback
            audioQueue.enqueueTurn(data.decisions);
        }
        if (data.countries) {
            for (const [tag, c] of Object.entries(data.countries)) {
                latestCountries[tag] = c;
                if (TAGS.includes(tag)) {
                    updateCardCountry(tag, c);
                }
            }
            updateDiploNodeSizes();
        }
        if (data.wars) {
            latestWars = data.wars;
            updateWarIndicators(data.wars);
            data.wars.forEach((w) => {
                [...w.attackers, ...w.defenders].forEach((tag) => {
                    if (!TAGS.includes(tag)) visibleMinors.add(tag);
                });
            });
        }
        if (data.cost) updateCostDisplay(data.cost);
    }

    function discoverMinorPowers(decisions) {
        for (const tag of TAGS) {
            const dec = decisions[tag];
            if (!dec || !dec.diplomatic) continue;
            for (const d of dec.diplomatic) {
                if (!TAGS.includes(d.target)) {
                    visibleMinors.add(d.target);
                }
            }
        }
    }

    function updateCostDisplay(cost) {
        const el = $("#api-cost");
        if (!el) return;
        const total = cost.total_cost || 0;
        el.textContent = "$" + total.toFixed(2);
        if (total >= 5) el.style.color = "#ef4444";
        else if (total >= 1) el.style.color = "#eab308";
        else el.style.color = "#22c55e";
    }

    // ─── Nation Card Builder ────────────────────────────────────────

    function buildNationCards() {
        const grid = $("#nation-grid");
        TAGS.forEach((tag) => {
            const n = NATIONS[tag];
            const card = document.createElement("div");
            card.className = "nation-card";
            card.dataset.tag = tag;
            card.style.setProperty("--card-accent", `var(--nation-${tag})`);

            card.innerHTML = `
                <div class="card-top">
                    <div class="card-identity">
                        <span class="card-flag">${n.flag}</span>
                        <div class="card-names">
                            <h3>${n.name}</h3>
                            <div class="card-persona" data-field="persona">--</div>
                        </div>
                    </div>
                    <span class="card-war" data-field="war">AT WAR</span>
                    <span class="card-mood" data-field="mood">--</span>
                </div>
                <div class="card-monologue" data-field="monologue-preview">Awaiting intelligence...</div>
                <div class="card-stats">
                    <div class="card-stat"><div class="stat-label">MIC</div><div class="stat-value" data-field="mic">--</div></div>
                    <div class="card-stat"><div class="stat-label">CIC</div><div class="stat-value" data-field="cic">--</div></div>
                    <div class="card-stat"><div class="stat-label">NIC</div><div class="stat-value" data-field="nic">--</div></div>
                    <div class="card-stat"><div class="stat-label">DIV</div><div class="stat-value" data-field="div">--</div></div>
                </div>
                <div class="mind-reader">
                    <div class="mind-grid">
                        <div class="mind-block" style="grid-column: 1 / -1">
                            <h4>Inner Monologue</h4>
                            <div class="mind-monologue" data-field="full-monologue">--</div>
                        </div>
                        <div class="mind-block">
                            <h4>Strategy Changes</h4>
                            <div class="strategy-pills" data-field="strategies"></div>
                        </div>
                        <div class="mind-block">
                            <h4>Threat Assessment</h4>
                            <div class="threat-bars" data-field="threats"></div>
                        </div>
                        <div class="mind-block">
                            <h4>Model</h4>
                            <div class="model-badge" data-field="model">--</div>
                        </div>
                    </div>
                </div>`;

            card.addEventListener("click", (e) => {
                if (e.target.closest(".mind-reader")) return;
                toggleExpand(tag);
            });

            grid.appendChild(card);
        });
    }

    function toggleExpand(tag) {
        const card = document.querySelector(`.nation-card[data-tag="${tag}"]`);
        if (expandedTag === tag) {
            card.classList.remove("expanded");
            expandedTag = null;
        } else {
            if (expandedTag) {
                const prev = document.querySelector(`.nation-card[data-tag="${expandedTag}"]`);
                if (prev) prev.classList.remove("expanded");
            }
            card.classList.add("expanded");
            expandedTag = tag;
        }
    }

    function updateCard(tag, dec) {
        const card = document.querySelector(`.nation-card[data-tag="${tag}"]`);
        if (!card) return;

        // Skip AI updates for the player's country
        if (tag === playerTag) return;

        const mood = (dec.mood || "").toLowerCase();
        const moodEl = card.querySelector('[data-field="mood"]');
        moodEl.textContent = mood || "--";
        moodEl.style.background = MOODS[mood] || "#4a4e65";
        moodEl.style.color = DARK_TEXT_MOODS.has(mood) ? "#000" : "#fff";

        const prev = card.querySelector('[data-field="monologue-preview"]');
        if (dec.inner_monologue) {
            const t = dec.inner_monologue.replace(/\n/g, " ");
            prev.textContent = t.length > 140 ? t.substring(0, 140) + "..." : t;
        }

        const full = card.querySelector('[data-field="full-monologue"]');
        if (dec.inner_monologue) full.textContent = dec.inner_monologue;

        const pillBox = card.querySelector('[data-field="strategies"]');
        pillBox.innerHTML = "";
        const items = [];
        (dec.diplomatic || []).forEach((d) => items.push({ label: `${d.strategy_type} ${d.target}`, cls: STRATEGY_COLORS[d.strategy_type] || "befriend" }));
        (dec.military || []).forEach((m) => items.push({ label: `${m.strategy_type}`, cls: "military" }));
        (dec.production || []).forEach((p) => items.push({ label: `${p.strategy_type.replace(/_/g, " ").substring(0, 25)}`, cls: "production" }));
        if (items.length === 0) pillBox.innerHTML = '<span style="color:var(--text-muted);font-size:11px;">No changes</span>';
        else items.forEach((it) => {
            const pill = document.createElement("span");
            pill.className = `strategy-pill pill-${it.cls}`;
            pill.textContent = it.label;
            pillBox.appendChild(pill);
        });

        const threatBox = card.querySelector('[data-field="threats"]');
        renderThreats(threatBox, dec.threats || {});

        const modelEl = card.querySelector('[data-field="model"]');
        if (dec.model) modelEl.textContent = dec.model;
    }

    function updateCardCountry(tag, c) {
        const card = document.querySelector(`.nation-card[data-tag="${tag}"]`);
        if (!card) return;
        const set = (f, v) => { const el = card.querySelector(`[data-field="${f}"]`); if (el && v !== undefined) el.textContent = v; };
        set("mic", c.mil_factories);
        set("cic", c.civ_factories);
        set("nic", c.dockyards);
        set("div", c.division_count);

        const war = card.querySelector('[data-field="war"]');
        war.classList.toggle("visible", !!c.at_war);
    }

    function updateWarIndicators(wars) {
        TAGS.forEach((tag) => {
            const atWar = wars.some((w) => w.attackers.includes(tag) || w.defenders.includes(tag));
            const card = document.querySelector(`.nation-card[data-tag="${tag}"]`);
            if (card) card.querySelector('[data-field="war"]').classList.toggle("visible", atWar);
        });
    }

    function renderThreats(container, threats) {
        const tags = Object.keys(threats).sort((a, b) => threats[b] - threats[a]);
        if (!tags.length) { container.innerHTML = '<span style="color:var(--text-muted);font-size:11px;">No threats</span>'; return; }
        container.innerHTML = tags.map((t) => {
            const v = threats[t], pct = Math.min(v, 100);
            const cls = pct >= 80 ? "critical" : pct >= 50 ? "high" : pct >= 25 ? "medium" : "low";
            return `<div class="threat-row"><span class="threat-tag">${esc(t)}</span><div class="threat-track"><div class="threat-fill ${cls}" style="width:${pct}%"></div></div><span class="threat-val">${v}</span></div>`;
        }).join("");
    }

    // ─── Agent Minds (Tabbed) ───────────────────────────────────────

    function buildAgentMinds() {
        const tabBar = $("#minds-tabs");
        TAGS.forEach((tag, i) => {
            const n = NATIONS[tag];
            const btn = document.createElement("button");
            btn.className = "minds-tab" + (i === 0 ? " active" : "");
            btn.dataset.tag = tag;
            btn.innerHTML = `<span class="tab-flag">${n.flag}</span><span class="tab-name">${n.name}</span>`;
            btn.addEventListener("click", () => switchAgentTab(tag));
            tabBar.appendChild(btn);
        });
        activeAgentTab = TAGS[0];
    }

    function switchAgentTab(tag) {
        activeAgentTab = tag;
        $$(".minds-tab").forEach((t) => t.classList.toggle("active", t.dataset.tag === tag));
        renderAgentHistory(tag);
    }

    function renderAgentHistory(tag) {
        const content = $("#minds-content");
        const history = agentHistory[tag] || [];
        const n = ALL_NATIONS[tag] || { name: tag };

        if (history.length === 0) {
            content.innerHTML = `<div class="minds-empty">No thinking data yet for ${esc(n.name)}...</div>`;
            return;
        }

        content.innerHTML = history.slice().reverse().map((entry) => {
            const moodColor = MOODS[entry.mood] || "#4a4e65";
            const darkText = DARK_TEXT_MOODS.has(entry.mood);

            let stratHtml = "";
            if (entry.diplomatic && entry.diplomatic.length) {
                stratHtml += entry.diplomatic.map((d) => {
                    const icon = EVENT_ICONS[d.strategy_type] || "";
                    return `<span class="strategy-pill pill-${STRATEGY_COLORS[d.strategy_type] || "befriend"}">${icon} ${d.strategy_type} ${d.target}</span>`;
                }).join("");
            }
            if (entry.military && entry.military.length) {
                stratHtml += entry.military.map((m) =>
                    `<span class="strategy-pill pill-military">${EVENT_ICONS.military} ${m.strategy_type}</span>`
                ).join("");
            }
            if (entry.production && entry.production.length) {
                stratHtml += entry.production.map((p) =>
                    `<span class="strategy-pill pill-production">${EVENT_ICONS.production} ${p.strategy_type.replace(/_/g, " ").substring(0, 25)}</span>`
                ).join("");
            }

            return `
                <div class="mind-entry">
                    <div class="mind-entry-header">
                        <span class="mind-turn">T${entry.turn}</span>
                        <span class="mind-date">${esc(entry.date || "")}</span>
                        <span class="mind-mood" style="background:${moodColor};color:${darkText ? "#000" : "#fff"}">${entry.mood}</span>
                        <span class="mind-model">${esc(entry.model || "")}</span>
                    </div>
                    <div class="mind-entry-text">${esc(entry.monologue)}</div>
                    ${stratHtml ? '<div class="mind-entry-strats">' + stratHtml + "</div>" : ""}
                </div>`;
        }).join("");
    }

    function updateAgentMind(tag, decision, turn, date) {
        if (!agentHistory[tag]) agentHistory[tag] = [];
        agentHistory[tag].push({
            turn: turn,
            date: date,
            mood: (decision.mood || "").toLowerCase(),
            monologue: decision.inner_monologue || "",
            model: decision.model || "",
            diplomatic: decision.diplomatic || [],
            military: decision.military || [],
            production: decision.production || [],
            threats: decision.threats || {},
        });

        if (activeAgentTab === tag) {
            renderAgentHistory(tag);
        }

        const tab = document.querySelector(`.minds-tab[data-tag="${tag}"]`);
        if (tab) {
            const moodColor = MOODS[(decision.mood || "").toLowerCase()] || "#4a4e65";
            tab.style.borderBottomColor = moodColor;
        }
    }

    // ─── Player Mode ────────────────────────────────────────────────

    function applyPlayerMode() {
        if (!playerTag) return;

        // Update the player's nation card
        const card = document.querySelector(`.nation-card[data-tag="${playerTag}"]`);
        if (card) {
            const moodEl = card.querySelector('[data-field="mood"]');
            moodEl.textContent = "YOU";
            moodEl.style.background = "#d4a017";
            moodEl.style.color = "#000";
            moodEl.classList.add("card-player-badge");

            const mono = card.querySelector('[data-field="monologue-preview"]');
            mono.textContent = "You are in command.";
            mono.style.fontStyle = "normal";
            mono.style.color = "var(--text-muted)";
        }

        // Remove player from whisper targets
        const whisperTarget = $("#whisper-target");
        if (whisperTarget) {
            const opt = whisperTarget.querySelector(`option[value="${playerTag}"]`);
            if (opt) opt.remove();
        }

        // Remove player tab from Agent Minds
        const tab = document.querySelector(`.minds-tab[data-tag="${playerTag}"]`);
        if (tab) tab.style.display = "none";

        // Switch to first non-player tab
        const firstAI = TAGS.find(t => t !== playerTag);
        if (firstAI) switchAgentTab(firstAI);
    }

    // ─── Diplomatic Web (SVG) ───────────────────────────────────────

    function buildDiploNodes() {
        const svg = $("#diplo-svg");
        const vb = svg.viewBox.baseVal;
        const cx = vb.width / 2, cy = vb.height / 2;
        const rx = 280, ry = 140;
        const nodesG = $("#diplo-nodes");

        TAGS.forEach((tag, i) => {
            const angle = (Math.PI * 2 * i) / TAGS.length - Math.PI / 2;
            const x = cx + rx * Math.cos(angle);
            const y = cy + ry * Math.sin(angle);
            nodePositions[tag] = { x, y };

            const g = svgEl("g", { class: "diplo-node", "data-tag": tag });

            const warGlow = svgEl("circle", {
                cx: x, cy: y, r: 42, fill: "#ef444400", class: "war-glow",
                filter: "url(#war-pulse)",
            });
            g.appendChild(warGlow);

            const ring = svgEl("circle", {
                cx: x, cy: y, r: 34, fill: "none",
                stroke: NATIONS[tag].accent, "stroke-width": 3,
                class: "mood-ring", opacity: 0.6,
            });
            g.appendChild(ring);

            const bg = svgEl("circle", {
                cx: x, cy: y, r: 30, fill: "#12121f",
                stroke: "#1e1e35", "stroke-width": 1,
                class: "node-bg",
            });
            g.appendChild(bg);

            const flag = svgEl("text", {
                x: x, y: y - 4, "text-anchor": "middle", "dominant-baseline": "central",
                "font-size": "22", class: "node-flag",
            });
            flag.textContent = NATIONS[tag].flag;
            g.appendChild(flag);

            const nameEl = svgEl("text", {
                x: x, y: y + 22, "text-anchor": "middle",
                fill: "#e8e8f0", "font-size": "10", "font-weight": "700",
                "letter-spacing": "0.5",
            });
            nameEl.textContent = NATIONS[tag].name;
            g.appendChild(nameEl);

            const personaEl = svgEl("text", {
                x: x, y: y + 33, "text-anchor": "middle",
                fill: "#4a4e65", "font-size": "8", "font-style": "italic",
                class: "node-persona",
            });
            personaEl.textContent = personas[tag] || "";
            g.appendChild(personaEl);

            nodesG.appendChild(g);
        });
    }

    function computeMinorPositions() {
        const svg = $("#diplo-svg");
        const vb = svg.viewBox.baseVal;
        const cx = vb.width / 2, cy = vb.height / 2;
        const positions = {};

        // Group minors by their most-connected major power
        const groups = {};
        for (const minor of visibleMinors) {
            if (TAGS.includes(minor)) continue;
            let bestMajor = null, bestScore = 0;

            for (const tag of TAGS) {
                const dec = latestDecisions[tag];
                if (!dec || !dec.diplomatic) continue;
                for (const d of dec.diplomatic) {
                    if (d.target === minor) {
                        const score = Math.abs(d.value || 50);
                        if (score > bestScore) { bestMajor = tag; bestScore = score; }
                    }
                }
            }

            if (!bestMajor) {
                for (const w of latestWars) {
                    if (w.attackers.includes(minor) || w.defenders.includes(minor)) {
                        for (const tag of TAGS) {
                            if (w.attackers.includes(tag) || w.defenders.includes(tag)) {
                                bestMajor = tag; break;
                            }
                        }
                        if (bestMajor) break;
                    }
                }
            }

            if (!bestMajor) bestMajor = TAGS[0];
            if (!groups[bestMajor]) groups[bestMajor] = [];
            groups[bestMajor].push(minor);
        }

        for (const [major, minors] of Object.entries(groups)) {
            const parent = nodePositions[major];
            if (!parent) continue;

            const dx = parent.x - cx, dy = parent.y - cy;
            const baseAngle = Math.atan2(dy, dx);
            const fanSpread = Math.min(Math.PI * 0.6, minors.length * 0.35);
            const startAngle = baseAngle - fanSpread / 2;
            const step = minors.length > 1 ? fanSpread / (minors.length - 1) : 0;
            const dist = 85;

            minors.sort();
            minors.forEach((minor, i) => {
                const a = minors.length === 1 ? baseAngle : startAngle + step * i;
                positions[minor] = {
                    x: Math.max(35, Math.min(vb.width - 35, parent.x + dist * Math.cos(a))),
                    y: Math.max(20, Math.min(vb.height - 20, parent.y + dist * Math.sin(a))),
                };
            });
        }

        return positions;
    }

    function updateDiploWeb() {
        const linesG = $("#diplo-lines");
        const minorNodesG = $("#diplo-minor-nodes");
        linesG.innerHTML = "";
        minorNodesG.innerHTML = "";

        // Compute and render minor power nodes
        const minorPositions = computeMinorPositions();
        for (const [tag, pos] of Object.entries(minorPositions)) {
            nodePositions[tag] = pos;
            const info = ALL_NATIONS[tag] || { name: tag, flag: "\u{1F3F3}\uFE0F", accent: "#4a4e65" };
            const g = svgEl("g", { class: "diplo-node minor-node", "data-tag": tag });

            g.appendChild(svgEl("circle", {
                cx: pos.x, cy: pos.y, r: 20, fill: "none",
                stroke: info.accent, "stroke-width": 1.5, opacity: 0.4,
            }));
            g.appendChild(svgEl("circle", {
                cx: pos.x, cy: pos.y, r: 17, fill: "#12121f",
                stroke: "#1e1e35", "stroke-width": 1,
            }));

            const flag = svgEl("text", {
                x: pos.x, y: pos.y - 1, "text-anchor": "middle", "dominant-baseline": "central",
                "font-size": "14",
            });
            flag.textContent = info.flag;
            g.appendChild(flag);

            const nameEl = svgEl("text", {
                x: pos.x, y: pos.y + 14, "text-anchor": "middle",
                fill: "#8b8fa8", "font-size": "7", "font-weight": "600",
                "letter-spacing": "0.3",
            });
            nameEl.textContent = info.name;
            g.appendChild(nameEl);

            minorNodesG.appendChild(g);
        }

        // Gather all diplomatic relations
        const relations = [];
        for (const tag of TAGS) {
            const dec = latestDecisions[tag];
            if (!dec || !dec.diplomatic) continue;
            dec.diplomatic.forEach((d) => {
                if (nodePositions[d.target]) {
                    relations.push({ from: tag, to: d.target, type: d.strategy_type, value: d.value || 50 });
                }
            });
        }

        // Draw lines
        relations.forEach((rel) => {
            const p1 = nodePositions[rel.from];
            const p2 = nodePositions[rel.to];
            if (!p1 || !p2) return;

            const color = LINE_COLORS[rel.type] || "#4a4e65";
            const thickness = Math.max(1, Math.min(4, Math.abs(rel.value) / 50));
            const isFriendly = rel.type === "befriend" || rel.type === "support" || rel.type === "protect";
            const isHostile = rel.type === "antagonize" || rel.type === "conquer";
            const isMinorLine = !TAGS.includes(rel.to);

            const dx = p2.x - p1.x, dy = p2.y - p1.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const nx = -dy / len * 3, ny = dx / len * 3;

            const line = svgEl("line", {
                x1: p1.x + nx, y1: p1.y + ny,
                x2: p2.x + nx, y2: p2.y + ny,
                stroke: color,
                "stroke-width": isMinorLine ? Math.max(1, thickness * 0.7) : thickness,
                "stroke-linecap": "round",
                opacity: isMinorLine ? 0.35 : (isHostile ? 0.8 : 0.5),
            });

            if (isFriendly) {
                line.setAttribute("stroke-dasharray", "6 4");
                line.style.animation = "dash-flow 1s linear infinite";
            }
            if (isHostile) {
                line.style.animation = "pulse-line 2s ease-in-out infinite";
            }

            linesG.appendChild(line);
        });

        // Update mood rings
        TAGS.forEach((tag) => {
            const ring = document.querySelector(`.diplo-node[data-tag="${tag}"] .mood-ring`);
            if (!ring) return;
            if (tag === playerTag) {
                ring.setAttribute("stroke", "#d4a017");
                ring.setAttribute("opacity", "1");
                ring.setAttribute("stroke-width", "4");
            } else {
                const dec = latestDecisions[tag];
                const mood = dec ? (dec.mood || "").toLowerCase() : "";
                const color = MOODS[mood] || NATIONS[tag].accent;
                ring.setAttribute("stroke", color);
                ring.setAttribute("opacity", "0.8");
            }
        });

        // Update war glows
        TAGS.forEach((tag) => {
            const c = latestCountries[tag];
            const glow = document.querySelector(`.diplo-node[data-tag="${tag}"] .war-glow`);
            if (glow) {
                const atWar = c && c.at_war;
                glow.setAttribute("fill", atWar ? "#ef444433" : "#ef444400");
                glow.style.animation = atWar ? "war-cloud-pulse 2s ease-in-out infinite" : "none";
            }
        });

        // Update persona labels
        TAGS.forEach((tag) => {
            const el = document.querySelector(`.diplo-node[data-tag="${tag}"] .node-persona`);
            if (el && personas[tag]) el.textContent = personas[tag];
        });
    }

    function updateDiploNodeSizes() {
        TAGS.forEach((tag) => {
            const c = latestCountries[tag];
            if (!c) return;
            const total = (c.mil_factories || 0) + (c.civ_factories || 0) + (c.dockyards || 0);
            const r = Math.max(26, Math.min(44, 26 + (total / 20)));
            const bg = document.querySelector(`.diplo-node[data-tag="${tag}"] .node-bg`);
            const ring = document.querySelector(`.diplo-node[data-tag="${tag}"] .mood-ring`);
            if (bg) bg.setAttribute("r", r);
            if (ring) ring.setAttribute("r", r + 4);
        });
    }

    // ─── Event Timeline ─────────────────────────────────────────────

    function addTimelineEntry(turn, date, decisions) {
        const container = $("#timeline-events");
        const empty = container.querySelector(".timeline-empty");
        if (empty) empty.remove();

        const events = collectTimelineEvents(decisions);

        // Board state snapshot icons
        const boardSnap = TAGS.map((tag) => {
            const c = latestCountries[tag];
            const d = decisions[tag];
            const n = NATIONS[tag];
            if (!n) return "";
            const mood = d ? (d.mood || "").toLowerCase() : "";
            const atWar = c && c.at_war;

            let statusIcon = "";
            if (atWar) statusIcon = EVENT_ICONS.war_ongoing;
            else if (mood === "panicking") statusIcon = EVENT_ICONS.panicking;
            else if (mood === "aggressive") statusIcon = EVENT_ICONS.aggressive_mood;
            else if (mood === "scheming") statusIcon = EVENT_ICONS.scheming;

            const factories = c ? (c.mil_factories + c.civ_factories + (c.dockyards || 0)) : "?";
            const divs = c ? c.division_count : "?";

            return `<span class="tl-snap-nation" title="${n.name}: ${factories} factories, ${divs} div, ${mood}">${n.flag}${statusIcon ? '<span class="tl-snap-status">' + statusIcon + "</span>" : ""}</span>`;
        }).join("");

        // Mood dots
        let moodDots = "";
        TAGS.forEach((tag) => {
            const dec = decisions[tag];
            const mood = dec ? (dec.mood || "").toLowerCase() : "";
            const color = MOODS[mood] || "#4a4e65";
            moodDots += `<span class="tl-mood-dot" style="background:${color}" title="${NATIONS[tag].name}: ${mood || "unknown"}">${NATIONS[tag].flag}</span>`;
        });

        // Events list with icons (top 4)
        const eventsHtml = events.slice(0, 4).map((ev) =>
            `<div class="tl-event-line"><span class="tl-event-icon">${ev.icon}</span><span class="tl-event-text">${esc(ev.text)}</span></div>`
        ).join("");

        const entry = document.createElement("div");
        entry.className = "tl-entry";
        entry.innerHTML = `
            <div class="tl-marker">
                <span class="tl-turn">T${turn || "?"}</span>
                <span class="tl-date">${esc(date || "")}</span>
            </div>
            <div class="tl-body">
                <div class="tl-events-list">${eventsHtml}</div>
                <div class="tl-board-snap">${boardSnap}</div>
                <div class="tl-moods">${moodDots}</div>
            </div>`;

        container.insertBefore(entry, container.firstChild);
        while (container.children.length > 50) container.removeChild(container.lastChild);
    }

    function collectTimelineEvents(decisions) {
        const events = [];

        const verbs = {
            befriend: "extends friendship to",
            antagonize: "takes aggressive stance toward",
            conquer: "plans conquest of",
            contain: "moves to contain",
            protect: "pledges protection of",
            support: "declares support for",
            alliance: "seeks alliance with",
            prepare_for_war: "prepares for war with",
            declare_war: "DECLARES WAR on",
        };

        const priority = {
            declare_war: 100, conquer: 80, antagonize: 60, prepare_for_war: 55,
            contain: 40, alliance: 35, support: 30, protect: 25, befriend: 10,
        };

        for (const tag of TAGS) {
            const dec = decisions[tag];
            if (!dec) continue;
            const src = NATIONS[tag]?.name || tag;

            if (dec.diplomatic) {
                for (const d of dec.diplomatic) {
                    const tgt = ALL_NATIONS[d.target]?.name || d.target;
                    const verb = verbs[d.strategy_type] || "targets";
                    const icon = EVENT_ICONS[d.strategy_type] || "";
                    const score = (priority[d.strategy_type] || 10) + Math.min(Math.abs(d.value) / 10, 20);
                    events.push({ text: `${src} ${verb} ${tgt}`, icon, score });
                }
            }

            if (dec.mood === "panicking") {
                events.push({ text: `${src} is PANICKING!`, icon: EVENT_ICONS.panicking, score: 90 });
            } else if (dec.mood === "aggressive" && dec.military?.length > 3) {
                events.push({ text: `${src} mobilizes aggressively`, icon: EVENT_ICONS.aggressive_mood, score: 70 });
            } else if (dec.mood === "scheming") {
                events.push({ text: `${src} is scheming...`, icon: EVENT_ICONS.scheming, score: 45 });
            }

            if (dec.production && dec.production.length > 2) {
                events.push({ text: `${src} shifts production priorities`, icon: EVENT_ICONS.production, score: 20 });
            }
            if (dec.military && dec.military.length > 2) {
                events.push({ text: `${src} restructures military`, icon: EVENT_ICONS.military, score: 25 });
            }
        }

        if (events.length === 0) {
            events.push({ text: "Nations deliberate in silence...", icon: "\u{1F54A}\uFE0F", score: 0 });
        }

        events.sort((a, b) => b.score - a.score);
        return events;
    }

    function initTimeline() {
        const toggle = $("#timeline-toggle");
        const events = $("#timeline-events");
        if (!toggle || !events) return;
        toggle.addEventListener("click", () => {
            timelineCollapsed = !timelineCollapsed;
            events.classList.toggle("collapsed", timelineCollapsed);
            toggle.textContent = timelineCollapsed ? "Expand" : "Collapse";
        });
    }

    // ─── Speed Controls ─────────────────────────────────────────────

    function initSpeedControls() {
        $$(".speed-btn").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const speed = parseInt(btn.dataset.speed, 10);
                fetch("/api/speed/" + speed, { method: "POST" })
                    .then((r) => r.json())
                    .then((data) => {
                        const active = data.paused ? 0 : data.speed;
                        $$(".speed-btn").forEach((b) => b.classList.toggle("active", parseInt(b.dataset.speed, 10) === active));
                    })
                    .catch((err) => console.error("Speed change failed:", err));
            });
        });
    }

    // ─── Whisper ────────────────────────────────────────────────────

    function initWhisper() {
        const target = $("#whisper-target");
        const input = $("#whisper-input");
        const btn = $("#whisper-send");

        function send() {
            const msg = input.value.trim();
            if (!msg) return;
            fetch("/api/whisper", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tag: target.value, message: msg }),
            })
            .then((r) => r.json())
            .then(() => {
                input.value = "";
                showToast(`Whisper sent to ${ALL_NATIONS[target.value]?.name || target.value}`);
            })
            .catch((err) => console.error("Whisper failed:", err));
        }

        btn.addEventListener("click", send);
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
    }

    function showToast(msg) {
        const toast = $("#toast");
        toast.textContent = msg;
        toast.classList.add("show");
        setTimeout(() => toast.classList.remove("show"), 2000);
    }

    // ─── Initial Load ───────────────────────────────────────────────

    function loadInitialData() {
        fetch("/api/status")
            .then((r) => r.json())
            .then((data) => {
                if (data.date) $("#game-date").textContent = data.date;
                if (data.turn !== undefined) $("#turn-number").textContent = data.turn;
                if (data.speed !== undefined) {
                    const active = data.paused ? 0 : data.speed;
                    $$(".speed-btn").forEach((b) => b.classList.toggle("active", parseInt(b.dataset.speed, 10) === active));
                }
            })
            .catch(() => {});

        fetch("/api/personas")
            .then((r) => r.json())
            .then((list) => {
                list.forEach((p) => {
                    personas[p.tag] = p.name;
                    const cardEl = document.querySelector(`.nation-card[data-tag="${p.tag}"] .card-persona`);
                    if (cardEl && p.name) cardEl.textContent = p.name;
                    const svgPersonaEl = document.querySelector(`.diplo-node[data-tag="${p.tag}"] .node-persona`);
                    if (svgPersonaEl && p.name) svgPersonaEl.textContent = p.name;
                });
            })
            .catch(() => {});
    }

    // ─── Audio Queue (TTS playback) ────────────────────────────────

    const audioQueue = {
        queue: [],
        playing: false,
        currentAudio: null,
        muted: localStorage.getItem("hoi-yo-muted") === "1",
        unlocked: false,  // browser autoplay gate
        currentTag: null,

        enqueueTurn(decisions) {
            if (!decisions) return;
            for (const tag of TAGS) {
                const d = decisions[tag];
                if (d && d.audio_url) this.queue.push({ tag, url: d.audio_url });
            }
            if (!this.playing) this._playNext();
        },

        async _playNext() {
            if (this.muted || this.queue.length === 0) {
                this.playing = false;
                this._clearSpeaking();
                return;
            }
            this.playing = true;
            const { tag, url } = this.queue.shift();
            this._setSpeaking(tag);

            const audio = new Audio(url);
            this.currentAudio = audio;
            await new Promise((resolve) => {
                audio.onended = resolve;
                audio.onerror = (e) => {
                    console.warn("Audio failed:", url, e);
                    resolve();
                };
                const playPromise = audio.play();
                if (playPromise) {
                    playPromise.catch((err) => {
                        // Autoplay blocked -- show prompt
                        if (!this.unlocked) showAudioPrompt();
                        resolve();
                    });
                }
            });
            this.currentAudio = null;
            this._clearSpeaking();
            this._playNext();
        },

        _setSpeaking(tag) {
            this.currentTag = tag;
            const node = document.querySelector(`.diplo-node[data-tag="${tag}"]`);
            if (node) node.classList.add("speaking");
            const card = document.querySelector(`.nation-card[data-tag="${tag}"]`);
            if (card) card.classList.add("speaking");
        },

        _clearSpeaking() {
            if (!this.currentTag) return;
            const node = document.querySelector(`.diplo-node[data-tag="${this.currentTag}"]`);
            if (node) node.classList.remove("speaking");
            const card = document.querySelector(`.nation-card[data-tag="${this.currentTag}"]`);
            if (card) card.classList.remove("speaking");
            this.currentTag = null;
        },

        toggleMute() {
            this.muted = !this.muted;
            localStorage.setItem("hoi-yo-muted", this.muted ? "1" : "0");
            updateMuteButton();
            if (this.muted) {
                this.queue = [];
                if (this.currentAudio) this.currentAudio.pause();
                this._clearSpeaking();
                this.playing = false;
            }
        },

        unlock() {
            this.unlocked = true;
            hideAudioPrompt();
        },
    };

    function initAudioQueue() {
        const btn = document.getElementById("mute-btn");
        if (btn) {
            btn.addEventListener("click", () => audioQueue.toggleMute());
        }
        updateMuteButton();
        // First user click anywhere unlocks audio playback
        document.addEventListener("click", () => audioQueue.unlock(), { once: true });
    }

    function updateMuteButton() {
        const btn = document.getElementById("mute-btn");
        const icon = document.getElementById("mute-icon");
        const label = document.getElementById("mute-label");
        if (!btn) return;
        if (audioQueue.muted) {
            btn.classList.add("muted");
            if (icon) icon.textContent = "🔇";  // muted speaker
            if (label) label.textContent = "VOICES OFF";
        } else {
            btn.classList.remove("muted");
            if (icon) icon.textContent = "🔊";  // speaker
            if (label) label.textContent = "VOICES ON";
        }
    }

    function showAudioPrompt() {
        let el = document.getElementById("audio-prompt");
        if (!el) {
            el = document.createElement("div");
            el.id = "audio-prompt";
            el.className = "audio-prompt";
            el.textContent = "🔊 Click anywhere to enable agent voices";
            document.body.appendChild(el);
            el.addEventListener("click", () => {
                audioQueue.unlock();
                el.classList.remove("visible");
            });
        }
        el.classList.add("visible");
    }

    function hideAudioPrompt() {
        const el = document.getElementById("audio-prompt");
        if (el) el.classList.remove("visible");
    }

    // ─── Helpers ────────────────────────────────────────────────────

    function svgEl(type, attrs) {
        const el = document.createElementNS(SVG_NS, type);
        for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
        return el;
    }

    function esc(str) {
        const d = document.createElement("div");
        d.appendChild(document.createTextNode(str));
        return d.innerHTML;
    }

})();
