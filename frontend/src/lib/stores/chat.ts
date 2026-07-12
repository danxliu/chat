import { writable, get } from "svelte/store";
import { toast } from "svelte-sonner";

export const MessageType = {
  MESSAGE: "message",
  THINKING: "thinking",
  CONTENT_CHUNK: "content_chunk",
  RICH_BLOCK: "rich_block",
  TITLE_UPDATE: "title_update",
  PING: "ping",
  PONG: "pong",
  CANCEL: "cancel",
  ERROR: "error",
  WARNING: "warning",
} as const;

export type MessageRole = "user" | "assistant" | "system";

export interface Attachment {
  file_id: string;
  filename: string;
  stored_filename: string;
  mime_type: string;
}

export interface Metrics {
  tokens: number;
  time_s: number;
  tokens_per_sec: number;
}

export interface Block {
  index: number;
  type: string;
  content: any;
}

export interface Message {
  role: MessageRole;
  blocks: Block[];
  attachments?: Attachment[];
  metrics?: Metrics;
  thought?: string;
  id?: string;
  isThinking?: boolean;
}

export interface Session {
  session_id: string;
  title: string;
}

// Stores
export const messages = writable<Message[]>([]);
export const sessions = writable<Session[]>([]);
export const currentSessionId = writable<string | null>(null);
export const isGenerating = writable(false);
export const isConnected = writable(false);
export const models = writable<string[]>([]);

const initialModel = typeof window !== "undefined" ? window.localStorage.getItem("selectedModel") || "" : "";
export const selectedModel = writable<string>(initialModel);

if (typeof window !== "undefined") {
  selectedModel.subscribe((val) => {
    if (val) {
      window.localStorage.setItem("selectedModel", val);
    }
  });
}

export const activeModel = selectedModel;
export const enableReasoning = writable(true);

let socket: WebSocket | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;
let pingTimeout: ReturnType<typeof setTimeout> | null = null;

export function connectWebSocket() {
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING)
  )
    return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket connected");
    isConnected.set(true);
    startPing();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleSocketMessage(data);
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
    isConnected.set(false);
  };

  socket.onclose = () => {
    console.log("WebSocket closed. Reconnecting in 3s...");
    isConnected.set(false);
    stopPing();
    setTimeout(connectWebSocket, 3000);
  };
}

function startPing() {
  stopPing();
  pingInterval = setInterval(() => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: MessageType.PING }));
      pingTimeout = setTimeout(() => {
        isConnected.set(false);
      }, 5000);
    }
  }, 30000);
}

function stopPing() {
  if (pingInterval) clearInterval(pingInterval);
  if (pingTimeout) clearTimeout(pingTimeout);
}

function handleSocketMessage(payload: any) {
  const currentSid = get(currentSessionId);

  switch (payload.type) {
    case MessageType.PONG:
      if (pingTimeout) clearTimeout(pingTimeout);
      isConnected.set(true);
      break;

    case MessageType.CONTENT_CHUNK:
      if (payload.session_id === currentSid) {
        messages.update((msgs) => {
          const lastMsg = msgs[msgs.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            const targetBlockIndex = lastMsg.blocks.findIndex(
              (b) => b.index === payload.block_index,
            );

            let newBlocks = [...lastMsg.blocks];
            if (targetBlockIndex !== -1) {
              newBlocks[targetBlockIndex] = {
                ...newBlocks[targetBlockIndex],
                content: newBlocks[targetBlockIndex].content + payload.content,
              };
            } else {
              newBlocks.push({
                index: payload.block_index,
                type: "text",
                content: payload.content,
              });
            }

            return [
              ...msgs.slice(0, -1),
              { ...lastMsg, blocks: newBlocks, isThinking: false },
            ];
          } else {
            return [
              ...msgs,
              {
                role: "assistant",
                blocks: [
                  {
                    index: payload.block_index,
                    type: "text",
                    content: payload.content,
                  },
                ],
                isThinking: false,
              },
            ];
          }
        });
      }
      break;

    case MessageType.RICH_BLOCK:
      if (payload.session_id === currentSid) {
        messages.update((msgs) => {
          const lastMsg = msgs[msgs.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...msgs.slice(0, -1),
              { ...lastMsg, blocks: [...lastMsg.blocks, payload.block] },
            ];
          }
          return msgs;
        });
      }
      break;

    case MessageType.THINKING:
      if (payload.session_id === currentSid) {
        messages.update((msgs) => {
          let lastMsg = msgs[msgs.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            let newThought = lastMsg.thought || "";
            if (payload.data) {
              if (payload.data.type === "thought") {
                newThought += payload.data.content;
              } else if (payload.data.type === "tool_call") {
                newThought += `\n\n**Tool Call:** ${payload.data.tool}\n\n`;
              }
            }
            return [
              ...msgs.slice(0, -1),
              { ...lastMsg, thought: newThought, isThinking: true },
            ];
          } else {
            return [
              ...msgs,
              {
                role: "assistant",
                blocks: [],
                thought: payload.data?.content || "",
                isThinking: true,
              },
            ];
          }
        });
      }
      break;

    case MessageType.MESSAGE:
      if (payload.session_id === currentSid) {
        isGenerating.set(false);
        messages.update((msgs) => {
          const lastMsg = msgs[msgs.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            return [
              ...msgs.slice(0, -1),
              { ...lastMsg, metrics: payload.metrics, isThinking: false },
            ];
          }
          return [
            ...msgs,
            {
              role: "assistant",
              blocks: [
                {
                  index: 0,
                  type: "text",
                  content: payload.content,
                },
              ],
              metrics: payload.metrics,
              isThinking: false,
            },
          ];
        });
        refreshSessions();
      }
      break;

    case MessageType.TITLE_UPDATE:
      refreshSessions();
      break;

    case MessageType.ERROR:
      console.error("Server error:", payload.message);
      isGenerating.set(false);
      toast.error(payload.message);
      break;

    case MessageType.WARNING:
      console.warn("Server warning:", payload.message);
      toast.warning(payload.message);
      break;
  }
}

