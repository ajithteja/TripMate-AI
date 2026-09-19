(function () {
  "use strict";

  const CONVOS_KEY = "tripmate_convos";
  const ACTIVE_KEY = "tripmate_active";
  const LEGACY_CHAT_KEY = "tripmate_chat";
  const LEGACY_THREAD_KEY = "tripmate_thread_id";

  const $ = (sel) => document.querySelector(sel);

  const appEl = $(".app");
  const chatEl = $("#chat");
  const messagesEl = $("#messages");
  const welcomeEl = $("#welcome");
  const inputEl = $("#input");
  const sendBtn = $("#sendBtn");
  const newChatBtn = $("#newChatBtn");
  const chipsEl = $("#chips");
  const sidebarEl = $("#sidebar");
  const sidebarToggle = $("#sidebarToggle");
  const sidebarClose = $("#sidebarClose");
  const sidebarNewBtn = $("#sidebarNewBtn");
  const convListEl = $("#convList");
  const overlayEl = $("#overlay");

  const state = {
    convos: [],
    activeId: null,
    draft: null,
    busy: false,
    loadingEl: null,
    stepTimer: null,
    stepIndex: 0,
  };

  const AGENT_STEPS = [
    "Contacting the flight agent…",
    "Searching hotel options…",
    "Building your itinerary…",
    "Crafting the final response…",
  ];

  function esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function clip(str, n) {
    const s = String(str || "");
    return s.length <= n ? s : s.slice(0, n - 1).trim() + "…";
  }

  function newId() {
    return "conv_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function fmtTime(ts) {
    if (!ts) return "";
    const d = new Date(ts);
    const now = Date.now();
    const diff = now - ts;
    if (diff < 60000) return "just now";
    if (diff < 3600000) return Math.floor(diff / 60000) + " min ago";
    if (diff < 86400000) return Math.floor(diff / 3600000) + " hr ago";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function inline(text) {
    let t = esc(text);
    t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
    t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    t = t.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    t = t.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    t = t.replace(
      /(^|\s)(https?:\/\/[^\s<]+)/g,
      '$1<a href="$2" target="_blank" rel="noopener">$2</a>'
    );
    return t;
  }

  function renderMarkdown(src) {
    if (!src) return "";
    const lines = String(src).replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let listType = null;
    let listItems = [];

    const closeList = () => {
      if (listType) {
        html += "<" + listType + ">" + listItems.join("") + "</" + listType + ">";
        listItems = [];
        listType = null;
      }
    };

    const pushParagraph = (text) => {
      if (text) html += "<p>" + inline(text) + "</p>";
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (/^```/.test(trimmed)) {
        closeList();
        const buf = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i].trim())) {
          buf.push(lines[i]);
          i++;
        }
        const code = esc(buf.join("\n"));
        if (code) {
          html += "<pre><code>" + code + "</code></pre>";
        }
        continue;
      }

      if (!trimmed) {
        closeList();
        continue;
      }

      let m;
      if ((m = /^(#{1,6})\s+(.*)$/.exec(trimmed))) {
        closeList();
        const level = m[1].length;
        html += "<h" + level + ">" + inline(m[2]) + "</h" + level + ">";
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        closeList();
        html += "<hr>";
        continue;
      }

      if (/^>/.test(trimmed)) {
        closeList();
        html += "<blockquote>" + inline(trimmed.replace(/^>\s?/, "")) + "</blockquote>";
        continue;
      }

      if ((m = /^([-*+])\s+(.*)$/.exec(trimmed))) {
        if (listType !== "ul") {
          closeList();
          listType = "ul";
        }
        listItems.push("<li>" + inline(m[2]));
        continue;
      }

      if ((m = /^(\d+)[.)]\s+(.*)$/.exec(trimmed))) {
        if (listType !== "ol") {
          closeList();
          listType = "ol";
        }
        listItems.push("<li>" + inline(m[2]));
        continue;
      }

      if (listType && /^\s+/.test(line)) {
        listItems[listItems.length - 1] += "<br>" + inline(trimmed);
        continue;
      }

      closeList();
      let para = trimmed;
      while (i + 1 < lines.length && lines[i + 1].trim() && !/^(#|```)/.test(lines[i + 1].trim())) {
        i++;
        para += " " + lines[i].trim();
      }
      pushParagraph(para);
    }

    closeList();
    return html;
  }

  function rowEl(kind, bubble, extraClass) {
    const row = document.createElement("div");
    row.className = "msg " + kind + (extraClass ? " " + extraClass : "");

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = '<svg class="icon"><use href="#i-plane"></use></svg>';

    const bubbleEl = document.createElement("div");
    bubbleEl.className = "bubble";
    bubbleEl.appendChild(bubble);

    row.appendChild(avatar);
    row.appendChild(bubbleEl);
    return row;
  }

  function appendUserMessage(text) {
    const content = document.createElement("div");
    content.textContent = text;
    messagesEl.appendChild(rowEl("user", content));
    scrollToBottom();
  }

  function buildBotBubble(data) {
    const wrap = document.createElement("div");

    const md = document.createElement("div");
    md.className = "md";
    md.innerHTML = renderMarkdown(data.answer);
    wrap.appendChild(md);

    const hasFlights = data.flight_results && String(data.flight_results).trim();
    const hasHotels = data.hotel_results && String(data.hotel_results).trim();
    const hasItinerary = data.itinerary && String(data.itinerary).trim();

    if (hasFlights || hasHotels || hasItinerary) {
      const details = document.createElement("div");
      details.className = "details";

      if (hasFlights) {
        details.appendChild(
          detailEl("Flight Information", "i-plane", String(data.flight_results).trim())
        );
      }
      if (hasHotels) {
        details.appendChild(
          detailEl("Hotel Suggestions", "i-home", String(data.hotel_results).trim())
        );
      }
      if (hasItinerary) {
        details.appendChild(
          detailEl("Itinerary", "i-cal", String(data.itinerary).trim())
        );
      }

      wrap.appendChild(details);
    }

    if (data.llm_calls) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.innerHTML =
        '<span class="dot"></span><span>Planned by 4 agents &middot; ' +
        esc(data.llm_calls) +
        " model runs</span>";
      wrap.appendChild(meta);
    }

    return wrap;
  }

  function detailEl(label, iconId, rawContent) {
    const det = document.createElement("details");

    const summary = document.createElement("summary");
    summary.innerHTML =
      '<span class="d-icon"><svg class="icon"><use href="#' +
      iconId +
      '"></use></svg></span>' +
      "<span>" +
      esc(label) +
      '</span><svg class="icon chev"><use href="#i-chev"></use></svg>';

    const panel = document.createElement("div");
    panel.className = "panel md";
    panel.innerHTML = renderMarkdown(rawContent);
    if (iconId === "i-plane") {
      panel.className = "panel plain";
      panel.textContent = rawContent;
    }

    det.appendChild(summary);
    det.appendChild(panel);
    return det;
  }

  function appendBotMessage(data) {
    const bubble = buildBotBubble(data);
    messagesEl.appendChild(rowEl("bot", bubble));
    scrollToBottom();
  }

  function appendError(message) {
    const content = document.createElement("div");
    content.textContent = message;
    messagesEl.appendChild(rowEl("bot", content, "error"));
    scrollToBottom();
  }

  function startLoading() {
    if (state.loadingEl) return state.loadingEl;

    const content = document.createElement("div");
    content.className = "typing-steps";

    const typ = document.createElement("span");
    typ.className = "dots";
    typ.innerHTML = "<span></span><span></span><span></span>";

    const step = document.createElement("b");
    step.textContent = AGENT_STEPS[0];

    content.appendChild(typ);
    content.appendChild(step);

    const row = rowEl("bot", content, "loading");
    messagesEl.appendChild(row);
    scrollToBottom();

    state.loadingEl = row;
    state.stepIndex = 0;
    state.stepTimer = setInterval(() => {
      state.stepIndex = (state.stepIndex + 1) % AGENT_STEPS.length;
      step.textContent = AGENT_STEPS[state.stepIndex];
    }, 1600);

    return row;
  }

  function stopLoading() {
    if (state.stepTimer) {
      clearInterval(state.stepTimer);
      state.stepTimer = null;
    }
    if (state.loadingEl) {
      state.loadingEl.remove();
      state.loadingEl = null;
    }
  }

  function setComposerEnabled(enabled) {
    if (enabled) {
      inputEl.disabled = false;
      sendBtn.disabled = !inputEl.value.trim() || state.busy;
    } else {
      inputEl.disabled = true;
      sendBtn.disabled = true;
    }
  }

  function hideWelcome() {
    welcomeEl.hidden = true;
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      chatEl.scrollTop = chatEl.scrollHeight;
    });
  }

  function autoGrow() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px";
    sendBtn.disabled = !inputEl.value.trim() || state.busy;
  }

  function closeSidebar() {
    appEl.classList.remove("sidebar-open");
  }

  function openSidebar() {
    renderSidebar();
    appEl.classList.add("sidebar-open");
  }

  /* ----------------------------------------------------------
     Storage
     ---------------------------------------------------------- */

  function writeStore() {
    try {
      localStorage.setItem(CONVOS_KEY, JSON.stringify(state.convos));
      localStorage.setItem(ACTIVE_KEY, state.activeId || "");
    } catch (e) {
      return;
    }
  }

  function readStore() {
    try {
      const parsed = JSON.parse(localStorage.getItem(CONVOS_KEY) || "[]");
      state.convos = Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      state.convos = [];
    }
    state.activeId = localStorage.getItem(ACTIVE_KEY) || null;
  }

  async function loadConversationsFromDB() {
    try {
      const res = await fetch("/api/conversations");
      const data = await res.json();
      if (!data.success || !Array.isArray(data.conversations)) return;

      const dbConvos = data.conversations;
      const localConvos = state.convos;

      // Index local conversations by threadId for quick lookup
      const localByThreadId = {};
      localConvos.forEach((c) => {
        if (c.threadId) localByThreadId[c.threadId] = c;
      });

      const merged = [];
      const seenThreadIds = new Set();

      // First pass: add DB conversations (they are the source of truth)
      dbConvos.forEach((dbConv) => {
        seenThreadIds.add(dbConv.thread_id);
        const local = localByThreadId[dbConv.thread_id];

        // Build messages from DB data
        const messages = [];
        if (dbConv.messages && dbConv.messages.length) {
          dbConv.messages.forEach((m) => {
            if (m.role === "human") {
              messages.push({ role: "user", content: m.content });
            } else if (m.role === "ai" && m.content) {
              // Skip intermediate AI messages ("Flight results fetched.", etc.)
              const skip = ["Flight results fetched.", "Hotel information fetched."];
              const trimmed = m.content.trim();
              if (!skip.includes(trimmed)) {
                messages.push({
                  role: "bot",
                  data: {
                    answer: m.content,
                    flight_results: dbConv.flight_results || "",
                    hotel_results: dbConv.hotel_results || "",
                    itinerary: dbConv.itinerary || "",
                    llm_calls: dbConv.llm_calls || 0,
                  },
                });
              }
            }
          });
        }

        // Use the title from user_query
        const title = dbConv.title || "New conversation";

        // Parse the timestamp
        let ts = Date.now();
        if (dbConv.ts) {
          const parsed = new Date(dbConv.ts);
          if (!isNaN(parsed.getTime())) ts = parsed.getTime();
        }

        merged.push({
          id: local ? local.id : "conv_" + dbConv.thread_id.replace(/[^a-zA-Z0-9]/g, ""),
          title: local && local.title ? local.title : title,
          threadId: dbConv.thread_id,
          updatedAt: local ? local.updatedAt : ts,
          messages: messages,
        });
      });

      // Second pass: add any local-only conversations (no thread_id or not in DB)
      localConvos.forEach((c) => {
        if (!c.threadId || !seenThreadIds.has(c.threadId)) {
          merged.push(c);
        }
      });

      // Sort by updatedAt descending
      merged.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));

      state.convos = merged;
      writeStore();
      renderSidebar();
    } catch (e) {
      console.error("Failed to load conversations from DB:", e);
    }
  }

  function migrateLegacy() {
    try {
      const chat = JSON.parse(localStorage.getItem(LEGACY_CHAT_KEY) || "[]");
      if (!Array.isArray(chat) || !chat.length) return;
      const first = chat.find((m) => m.role === "user");
      const convo = {
        id: newId(),
        title: clip(first && first.content, 48),
        threadId: localStorage.getItem(LEGACY_THREAD_KEY) || null,
        updatedAt: Date.now(),
        messages: chat,
      };
      state.convos.unshift(convo);
      state.activeId = convo.id;
    } finally {
      localStorage.removeItem(LEGACY_CHAT_KEY);
      localStorage.removeItem(LEGACY_THREAD_KEY);
    }
  }

  function getActive() {
    return state.convos.find((c) => c.id === state.activeId) || null;
  }

  function ensureActive() {
    let convo = getActive();
    if (convo) return convo;
    if (state.draft) {
      convo = state.draft;
      state.draft = null;
    } else {
      convo = { id: newId(), title: "", threadId: null, updatedAt: Date.now(), messages: [] };
    }
    state.convos.unshift(convo);
    state.activeId = convo.id;
    writeStore();
    renderSidebar();
    return convo;
  }

  function bumpToTop(convo) {
    const idx = state.convos.indexOf(convo);
    if (idx > 0) {
      state.convos.splice(idx, 1);
      state.convos.unshift(convo);
    }
  }

  /* ----------------------------------------------------------
     Conversation rendering
     ---------------------------------------------------------- */

  function renderChat(convo) {
    messagesEl.innerHTML = "";
    (convo.messages || []).forEach((msg) => {
      if (msg.role === "user") {
        appendUserMessage(msg.content || "");
      } else if (msg.role === "bot" && msg.data) {
        appendBotMessage(msg.data);
      }
    });
    if (convo.messages && convo.messages.length) {
      hideWelcome();
    } else {
      welcomeEl.hidden = false;
    }
    scrollToBottom();
  }

  function renderSidebar() {
    const list = state.convos;
    if (!list.length) {
      convListEl.innerHTML = '<p class="conv-empty">No conversations yet. Start a new trip to begin.</p>';
      return;
    }

    convListEl.innerHTML = "";
    list.forEach((convo) => {
      const item = document.createElement("div");
      item.className = "conv-item" + (convo.id === state.activeId ? " active" : "");

      const main = document.createElement("button");
      main.className = "conv-main";
      main.dataset.id = convo.id;

      const title = document.createElement("span");
      title.className = "conv-title";
      title.textContent = convo.title || "New conversation";

      const meta = document.createElement("span");
      meta.className = "conv-meta";
      meta.textContent = fmtTime(convo.updatedAt) + (convo.messages && convo.messages.length ? "" : " · draft");

      main.appendChild(title);
      main.appendChild(meta);

      const del = document.createElement("button");
      del.className = "conv-del";
      del.dataset.id = convo.id;
      del.setAttribute("aria-label", "Delete conversation");
      del.innerHTML = '<svg class="icon"><use href="#i-trash"></use></svg>';

      item.appendChild(main);
      item.appendChild(del);
      convListEl.appendChild(item);
    });
  }

  function openConvo(id) {
    if (state.busy) return;
    const convo = state.convos.find((c) => c.id === id);
    if (!convo) return;
    state.activeId = convo.id;
    state.draft = null;
    writeStore();
    renderChat(convo);
    renderSidebar();
    if (window.innerWidth <= 760) closeSidebar();
    setComposerEnabled(true);
    inputEl.focus();
  }

  function deleteConvo(id) {
    if (state.busy) return;
    const idx = state.convos.findIndex((c) => c.id === id);
    if (idx < 0) return;
    state.convos.splice(idx, 1);
    if (state.activeId === id) {
      state.activeId = state.convos.length ? state.convos[0].id : null;
      if (state.activeId) {
        renderChat(getActive());
      } else {
        messagesEl.innerHTML = "";
        welcomeEl.hidden = false;
      }
    }
    writeStore();
    renderSidebar();
  }

  function startNewChat() {
    if (state.busy) return;
    stopLoading();
    state.busy = false;
    state.activeId = null;
    state.draft = { id: newId(), title: "", threadId: null, updatedAt: Date.now(), messages: [] };
    messagesEl.innerHTML = "";
    welcomeEl.hidden = false;
    setComposerEnabled(true);
    renderSidebar();
    closeSidebar();
    inputEl.focus();
  }

  /* ----------------------------------------------------------
     API
     ---------------------------------------------------------- */

  async function sendMessage(text) {
    const trimmed = String(text).trim();
    if (!trimmed || state.busy) return;

    state.busy = true;
    setComposerEnabled(false);
    hideWelcome();

    const convo = ensureActive();
    convo.updatedAt = Date.now();
    convo.messages.push({ role: "user", content: trimmed });
    if (!convo.title) convo.title = clip(trimmed, 48);
    bumpToTop(convo);
    writeStore();
    renderSidebar();

    appendUserMessage(trimmed);
    startLoading();

    try {
      const res = await fetch("/api/travel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          thread_id: convo.threadId || null,
        }),
      });

      const data = await res.json().catch(() => null);

      stopLoading();

      if (!res.ok || !data || data.success !== true) {
        const reason = (data && data.error) || "The travel service returned an error.";
        throw new Error(reason);
      }

      convo.threadId = data.thread_id || convo.threadId;
      convo.updatedAt = Date.now();
      convo.messages.push({
        role: "bot",
        data: {
          answer: data.answer,
          flight_results: data.flight_results,
          hotel_results: data.hotel_results,
          itinerary: data.itinerary,
          llm_calls: data.llm_calls,
        },
      });
      bumpToTop(convo);
      writeStore();
      renderSidebar();

      if (state.activeId === convo.id) {
        appendBotMessage(data);
      }
    } catch (err) {
      stopLoading();
      if (state.activeId === convo.id) {
        appendError("Something went wrong: " + (err && err.message ? err.message : "unknown error"));
      }
    } finally {
      state.busy = false;
      setComposerEnabled(true);
      inputEl.focus();
    }
  }

  /* ----------------------------------------------------------
     UI wiring
     ---------------------------------------------------------- */

  function submit() {
    const text = inputEl.value;
    if (!state.busy && text.trim()) {
      inputEl.value = "";
      autoGrow();
      sendMessage(text);
    }
  }

  inputEl.addEventListener("input", autoGrow);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !state.busy) {
      e.preventDefault();
      submit();
    }
  });

  sendBtn.addEventListener("click", submit);

  if (chipsEl) {
    chipsEl.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (chip && chip.dataset.prompt && !state.busy) {
        inputEl.value = chip.dataset.prompt;
        autoGrow();
        submit();
      }
    });
  }

  sidebarToggle.addEventListener("click", () => {
    if (appEl.classList.contains("sidebar-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  sidebarClose.addEventListener("click", closeSidebar);
  overlayEl.addEventListener("click", closeSidebar);

  newChatBtn.addEventListener("click", startNewChat);
  sidebarNewBtn.addEventListener("click", startNewChat);

  convListEl.addEventListener("click", (e) => {
    const del = e.target.closest(".conv-del");
    if (del) {
      e.stopPropagation();
      deleteConvo(del.dataset.id);
      return;
    }
    const main = e.target.closest(".conv-main");
    if (main) openConvo(main.dataset.id);
  });

  /* ----------------------------------------------------------
     Init
     ---------------------------------------------------------- */

  readStore();
  migrateLegacy();

  let active = getActive();
  if (!active && state.convos.length) {
    active = state.convos[0];
    state.activeId = active.id;
  }

  if (active) {
    renderChat(active);
  } else {
    welcomeEl.hidden = false;
  }

  renderSidebar();
  inputEl.focus();
  autoGrow();

  // Load conversations from DB (overrides localStorage with server truth)
  loadConversationsFromDB().then(() => {
    // Re-render the active conversation after DB load
    const afterActive = getActive();
    if (afterActive) {
      renderChat(afterActive);
      renderSidebar();
    }
  });
})();