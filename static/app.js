let socket = null;
let currentSessionId = null;
let pingInterval = null;
let pingTimeout = null;
let isGenerating = false;

const chatContainer = document.getElementById("chat-container");
const messagesDiv = document.getElementById("messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const chatList = document.getElementById("chat-list");
const newChatButton = document.getElementById("new-chat");
const clearAllButton = document.getElementById("clear-all");
const deleteMemoryButton = document.getElementById("delete-memory");
const modelSelector = document.getElementById("model-selector");
const attachButton = document.getElementById("attach-button");
const reasoningButton = document.getElementById("reasoning-button");
const fileInput = document.getElementById("file-input");
const attachmentPreviews = document.getElementById("attachment-previews");
const connectionPill = document.getElementById("connection-pill");
const toastContainer = document.getElementById("toast-container");
const inputArea = document.getElementById("input-area");
const dragOverlay = document.getElementById("drag-overlay");

let pendingAttachments = [];
let dragCounter = 0;

const MessageType = {
  MESSAGE: "message",
  THINKING: "thinking",
  CONTENT_CHUNK: "content_chunk",
  TITLE_UPDATE: "title_update",
  PING: "ping",
  PONG: "pong",
  CANCEL: "cancel",
  ERROR: "error",
  WARNING: "warning",
};

const messageHandlers = {
  [MessageType.MESSAGE]: handleIncomingMessage,
  [MessageType.THINKING]: handleThinking,
  [MessageType.CONTENT_CHUNK]: handleContentChunk,
  [MessageType.TITLE_UPDATE]: handleTitleUpdate,
  [MessageType.PONG]: handlePong,
  [MessageType.ERROR]: handleErrorMessage,
  [MessageType.WARNING]: handleWarningMessage,
};

let currentAssistantMessageDiv = null;
let currentAssistantContent = "";
let currentThought = "";

// Configure marked to handle line breaks properly
marked.setOptions({
  breaks: true,
  gfm: true,
});

function renderMarkdown(text) {
  const rawHtml = marked.parse(text);
  return DOMPurify.sanitize(rawHtml);
}

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

  attachButton.addEventListener("click", () => fileInput.click());
  reasoningButton.addEventListener("click", () => {
    reasoningButton.classList.toggle("active");
  });
  fileInput.addEventListener("change", handleFileSelect);

  inputArea.addEventListener("dragenter", (e) => {
    e.preventDefault();
    dragCounter++;
    if (dragCounter === 1) {
      dragOverlay.classList.add("drag-active");
    }
  });

  inputArea.addEventListener("dragover", (e) => {
    e.preventDefault();
  });

  inputArea.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
      dragOverlay.classList.remove("drag-active");
    }
  });

  inputArea.addEventListener("drop", async (e) => {
    e.preventDefault();
    dragCounter = 0;
    dragOverlay.classList.remove("drag-active");

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      for (const file of files) {
        await uploadFile(file);
      }
    }
  });

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
  const response = await fetch("/api/chats/models");
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
      appendMessage("user", msg.content, msg.attachments || []);
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
            const toolName = tc.function ? tc.function.name : tc.name;
            updateThinkingLog({ type: "tool_call", tool: toolName });
          });
        }
      }

      if (msg.content) {
        if (isThinkingOpen) {
          finalizeThinkingIndicator();
          isThinkingOpen = false;
        }
        appendMessage(
          msg.role,
          msg.content,
          msg.attachments || [],
          msg.metrics,
        );
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
  currentThought = "";
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

function setConnectionStatus(status) {
  if (status === "CONNECTED") {
    connectionPill.classList.remove("disconnected");
    connectionPill.classList.add("connected");
    connectionPill.querySelector("span").textContent = "CONNECTED";
  } else {
    connectionPill.classList.remove("connected");
    connectionPill.classList.add("disconnected");
    connectionPill.querySelector("span").textContent = "DISCONNECTED";
  }
}

function showToast(level, message) {
  const toast = document.createElement("div");
  toast.className = `toast toast-${level.toLowerCase()}`;

  const icon = level === "ERROR" ? "error" : "warning";
  const title = level.toUpperCase();

  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-icon-container">
        <span class="material-icons toast-icon">${icon}</span>
      </div>
      <div class="toast-text">
        <div class="toast-title">${title}</div>
        <div class="toast-desc">${message}</div>
      </div>
      <button class="toast-close">
        <span class="material-icons">close</span>
      </button>
    </div>
    <div class="toast-progress-bar"></div>
  `;

  const closeBtn = toast.querySelector(".toast-close");
  closeBtn.onclick = () => {
    toast.style.animation =
      "toast-slide-in 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) reverse forwards";
    setTimeout(() => toast.remove(), 300);
  };

  toastContainer.appendChild(toast);

  // Auto remove after 5s
  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.animation =
        "toast-slide-in 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) reverse forwards";
      setTimeout(() => toast.remove(), 300);
    }
  }, 5000);
}

function connectWebSocket() {
  if (socket && socket.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("Persistent WebSocket connected");
    setConnectionStatus("CONNECTED");
    if (pingInterval) clearInterval(pingInterval);
    pingInterval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: MessageType.PING }));
        // If no pong in 5s, consider disconnected
        pingTimeout = setTimeout(() => {
          setConnectionStatus("DISCONNECTED");
        }, 5000);
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
    setConnectionStatus("DISCONNECTED");
  };

  socket.onclose = () => {
    console.log("WebSocket connection closed. Reconnecting in 3s...");
    setConnectionStatus("DISCONNECTED");
    clearInterval(pingInterval);
    if (pingTimeout) clearTimeout(pingTimeout);
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
      const textDiv =
        currentAssistantMessageDiv.querySelector(".message-text") ||
        currentAssistantMessageDiv;
      textDiv.innerHTML = cleanHtml;
      renderMathInElement(textDiv, {
        delimiters: [
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      });

      if (payload.metrics) {
        const metricsDiv = document.createElement("div");
        metricsDiv.className = "message-metrics";
        metricsDiv.textContent = `Generated ${payload.metrics.tokens} tokens in ${payload.metrics.time_s.toFixed(2)}s (${payload.metrics.tokens_per_sec.toFixed(1)} tokens/s)`;
        currentAssistantMessageDiv.appendChild(metricsDiv);
      }

      currentAssistantMessageDiv = null;
      currentAssistantContent = "";
    } else {
      appendMessage(
        "assistant",
        payload.content,
        payload.attachments || [],
        payload.metrics,
      );
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

      const textDiv = document.createElement("div");
      textDiv.className = "message-text";
      currentAssistantMessageDiv.appendChild(textDiv);

      messagesDiv.appendChild(currentAssistantMessageDiv);
      currentAssistantContent = "";
    }

    currentAssistantContent += payload.content;
    const textDiv = currentAssistantMessageDiv.querySelector(".message-text");

    // Parse Markdown and sanitize
    const rawHtml = marked.parse(currentAssistantContent);
    const cleanHtml = DOMPurify.sanitize(rawHtml);
    textDiv.innerHTML = cleanHtml;

    // Render LaTeX
    renderMathInElement(textDiv, {
      delimiters: [
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
    currentThought += data.content;
  } else if (data.type === "tool_call") {

    currentThought += `\n\n**Tool Call:** ${data.tool}\n\n`;

    // Update thinking button text
    const button = indicator.querySelector(".thinking-button");
    if (button && !button.classList.contains("finalized")) {
      button.innerHTML = `Calling ${data.tool}<span class="dots"><span>.</span><span>.</span><span>.</span></span>`;
    }
  }

  // Parse Markdown and sanitize
  const cleanHtml = renderMarkdown(currentThought);
  logDiv.innerHTML = cleanHtml;

  // Render LaTeX
  if (typeof renderMathInElement === "function") {
    renderMathInElement(logDiv, {
      delimiters: [
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: false,
    });
  }

  // Auto scroll the log if it's visible
  if (logDiv.style.display !== "none") {
    logDiv.scrollTop = logDiv.scrollHeight;
  }
}

function handlePong(payload) {
  if (pingTimeout) clearTimeout(pingTimeout);
  setConnectionStatus("CONNECTED");
}

function handleErrorMessage(payload) {
  console.error("Server Error:", payload.message);
  showToast("ERROR", payload.message);
  if (!payload.session_id || payload.session_id === currentSessionId) {
    setGenerating(false);
    finalizeThinkingIndicator();
    appendMessage("system", "Error: " + payload.message);
  }
}

function handleWarningMessage(payload) {
  console.warn("Server Warning:", payload.message);
  showToast("WARNING", payload.message);
}

function showThinkingIndicator(text) {
  if (document.getElementById("thinking-indicator")) return;

  currentThought = "";
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
    if (!currentThought.trim()) {
      indicator.remove();
      return;
    }
    indicator.id = ""; // Remove ID to allow a new one for next message
    const button = indicator.querySelector(".thinking-button");
    if (button) {
      button.innerHTML = "View Thought Process";
      button.classList.add("finalized");
    }
    currentThought = "";
  }
}

function removeThinkingIndicator() {
  const indicator = document.getElementById("thinking-indicator");
  if (indicator) indicator.remove();
}

function appendMessage(role, text, attachments = [], metrics = null) {
  const msgElement = document.createElement("div");
  msgElement.className = `message ${role}-message`;

  if (attachments && attachments.length > 0) {
    const attachmentsContainer = document.createElement("div");
    attachmentsContainer.className = "message-attachments";
    attachments.forEach((att) => {
      const item = document.createElement("div");
      item.className = "message-attachment-item";
      if (att.mime_type && att.mime_type.startsWith("image/")) {
        const img = document.createElement("img");
        img.src = `/uploads/${att.stored_filename}`;
        img.onclick = () => window.open(img.src, "_blank");
        item.appendChild(img);
      } else {
        const icon = document.createElement("span");
        icon.className = "material-icons";
        icon.textContent = "description";
        const name = document.createElement("span");
        name.textContent = att.filename;
        const link = document.createElement("a");
        link.href = `/uploads/${att.stored_filename}`;
        link.target = "_blank";
        link.appendChild(icon);
        link.appendChild(name);
        item.appendChild(link);
      }
      attachmentsContainer.appendChild(item);
    });
    msgElement.appendChild(attachmentsContainer);
  }

  const textContainer = document.createElement("div");
  textContainer.className = "message-text";

  if (role === "assistant") {
    // Parse Markdown and sanitize
    const cleanHtml = renderMarkdown(text);
    textContainer.innerHTML = cleanHtml;

    // Render LaTeX
    if (typeof renderMathInElement === "function") {
      renderMathInElement(textContainer, {
        delimiters: [
          { left: "\\(", right: "\\)", display: false },
          { left: "\\[", right: "\\]", display: true },
        ],
        throwOnError: false,
      });
    }

    if (metrics) {
      const metricsDiv = document.createElement("div");
      metricsDiv.className = "message-metrics";
      metricsDiv.textContent = `Generated ${metrics.tokens} tokens in ${metrics.time_s.toFixed(2)}s (${metrics.tokens_per_sec.toFixed(1)} tokens/s)`;
      msgElement.appendChild(metricsDiv);
    }
  } else {
    // For user messages, we can just use textContent or simple styling
    textContainer.textContent = text;
  }

  msgElement.appendChild(textContainer);
  messagesDiv.appendChild(msgElement);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
  if (isGenerating) return;

  const text = userInput.value.trim();
  const model = modelSelector.value;
  if (
    (text || pendingAttachments.length > 0) &&
    model &&
    socket &&
    socket.readyState === WebSocket.OPEN &&
    currentSessionId
  ) {
    setGenerating(true);
    appendMessage("user", text, [...pendingAttachments]);
    if (reasoningButton.classList.contains("active")) {
      showThinkingIndicator("Assistant is thinking...");
    }
    socket.send(
      JSON.stringify({
        type: MessageType.MESSAGE,
        session_id: currentSessionId,
        content: text,
        model: model,
        attachments: pendingAttachments,
        enable_reasoning: reasoningButton.classList.contains("active"),
      }),
    );
    userInput.value = "";
    userInput.style.height = "auto";
    clearAttachments();
  }
}

async function handleFileSelect(event) {
  const files = Array.from(event.target.files);
  for (const file of files) {
    await uploadFile(file);
  }
  fileInput.value = ""; // Reset input
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/chats/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    pendingAttachments.push(data);
    renderAttachmentPreview(data, file);
  } catch (error) {
    console.error("Upload failed:", error);
    appendMessage("system", `Upload failed for ${file.name}`);
  }
}

function renderAttachmentPreview(data, file) {
  const item = document.createElement("div");
  item.className = "attachment-item";
  item.dataset.fileId = data.file_id;

  if (data.mime_type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    item.appendChild(img);
  } else {
    const icon = document.createElement("span");
    icon.className = "material-icons file-icon";
    icon.textContent = "description";
    item.appendChild(icon);
  }

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-attachment";
  removeBtn.innerHTML =
    '<span class="material-icons" style="font-size: 14px;">close</span>';
  removeBtn.onclick = () => removeAttachment(data.file_id);
  item.appendChild(removeBtn);

  attachmentPreviews.appendChild(item);
}

function removeAttachment(fileId) {
  pendingAttachments = pendingAttachments.filter((a) => a.file_id !== fileId);
  const item = attachmentPreviews.querySelector(`[data-file-id="${fileId}"]`);
  if (item) item.remove();
}

function clearAttachments() {
  pendingAttachments = [];
  attachmentPreviews.innerHTML = "";
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

userInput.addEventListener("paste", async (e) => {
  const items = e.clipboardData.items;
  let files = [];

  for (let i = 0; i < items.length; i++) {
    if (items[i].kind === "file") {
      const file = items[i].getAsFile();
      if (file) {
        files.push(file);
      }
    }
  }

  if (files.length > 0) {
    e.preventDefault();
    for (const file of files) {
      await uploadFile(file);
    }
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

async function deletePersonalHistory() {
  if (
    !confirm(
      "Are you sure you want to delete your personal history? This will erase all learned memories and cannot be undone.",
    )
  )
    return;

  const response = await fetch("/api/chats/memory", { method: "DELETE" });
  if (response.ok) {
    alert("Personal history deleted successfully.");
  } else {
    alert("Failed to delete personal history.");
  }
}

deleteMemoryButton.addEventListener("click", deletePersonalHistory);

init();
