let socket = null;
let currentSessionId = null;
let pingInterval = null;
let isGenerating = false;

const chatContainer = document.getElementById("chat-container");
const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const chatList = document.getElementById("chat-list");
const newChatButton = document.getElementById("new-chat");
const clearAllButton = document.getElementById("clear-all");
const modelSelector = document.getElementById("model-selector");

const MessageType = {
  MESSAGE: "message",
  THINKING: "thinking",
  CONTENT_CHUNK: "content_chunk",
  TITLE_UPDATE: "title_update",
  PING: "ping",
  PONG: "pong",
  CANCEL: "cancel",
  ERROR: "error",
};

const messageHandlers = {
  [MessageType.MESSAGE]: handleIncomingMessage,
  [MessageType.THINKING]: handleThinking,
  [MessageType.CONTENT_CHUNK]: handleContentChunk,
  [MessageType.TITLE_UPDATE]: handleTitleUpdate,
  [MessageType.PONG]: handlePong,
  [MessageType.ERROR]: handleErrorMessage,
};

let currentAssistantMessageDiv = null;
let currentAssistantContent = "";

// Configure marked to handle line breaks properly
marked.setOptions({
  breaks: true,
  gfm: true,
});

function setGenerating(state) {
  isGenerating = state;
  if (isGenerating) {
    sendButton.classList.add("stop-mode");
    sendButton.innerHTML = '<span class="material-icons">stop</span>';
  } else {
    sendButton.classList.remove("stop-mode");
    sendButton.innerHTML = '<span class="material-icons">send</span>';
  }
}

async function init() {
  connectWebSocket();
  await loadSessions();
  await loadModels();

  // Create an initial session if none exist
  const response = await fetch("/api/chats");
  const data = await response.json();
  if (data.sessions.length === 0) {
    await createNewSession();
  } else {
    await switchSession(data.sessions[0].session_id);
  }
}

async function loadModels() {
  const response = await fetch("/api/models");
  const data = await response.json();
  modelSelector.innerHTML = "";
  data.models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    modelSelector.appendChild(option);
  });
}

async function createNewSession() {
  const response = await fetch("/api/chats", { method: "POST" });
  const data = await response.json();
  await loadSessions();
  await switchSession(data.session_id);
  return data.session_id;
}

async function loadSessions() {
  const response = await fetch("/api/chats");
  const data = await response.json();
  chatList.innerHTML = "";
  data.sessions.forEach((session) => {
    const sid = session.session_id;
    const title = session.title;

    const li = document.createElement("li");
    li.className = "session-item";
    li.dataset.sessionId = sid;
    if (sid === currentSessionId) {
      li.classList.add("active");
    }

    const span = document.createElement("span");
    span.textContent = title;
    span.onclick = () => switchSession(sid);
    li.appendChild(span);

    const deleteBtn = document.createElement("button");
    deleteBtn.innerHTML = '<span class="material-icons">delete</span>';
    deleteBtn.className = "delete-session";
    deleteBtn.onclick = (e) => {
      e.stopPropagation();
      deleteSession(sid);
    };
    li.appendChild(deleteBtn);

    chatList.appendChild(li);
  });
}

async function deleteSession(sessionId) {
  if (!confirm("Are you sure you want to delete this session?")) return;

  await fetch(`/api/chats/${sessionId}`, { method: "DELETE" });
  if (currentSessionId === sessionId) {
    currentSessionId = null;
    messagesDiv.innerHTML = "";
  }
  await loadSessions();

  const response = await fetch("/api/chats");
  const data = await response.json();
  if (data.sessions.length > 0) {
    if (!currentSessionId) await switchSession(data.sessions[0].session_id);
  } else {
    await createNewSession();
  }
}

