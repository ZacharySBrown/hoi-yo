/**
 * HOI-YO Launcher -- Client Application
 *
 * Game setup, role selection, persona assignment, and launch flow.
 */
(function () {
    "use strict";

    // ─── Constants ──────────────────────────────────────────────────

    const TAGS = ["GER", "SOV", "USA", "ENG", "JAP", "ITA"];

    const NATIONS = {
        GER: { name: "Germany",        flag: "\u{1F1E9}\u{1F1EA}" },
        SOV: { name: "Soviet Union",   flag: "\u{1F1F7}\u{1F1FA}" },
        USA: { name: "United States",  flag: "\u{1F1FA}\u{1F1F8}" },
        ENG: { name: "United Kingdom", flag: "\u{1F1EC}\u{1F1E7}" },
        JAP: { name: "Japan",          flag: "\u{1F1EF}\u{1F1F5}" },
        ITA: { name: "Italy",          flag: "\u{1F1EE}\u{1F1F9}" },
    };

    // ─── State ──────────────────────────────────────────────────────

    let currentRole = "observer";   // "observer" | "player"
    let playerTag = null;
    let selectedSpeed = 3;
    let availablePersonas = {};     // { GER: [{id, name}, ...], ... }
    let enabledNations = {};        // { GER: true, ... }
    let launchConfig = null;

    // ─── DOM Refs ───────────────────────────────────────────────────

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ─── Boot ───────────────────────────────────────────────────────

    document.addEventListener("DOMContentLoaded", () => {
        initState();
        buildOpponentsGrid();
        initRoleSelector();
        initSpeedControls();
        initSetup();
        initLaunch();
        checkSetup();
        loadPersonas();
    });

    // ─── Init State ─────────────────────────────────────────────────

    function initState() {
        TAGS.forEach((tag) => { enabledNations[tag] = true; });
    }

    // ─── Opponents Grid ─────────────────────────────────────────────

    function buildOpponentsGrid() {
        const grid = $("#opponents-grid");
        grid.innerHTML = "";

        TAGS.forEach((tag) => {
            const n = NATIONS[tag];
            const row = document.createElement("div");
            row.className = "opponent-row";
            row.id = "opp-" + tag;
            row.innerHTML =
                '<span class="opponent-flag">' + n.flag + '</span>' +
                '<span class="opponent-name">' + n.name + '</span>' +
                '<div class="opponent-persona" id="persona-cell-' + tag + '">' +
                    '<select class="persona-select" id="persona-' + tag + '">' +
                        '<option value="">Loading...</option>' +
                    '</select>' +
                '</div>' +
                '<div class="opponent-toggle">' +
                    '<input type="checkbox" id="enable-' + tag + '" checked>' +
                '</div>';
            grid.appendChild(row);

            // Toggle handler
            const checkbox = row.querySelector("#enable-" + tag);
            checkbox.addEventListener("change", () => {
                enabledNations[tag] = checkbox.checked;
                row.classList.toggle("disabled", !checkbox.checked);
            });
        });
    }

    // ─── Role Selector ──────────────────────────────────────────────

    function initRoleSelector() {
        const radioObserver = $("#role-observer");
        const radioPlayer = $("#role-player");
        const playAsSelect = $("#play-as-select");

        radioObserver.addEventListener("change", () => {
            if (radioObserver.checked) {
                currentRole = "observer";
                playerTag = null;
                playAsSelect.disabled = true;
                updateGrid();
            }
        });

        radioPlayer.addEventListener("change", () => {
            if (radioPlayer.checked) {
                currentRole = "player";
                playerTag = playAsSelect.value;
                playAsSelect.disabled = false;
                updateGrid();
            }
        });

        playAsSelect.addEventListener("change", () => {
            if (currentRole === "player") {
                playerTag = playAsSelect.value;
                updateGrid();
            }
        });
    }

    function updateGrid() {
        TAGS.forEach((tag) => {
            const row = $("#opp-" + tag);
            const cell = $("#persona-cell-" + tag);
            const checkbox = $("#enable-" + tag);

            if (currentRole === "player" && tag === playerTag) {
                row.classList.add("is-player");
                cell.innerHTML = '<span class="you-badge">YOU</span>';
                checkbox.checked = true;
                checkbox.disabled = true;
                enabledNations[tag] = true;
                row.classList.remove("disabled");
            } else {
                row.classList.remove("is-player");
                rebuildPersonaDropdown(tag);
                checkbox.disabled = false;
            }
        });
    }

    // ─── Persona Loading ────────────────────────────────────────────

    function loadPersonas() {
        fetch("/api/personas/available")
            .then((r) => r.json())
            .then((data) => {
                availablePersonas = data;
                TAGS.forEach((tag) => rebuildPersonaDropdown(tag));
            })
            .catch((err) => {
                console.warn("Could not load personas:", err);
                // Leave dropdowns with placeholder text
            });
    }

    function rebuildPersonaDropdown(tag) {
        const cell = $("#persona-cell-" + tag);
        if (!cell) return;

        // Don't rebuild if showing YOU badge
        if (currentRole === "player" && tag === playerTag) return;

        const personas = availablePersonas[tag] || [];
        let html = '<select class="persona-select" id="persona-' + tag + '">';

        if (personas.length === 0) {
            html += '<option value="default">Default AI</option>';
        } else {
            personas.forEach((p, i) => {
                const selected = personas.length === 1 ? " selected" : "";
                const id = typeof p === "object" ? p.id : p;
                const name = typeof p === "object" ? p.name : p;
                html += '<option value="' + id + '"' + selected + '>' + name + '</option>';
            });
        }

        html += '</select>';
        cell.innerHTML = html;
    }

    function randomizePersonas() {
        TAGS.forEach((tag) => {
            if (currentRole === "player" && tag === playerTag) return;

            const select = $("#persona-" + tag);
            if (!select) return;

            const options = select.options;
            if (options.length > 1) {
                const idx = Math.floor(Math.random() * options.length);
                select.selectedIndex = idx;
            }
        });
    }

    // ─── Speed Controls ─────────────────────────────────────────────

    function initSpeedControls() {
        $$(".speed-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                $$(".speed-btn").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                selectedSpeed = parseInt(btn.dataset.speed, 10);
            });
        });
    }

    // ─── Setup ──────────────────────────────────────────────────────

    function initSetup() {
        const setupBtn = $("#setup-btn");
        const overlay = $("#setup-overlay");
        const saveBtn = $("#setup-save-btn");
        const changeBtn = $("#status-change-btn");

        setupBtn.addEventListener("click", () => showOverlay("setup-overlay"));
        changeBtn.addEventListener("click", () => showOverlay("setup-overlay"));

        saveBtn.addEventListener("click", () => {
            const path = $("#hoi4-path-input").value.trim();
            if (path) {
                saveSetup(path);
            }
        });

        // Close overlay on click outside card
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) hideOverlay("setup-overlay");
        });
    }

    function checkSetup() {
        fetch("/api/setup/status")
            .then((r) => r.json())
            .then((data) => {
                updateStatusBar(data);
                if (data.hoi4_path) {
                    $("#hoi4-path-input").value = data.hoi4_path;
                }
                if (!data.hoi4_found) {
                    showOverlay("setup-overlay");
                }
            })
            .catch((err) => {
                console.warn("Setup check failed:", err);
                updateStatusBar({ hoi4_found: false, hoi4_path: "" });
            });
    }

    function saveSetup(path) {
        fetch("/api/setup/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ hoi4_path: path }),
        })
            .then((r) => r.json())
            .then((data) => {
                hideOverlay("setup-overlay");
                updateStatusBar(data);
            })
            .catch((err) => {
                console.error("Save setup failed:", err);
            });
    }

    function updateStatusBar(data) {
        const el = $("#status-text");
        if (data.hoi4_found) {
            el.innerHTML =
                'HOI4: <span class="status-ok">' +
                truncatePath(data.hoi4_path || "detected") +
                ' \u2713</span>';
        } else {
            el.innerHTML =
                'HOI4: <span class="status-warn">Not found \u26A0</span>';
        }
    }

    function truncatePath(p) {
        if (p.length > 50) {
            return "\u2026" + p.slice(-47);
        }
        return p;
    }

    // ─── Launch ─────────────────────────────────────────────────────

    function initLaunch() {
        const launchBtn = $("#launch-btn");
        const readyBtn = $("#ready-btn");

        launchBtn.addEventListener("click", onLaunch);
        readyBtn.addEventListener("click", onReady);
    }

    function collectConfig() {
        const personas = {};
        TAGS.forEach((tag) => {
            if (!enabledNations[tag]) return;
            if (currentRole === "player" && tag === playerTag) return;

            const select = $("#persona-" + tag);
            if (select) {
                personas[tag] = select.value || "default";
            }
        });

        return {
            player_tag: currentRole === "player" ? playerTag : null,
            personas: personas,
            speed: selectedSpeed,
            popcorn: $("#opt-popcorn").checked,
            deep_dive: $("#opt-deepdive").checked,
        };
    }

    function onLaunch() {
        launchConfig = collectConfig();

        // Update instruction text with player's country
        if (launchConfig.player_tag) {
            const n = NATIONS[launchConfig.player_tag];
            $("#instruction-country").innerHTML =
                'Pick <span class="step-highlight">' +
                n.flag + " " + n.name +
                '</span>';
        } else {
            $("#instruction-country").innerHTML =
                'Pick <span class="step-highlight">any country</span> (AI controls all)';
        }

        // Disable launch button to prevent double-click
        $("#launch-btn").disabled = true;

        fetch("/api/game/launch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(launchConfig),
        })
            .then((r) => {
                if (!r.ok) throw new Error("Launch failed: " + r.status);
                return r.json();
            })
            .then(() => {
                showOverlay("post-launch-overlay");
            })
            .catch((err) => {
                console.error("Launch error:", err);
                $("#launch-btn").disabled = false;
                // Show error inline -- keep it simple
                alert("Launch failed. Check the console for details.");
            });
    }

    function onReady() {
        if (!launchConfig) return;

        fetch("/api/game/ready", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(launchConfig),
        })
            .then((r) => {
                if (!r.ok) throw new Error("Ready call failed: " + r.status);
                return r.json();
            })
            .then(() => {
                window.location.href = "/dashboard";
            })
            .catch((err) => {
                console.error("Ready error:", err);
                // Redirect anyway -- the dashboard will try to connect
                window.location.href = "/dashboard";
            });
    }

    // ─── Overlay Helpers ────────────────────────────────────────────

    function showOverlay(id) {
        $("#" + id).classList.add("visible");
    }

    function hideOverlay(id) {
        $("#" + id).classList.remove("visible");
    }

})();
