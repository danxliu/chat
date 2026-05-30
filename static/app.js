let socket = null;
let currentSessionId = null;
let pingInterval = null;

const chatContainer = document.getElementById('chat-container');
const messagesDiv = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const chatList = document.getElementById('chat-list');
const newChatButton = document.getElementById('new-chat');

const MessageType = {
    MESSAGE: 'message',
    THINKING: 'thinking',
    PING: 'ping',
    PONG: 'pong',
    CANCEL: 'cancel',
    ERROR: 'error'
};

const messageHandlers = {
    [MessageType.MESSAGE]: handleIncomingMessage,
    [MessageType.THINKING]: handleThinking,
    [MessageType.PONG]: handlePong,
    [MessageType.ERROR]: handleErrorMessage
};

async function init() {
    connectWebSocket();
    await loadSessions();
    
    // Create an initial session if none exist
    const response = await fetch('/api/chats');
    const data = await response.json();
    if (data.sessions.length === 0) {
        await createNewSession();
    } else {
        await switchSession(data.sessions[0]);
    }
}

async function createNewSession() {
    const response = await fetch('/api/chats', { method: 'POST' });
    const data = await response.json();
    await loadSessions();
    await switchSession(data.session_id);
    return data.session_id;
}

async function loadSessions() {
    const response = await fetch('/api/chats');
    const data = await response.json();
    chatList.innerHTML = '';
    data.sessions.forEach(sid => {
        const li = document.createElement('li');
        li.className = 'session-item';
        
        const span = document.createElement('span');
        span.textContent = sid;
        span.onclick = () => switchSession(sid);
        li.appendChild(span);

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = '×';
        deleteBtn.className = 'delete-session';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteSession(sid);
        };
        li.appendChild(deleteBtn);

        if (sid === currentSessionId) {
            li.classList.add('active');
        }
        chatList.appendChild(li);
    });
}

async function deleteSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session?')) return;
    
    await fetch(`/api/chats/${sessionId}`, { method: 'DELETE' });
    if (currentSessionId === sessionId) {
        currentSessionId = null;
        messagesDiv.innerHTML = '';
    }
    await loadSessions();
    
    // If we deleted the active session, pick another one or create new
    const response = await fetch('/api/chats');
    const data = await response.json();
    if (data.sessions.length > 0) {
        if (!currentSessionId) await switchSession(data.sessions[0]);
    } else {
        await createNewSession();
    }
}

async function loadHistory(sessionId) {
    const response = await fetch(`/api/chats/${sessionId}/history`);
    const data = await response.json();
    messagesDiv.innerHTML = '';
    data.history.forEach(msg => {
        appendMessage(msg.role === 'user' ? 'You' : 'Assistant', msg.content);
    });
}

async function switchSession(sessionId) {
    currentSessionId = sessionId;
    await loadHistory(sessionId);
    updateActiveSessionInList();
}

function updateActiveSessionInList() {
    const items = chatList.querySelectorAll('li');
    items.forEach(li => {
        const sid = li.querySelector('span').textContent;
        if (sid === currentSessionId) {
            li.classList.add('active');
        } else {
            li.classList.remove('active');
        }
    });
}

function connectWebSocket() {
    if (socket && socket.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('Persistent WebSocket connected');
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
                console.warn('Unknown message type:', data.type);
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };

    socket.onerror = (error) => {
        console.error('WebSocket Error:', error);
    };

    socket.onclose = () => {
        console.log('WebSocket connection closed. Reconnecting in 3s...');
        clearInterval(pingInterval);
        setTimeout(connectWebSocket, 3000);
    };
}

function handleIncomingMessage(payload) {
    // Only append if it's for the current session
    if (payload.session_id === currentSessionId) {
        removeThinkingIndicator();
        appendMessage('Assistant', payload.content);
    }
}

function handleThinking(payload) {
    if (payload.session_id === currentSessionId) {
        showThinkingIndicator(payload.content);
    }
}

function handlePong(payload) {
    // Heartbeat acknowledged
}

function handleErrorMessage(payload) {
    console.error('Server Error:', payload.message);
    if (!payload.session_id || payload.session_id === currentSessionId) {
        removeThinkingIndicator();
        appendMessage('System', 'Error: ' + payload.message);
    }
}

function showThinkingIndicator(text) {
    removeThinkingIndicator();
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'thinking-indicator';
    thinkingDiv.style.fontStyle = 'italic';
    thinkingDiv.style.color = '#888';
    thinkingDiv.textContent = text;
    messagesDiv.appendChild(thinkingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeThinkingIndicator() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) indicator.remove();
}

function appendMessage(sender, text) {
    const msgElement = document.createElement('div');
    msgElement.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesDiv.appendChild(msgElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
    const text = userInput.value.trim();
    if (text && socket && socket.readyState === WebSocket.OPEN && currentSessionId) {
        appendMessage('You', text);
        socket.send(JSON.stringify({
            type: MessageType.MESSAGE,
            session_id: currentSessionId,
            content: text
        }));
        userInput.value = '';
    }
}

sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

newChatButton.addEventListener('click', createNewSession);

init();