async function loadHistory(sessionId) {
  const response = await fetch(`/api/chats/${sessionId}/history`);
  const data = await response.json();
  messagesDiv.innerHTML = "";

  let isThinkingOpen = false;

  data.history.forEach((msg, index) => {
    if (msg.role === "user") {
      if (isThinkingOpen) {
        finalizeThinkingIndicator();
        isThinkingOpen = false;
      }
      appendMessage("user", msg.content);
    } else if (msg.role === "assistant") {
      const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0;

      if (msg.thought || hasToolCalls || (msg.content && hasToolCalls)) {
        if (!isThinkingOpen) {
          showThinkingIndicator();
          isThinkingOpen = true;
        }
        if (msg.thought) {
          updateThinkingLog({ type: "thought", content: msg.thought });
        }
        if (hasToolCalls) {
          msg.tool_calls.forEach((tc) => {
            updateThinkingLog({ type: "tool_call", tool: tc.name });
          });
        }
      }

      if (msg.content) {
        if (isThinkingOpen) {
          finalizeThinkingIndicator();
          isThinkingOpen = false;
        }
        appendMessage("assistant", msg.content);
      }

      // Finalize if it's the last message and still thinking
      if (index === data.history.length - 1 && isThinkingOpen) {
        finalizeThinkingIndicator();
        isThinkingOpen = false;
      }
    }
  });
}

async function switchSession(sessionId) {
  currentSessionId = sessionId;
  currentAssistantMessageDiv = null;
  currentAssistantContent = "";
  await loadHistory(sessionId);
  updateActiveSessionInList();
}

function updateActiveSessionInList() {
  const items = chatList.querySelectorAll("li");
  items.forEach((li) => {
    const sid = li.dataset.sessionId;
    if (sid === currentSessionId) {
      li.classList.add("active");
    } else {
      li.classList.remove("active");
    }
  });
}

function connectWebSocket() {
  if (socket && socket.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("Persistent WebSocket connected");
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: MessageType.PING }));
      }
    }, 30000);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const handler = messageHandlers[data.type];
      if (handler) {
        handler(data);
      } else {
        console.warn("Unknown message type:", data.type);
      }
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };

  socket.onerror = (error) => {
    console.error("WebSocket Error:", error);
  };

  socket.onclose = () => {
    console.log("WebSocket connection closed. Reconnecting in 3s...");
    clearInterval(pingInterval);
    setTimeout(connectWebSocket, 3000);
  };
}

function handleIncomingMessage(payload) {
  if (payload.session_id === currentSessionId) {
    setGenerating(false);
    finalizeThinkingIndicator();
    if (currentAssistantMessageDiv) {
      // Just ensure final render is correct
      currentAssistantContent = payload.content;
      const rawHtml = marked.parse(currentAssistantContent);
      const cleanHtml = DOMPurify.sanitize(rawHtml);
      currentAssistantMessageDiv.innerHTML = cleanHtml;
      renderMathInElement(currentAssistantMessageDiv, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      });
      currentAssistantMessageDiv = null;
      currentAssistantContent = "";
    } else {
      appendMessage("assistant", payload.content);
    }
    loadSessions(); // Reload sessions to update title if it was just generated
  }
}

function handleTitleUpdate(payload) {
  loadSessions();
}

function handleContentChunk(payload) {
  if (payload.session_id === currentSessionId) {
    if (!currentAssistantMessageDiv) {
      finalizeThinkingIndicator();
      currentAssistantMessageDiv = document.createElement("div");
      currentAssistantMessageDiv.className = "message assistant-message";
      messagesDiv.appendChild(currentAssistantMessageDiv);
      currentAssistantContent = "";
    }

    currentAssistantContent += payload.content;

    // Parse Markdown and sanitize
    const rawHtml = marked.parse(currentAssistantContent);
    const cleanHtml = DOMPurify.sanitize(rawHtml);
    currentAssistantMessageDiv.innerHTML = cleanHtml;

    // Render LaTeX
    renderMathInElement(currentAssistantMessageDiv, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: false,
    });
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
}

function handleThinking(payload) {
  if (payload.session_id === currentSessionId) {
    if (payload.data) {
      updateThinkingLog(payload.data);
    } else {
      showThinkingIndicator(payload.content || "Assistant is thinking...");
    }
  }
}

function updateThinkingLog(data) {
  let indicator = document.getElementById("thinking-indicator");
  if (!indicator) {
    showThinkingIndicator("Assistant is thinking...");
    indicator = document.getElementById("thinking-indicator");
  }

  const logDiv = indicator.querySelector(".thought-log");
  if (data.type === "thought") {
    logDiv.appendChild(document.createTextNode(data.content));
  } else if (data.type === "tool_call") {
    const toolEl = document.createElement("div");
    toolEl.className = "tool-call";
    toolEl.innerHTML = `<strong>Tool Call:</strong> ${data.tool}\n\n`;
    logDiv.appendChild(toolEl);

    // Update thinking button text
    const button = indicator.querySelector(".thinking-button");
    if (button && !button.classList.contains("finalized")) {
      button.innerHTML = `Calling ${data.tool}<span class="dots"><span>.</span><span>.</span><span>.</span></span>`;
    }
  }

  // Auto scroll the log if it's visible
  if (logDiv.style.display !== "none") {
    logDiv.scrollTop = logDiv.scrollHeight;
  }
}

