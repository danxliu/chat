const chatContainer = document.getElementById('chat-container');
const messagesDiv = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
const socket = new WebSocket(wsUrl);

socket.onopen = () => {
    console.log('Connected to WebSocket');
};

socket.onmessage = (event) => {
    const data = event.data;
    appendMessage('Assistant', data);
};

socket.onerror = (error) => {
    console.error('WebSocket Error:', error);
};

socket.onclose = () => {
    console.log('WebSocket connection closed');
};

function appendMessage(sender, text) {
    const msgElement = document.createElement('div');
    msgElement.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messagesDiv.appendChild(msgElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
    const text = userInput.value.trim();
    if (text && socket.readyState === WebSocket.OPEN) {
        appendMessage('You', text);
        socket.send(text);
        userInput.value = '';
    }
}

sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
