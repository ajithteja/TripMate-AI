(function () {
  "use strict";

  const THREAD_KEY = "tripmate_thread_id";
  const CHAT_KEY = "tripmate_chat";

  const $ = (sel) => document.querySelector(sel);

  const chatEl = $("#chat");
  const messagesEl = $("#messages");
  const welcomeEl = $("#welcome");
  const inputEl = $("#input");
  const sendBtn = $("#sendBtn");
  const newChatBtn = $("#newChatBtn");
  const chipsEl = $("#chips");

  const state = {
    threadId: localStorage.getItem(THREAD_KEY) || null,
    busy: false,
    loadingEl: null,
    stepTimer: null,
    stepIndex: 0,
    messages: [],
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

  async function sendMessage(text) {
    const trimmed = String(text).trim();
    if (!trimmed || state.busy) return;

    state.busy = true;
    setComposerEnabled(false);
    hideWelcome();

    appendUserMessage(trimmed);
    startLoading();

    try {
      const res = await fetch("/api/travel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          thread_id: state.threadId,
        }),
      });

      const data = await res.json().catch(() => null);

      stopLoading();

      if (!res.ok || !data || data.success !== true) {
        const reason = (data && data.error) || "The travel service returned an error.";
        throw new Error(reason);
      }

      state.threadId = data.thread_id || null;
      if (state.threadId) localStorage.setItem(THREAD_KEY, state.threadId);

      state.messages.push({
        role: "bot",
        data: {
          answer: data.answer,
          flight_results: data.flight_results,
          hotel_results: data.hotel_results,
          itinerary: data.itinerary,
          llm_calls: data.llm_calls,
        },
      });
      persistChat();

      appendBotMessage(data);
    } catch (err) {
      stopLoading();
      appendError("Something went wrong: " + (err && err.message ? err.message : "unknown error"));
    } finally {
      state.busy = false;
      setComposerEnabled(true);
      inputEl.focus();
    }
  }

  function persistChat() {
    try {
      localStorage.setItem(CHAT_KEY, JSON.stringify(state.messages));
    } catch (e) {
      return;
    }
  }

  function restoreChat() {
    let stored = [];
    try {
      stored = JSON.parse(localStorage.getItem(CHAT_KEY) || "[]");
    } catch (e) {
      stored = [];
    }

    if (!Array.isArray(stored) || stored.length === 0) return false;

    stored.forEach((msg) => {
      if (msg.role === "user") {
        appendUserMessage(msg.content || "");
      } else if (msg.role === "bot" && msg.data) {
        appendBotMessage(msg.data);
      }
    });

    state.messages = stored;
    return true;
  }

  function resetChat() {
    stopLoading();
    state.threadId = null;
    state.messages = [];
    state.busy = false;
    localStorage.removeItem(THREAD_KEY);
    localStorage.removeItem(CHAT_KEY);
    messagesEl.innerHTML = "";
    welcomeEl.hidden = false;
    setComposerEnabled(true);
    inputEl.focus();
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

  inputEl.addEventListener("input", autoGrow);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !state.busy) {
      e.preventDefault();
      submit();
    }
  });

  sendBtn.addEventListener("click", submit);

  function submit() {
    const text = inputEl.value;
    if (!state.busy && text.trim()) {
      inputEl.value = "";
      autoGrow();
      state.messages.push({ role: "user", content: String(text).trim() });
      persistChat();
      sendMessage(text);
    }
  }

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

  newChatBtn.addEventListener("click", resetChat);

  const hasHistory = restoreChat();
  if (hasHistory) hideWelcome();
  inputEl.focus();
  autoGrow();
})();