function handlePong(payload) {}

function handleErrorMessage(payload) {
  console.error("Server Error:", payload.message);
  if (!payload.session_id || payload.session_id === currentSessionId) {
    setGenerating(false);
    finalizeThinkingIndicator();
    appendMessage("system", "Error: " + payload.message);
  }
}

function showThinkingIndicator(text) {
  if (document.getElementById("thinking-indicator")) return;

  const container = document.createElement("div");
  container.id = "thinking-indicator";
  container.className = "assistant-thinking-container";

  const button = document.createElement("button");
  button.className = "thinking-button";
  button.innerHTML = `Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span>`;

  const logDiv = document.createElement("div");
  logDiv.className = "thought-log";
  logDiv.style.display = "none";

  button.onclick = () => {
    const isHidden = logDiv.style.display === "none";
    logDiv.style.display = isHidden ? "block" : "none";
    button.classList.toggle("expanded", isHidden);
    if (isHidden) {
      logDiv.scrollTop = logDiv.scrollHeight;
    }
  };

  container.appendChild(button);
  container.appendChild(logDiv);
  messagesDiv.appendChild(container);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function finalizeThinkingIndicator() {
  const indicator = document.getElementById("thinking-indicator");
  if (indicator) {
    indicator.id = ""; // Remove ID to allow a new one for next message
    const button = indicator.querySelector(".thinking-button");
    if (button) {
      button.innerHTML = "View Thought Process";
      button.classList.add("finalized");
    }
  }
}

function removeThinkingIndicator() {
  const indicator = document.getElementById("thinking-indicator");
  if (indicator) indicator.remove();
}

function appendMessage(role, text) {
  const msgElement = document.createElement("div");
  msgElement.className = `message ${role}-message`;

  if (role === "assistant") {
    // Parse Markdown and sanitize
    const rawHtml = marked.parse(text);
    const cleanHtml = DOMPurify.sanitize(rawHtml);
    msgElement.innerHTML = cleanHtml;

    // Render LaTeX
    renderMathInElement(msgElement, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: false,
    });
  } else {
    // For user messages, we can just use textContent or simple styling
    msgElement.textContent = text;
  }

  messagesDiv.appendChild(msgElement);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
  if (isGenerating) return;

  const text = userInput.value.trim();
  const model = modelSelector.value;
  if (
    text &&
    model &&
    socket &&
    socket.readyState === WebSocket.OPEN &&
    currentSessionId
  ) {
    setGenerating(true);
    appendMessage("user", text);
    socket.send(
      JSON.stringify({
        type: MessageType.MESSAGE,
        session_id: currentSessionId,
        content: text,
        model: model,
      }),
    );
    userInput.value = "";
    userInput.style.height = "auto";
  }
}

function cancelMessage() {
  if (
    socket &&
    socket.readyState === WebSocket.OPEN &&
    currentSessionId &&
    isGenerating
  ) {
    socket.send(
      JSON.stringify({
        type: MessageType.CANCEL,
        session_id: currentSessionId,
      }),
    );
    setGenerating(false);
  }
}

sendButton.addEventListener("click", () => {
  if (isGenerating) {
    cancelMessage();
  } else {
    sendMessage();
  }
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!isGenerating) {
      sendMessage();
    }
  }
});

userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = userInput.scrollHeight + "px";

  // Show scrollbar if max-height reached
  if (userInput.scrollHeight > 200) {
    userInput.style.overflowY = "auto";
  } else {
    userInput.style.overflowY = "hidden";
  }
});

newChatButton.addEventListener("click", createNewSession);

async function clearAllSessions() {
  if (
    !confirm(
      "Are you sure you want to clear ALL chat history? This cannot be undone.",
    )
  )
    return;

  await fetch("/api/chats", { method: "DELETE" });
  currentSessionId = null;
  messagesDiv.innerHTML = "";
  await loadSessions();
  await createNewSession();
}

clearAllButton.addEventListener("click", clearAllSessions);

init();
