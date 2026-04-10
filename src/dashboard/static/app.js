/**
 * HOI-YO Observer Dashboard v2 -- Client Application
 *
 * Clean vanilla JS powering a diplomatic web SVG, nation intelligence
 * cards, event timeline, and real-time WebSocket updates.
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

    // ─── DOM Refs ───────────────────────────────────────────────────

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ─── Boot ───────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", () => {
        buildNationCards();
        buildDiploNodes();
        initSpeedControls();
        initWhisper();
        initTimeline();
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
        if (data.date) {
            $("#game-date").textContent = data.date;
            updateTensionFromDate(data.date);
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
                }
            }
            updateDiploWeb();
            addTimelineEntry(data.turn, data.date, data.decisions);
        }
        if (data.countries) {
            for (const tag of TAGS) {
                if (data.countries[tag]) {
                    latestCountries[tag] = data.countries[tag];
                    updateCardCountry(tag, data.countries[tag]);
                }
            }
            updateDiploNodeSizes();
        }
        if (data.wars) updateWarIndicators(data.wars);
        if (data.cost) updateCostDisplay(data.cost);
    }

    function updateCostDisplay(cost) {
        const el = $("#api-cost");
        if (!el) return;
        const total = cost.total_cost || 0;
        el.textContent = "$" + total.toFixed(2);
        // Color shift: green under $1, yellow $1-5, red $5+
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

        // Mood
        const mood = (dec.mood || "").toLowerCase();
        const moodEl = card.querySelector('[data-field="mood"]');
        moodEl.textContent = mood || "--";
        moodEl.style.background = MOODS[mood] || "#4a4e65";
        moodEl.style.color = DARK_TEXT_MOODS.has(mood) ? "#000" : "#fff";

        // Monologue preview
        const prev = card.querySelector('[data-field="monologue-preview"]');
        if (dec.inner_monologue) {
            const t = dec.inner_monologue.replace(/\n/g, " ");
            prev.textContent = t.length > 140 ? t.substring(0, 140) + "..." : t;
        }

        // Full monologue
        const full = card.querySelector('[data-field="full-monologue"]');
        if (dec.inner_monologue) full.textContent = dec.inner_monologue;

        // Strategy pills
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

        // Threats
        const threatBox = card.querySelector('[data-field="threats"]');
        renderThreats(threatBox, dec.threats || {});

        // Model
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
        // Mark nations that are at war
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

    // ─── Diplomatic Web (SVG) ───────────────────────────────────────

    function buildDiploNodes() {
        const svg = $("#diplo-svg");
        const vb = svg.viewBox.baseVal;
        const cx = vb.width / 2, cy = vb.height / 2;
        const rx = 280, ry = 130;
        const nodesG = $("#diplo-nodes");

        TAGS.forEach((tag, i) => {
            const angle = (Math.PI * 2 * i) / TAGS.length - Math.PI / 2;
            const x = cx + rx * Math.cos(angle);
            const y = cy + ry * Math.sin(angle);
            nodePositions[tag] = { x, y };

            const g = svgEl("g", { class: "diplo-node", "data-tag": tag });

            // War glow circle (hidden by default)
            const warGlow = svgEl("circle", {
                cx: x, cy: y, r: 42, fill: "#ef444400", class: "war-glow",
                filter: "url(#war-pulse)",
            });
            g.appendChild(warGlow);

            // Mood ring
            const ring = svgEl("circle", {
                cx: x, cy: y, r: 34, fill: "none",
                stroke: NATIONS[tag].accent, "stroke-width": 3,
                class: "mood-ring", opacity: 0.6,
            });
            g.appendChild(ring);

            // Inner circle bg
            const bg = svgEl("circle", {
                cx: x, cy: y, r: 30, fill: "#12121f",
                stroke: "#1e1e35", "stroke-width": 1,
                class: "node-bg",
            });
            g.appendChild(bg);

            // Flag emoji
            const flag = svgEl("text", {
                x: x, y: y - 4, "text-anchor": "middle", "dominant-baseline": "central",
                "font-size": "22", class: "node-flag",
            });
            flag.textContent = NATIONS[tag].flag;
            g.appendChild(flag);

            // Country name
            const nameEl = svgEl("text", {
                x: x, y: y + 22, "text-anchor": "middle",
                fill: "#e8e8f0", "font-size": "10", "font-weight": "700",
                "letter-spacing": "0.5",
            });
            nameEl.textContent = NATIONS[tag].name;
            g.appendChild(nameEl);

            // Persona name
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

    function updateDiploWeb() {
        const linesG = $("#diplo-lines");
        linesG.innerHTML = "";

        // Gather all diplomatic relations
        const relations = []; // { from, to, type, value }
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
            const thickness = Math.max(1, Math.min(4, rel.value / 50));
            const isFriendly = rel.type === "befriend" || rel.type === "support" || rel.type === "protect";
            const isHostile = rel.type === "antagonize" || rel.type === "conquer";

            // Offset lines slightly so bidirectional relations don't overlap
            const dx = p2.x - p1.x, dy = p2.y - p1.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const nx = -dy / len * 3, ny = dx / len * 3;

            const line = svgEl("line", {
                x1: p1.x + nx, y1: p1.y + ny,
                x2: p2.x + nx, y2: p2.y + ny,
                stroke: color,
                "stroke-width": thickness,
                "stroke-linecap": "round",
                opacity: isHostile ? 0.8 : 0.5,
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
            const dec = latestDecisions[tag];
            const mood = dec ? (dec.mood || "").toLowerCase() : "";
            const color = MOODS[mood] || NATIONS[tag].accent;
            const ring = document.querySelector(`.diplo-node[data-tag="${tag}"] .mood-ring`);
            if (ring) {
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
                if (atWar) {
                    glow.style.animation = "war-cloud-pulse 2s ease-in-out infinite";
                } else {
                    glow.style.animation = "none";
                }
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
            // Scale radius: base 30, max ~44 for 300+ factories
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

        // Generate headline: pick the most significant diplomatic action
        const headline = generateHeadline(decisions);

        const entry = document.createElement("div");
        entry.className = "tl-entry";

        let moodDots = "";
        TAGS.forEach((tag) => {
            const dec = decisions[tag];
            const mood = dec ? (dec.mood || "").toLowerCase() : "";
            const color = MOODS[mood] || "#4a4e65";
            moodDots += `<span class="tl-mood-dot" style="background:${color}" title="${NATIONS[tag].name}: ${mood || 'unknown'}">${NATIONS[tag].flag}</span>`;
        });

        entry.innerHTML = `
            <div class="tl-marker">
                <span class="tl-turn">T${turn || "?"}</span>
                <span class="tl-date">${esc(date || "")}</span>
            </div>
            <div class="tl-body">
                <div class="tl-headline">${esc(headline)}</div>
                <div class="tl-moods">${moodDots}</div>
            </div>`;

        container.insertBefore(entry, container.firstChild);

        // Cap at 50
        while (container.children.length > 50) container.removeChild(container.lastChild);
    }

    let lastHeadline = "";
    let headlineRotation = 0;

    function generateHeadline(decisions) {
        // Collect ALL interesting events, then pick the most novel one
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
            declare_war: "declares war on",
        };

        // Dramatic priority: war > conquer > antagonize > prepare > contain > alliance > support > protect > befriend
        const priority = {
            declare_war: 100, conquer: 80, antagonize: 60, prepare_for_war: 55,
            contain: 40, alliance: 35, support: 30, protect: 25, befriend: 10,
        };

        for (const tag of TAGS) {
            const dec = decisions[tag];
            if (!dec) continue;

            // Diplomatic events
            if (dec.diplomatic) {
                for (const d of dec.diplomatic) {
                    const src = NATIONS[tag]?.name || tag;
                    const tgt = NATIONS[d.target]?.name || d.target;
                    const verb = verbs[d.strategy_type] || "targets";
                    const score = (priority[d.strategy_type] || 10) + Math.min(d.value / 10, 20);
                    events.push({ text: `${src} ${verb} ${tgt}`, score });
                }
            }

            // Mood-based color events
            if (dec.mood === "panicking") {
                events.push({ text: `${NATIONS[tag]?.name || tag} is PANICKING!`, score: 90 });
            } else if (dec.mood === "aggressive" && dec.military?.length > 3) {
                events.push({ text: `${NATIONS[tag]?.name || tag} mobilizes aggressively`, score: 70 });
            }
        }

        if (events.length === 0) return "Nations deliberate in silence...";

        // Sort by score descending, then pick one we haven't used recently
        events.sort((a, b) => b.score - a.score);

        // Try to avoid repeating the exact same headline
        for (const ev of events) {
            if (ev.text !== lastHeadline) {
                lastHeadline = ev.text;
                return ev.text;
            }
        }

        // If all are repeats, rotate through the top events
        headlineRotation = (headlineRotation + 1) % Math.min(events.length, 6);
        lastHeadline = events[headlineRotation].text;
        return lastHeadline;
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
                showToast(`Whisper sent to ${NATIONS[target.value]?.name || target.value}`);
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
                    const svgEl = document.querySelector(`.diplo-node[data-tag="${p.tag}"] .node-persona`);
                    if (svgEl && p.name) svgEl.textContent = p.name;
                });
            })
            .catch(() => {});
    }

    // ─── Helpers ────────────────────────────────────────────────────

    function updateTensionFromDate(dateStr) {
        const parts = dateStr.split(".");
        const year = parseInt(parts[0], 10);
        const month = parts.length > 1 ? parseInt(parts[1], 10) : 1;
        const total = (1948 - 1936) * 12;
        const elapsed = (year - 1936) * 12 + (month - 1);
        // We use this to keep the timeline fill updated even without explicit tension
    }

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