export async function refreshSessions() {
  const res = await fetch("/api/chats");
  if (!res.ok) throw new Error(`Failed to refresh sessions: ${res.statusText}`);
  const data = await res.json();
  sessions.set(data.sessions);
}

export async function loadHistory(sessionId: string) {
  const res = await fetch(`/api/chats/${sessionId}/history`);
  if (!res.ok) throw new Error(`Failed to load history: ${res.statusText}`);
  const data = await res.json();

  const history: Message[] = [];
  data.history.forEach((msg: any) => {
    history.push({
      role: msg.role,
      blocks: msg.blocks,
      thought: msg.thought,
      metrics: msg.metrics,
      attachments: msg.attachments,
    });
  });
  messages.set(history);
}

export async function switchSession(sessionId: string) {
  currentSessionId.set(sessionId);
  await loadHistory(sessionId);
}

export async function createNewSession() {
  const res = await fetch("/api/chats", { method: "POST" });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  const data = await res.json();
  await refreshSessions();
  await switchSession(data.session_id);
  return data.session_id;
}

export async function deleteSession(sessionId: string) {
  const res = await fetch(`/api/chats/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete session: ${res.statusText}`);
  const current = get(currentSessionId);
  if (current === sessionId) {
    currentSessionId.set(null);
    messages.set([]);
  }
  await refreshSessions();

  const s = get(sessions);
  if (s.length > 0) {
    await switchSession(s[0].session_id);
  } else {
    await createNewSession();
  }
}

export async function loadModels() {
  const res = await fetch("/api/chats/models");
  if (!res.ok) throw new Error(`Failed to load models: ${res.statusText}`);
  const data = await res.json();
  models.set(data.models);
  
  const currentModel = get(selectedModel);
  if (data.models.length > 0) {
    if (!currentModel || !data.models.includes(currentModel)) {
      selectedModel.set(data.models[0]);
    }
  }
}

export function sendMessage(content: string, attachments: Attachment[] = []) {
  const sid = get(currentSessionId);
  const model = get(activeModel);
  const reasoning = get(enableReasoning);

  if (!sid || !socket || socket.readyState !== WebSocket.OPEN) return;

  isGenerating.set(true);
  messages.update((msgs) => [
    ...msgs,
    {
      role: "user",
      blocks: [{ index: 0, type: "text", content }],
      attachments,
    },
  ]);

  socket.send(
    JSON.stringify({
      type: MessageType.MESSAGE,
      session_id: sid,
      content,
      model,
      attachments,
      enable_reasoning: reasoning,
    }),
  );
}

export function cancelGeneration() {
  const sid = get(currentSessionId);
  if (!sid || !socket || socket.readyState !== WebSocket.OPEN) return;

  socket.send(
    JSON.stringify({
      type: MessageType.CANCEL,
      session_id: sid,
    }),
  );
  isGenerating.set(false);
}
