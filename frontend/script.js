// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let currentAbortController = null;  // AbortController for the active fetch
let lastQuery = '';                  // Last submitted query, used for "edit" option after interrupt

// DOM elements
let chatMessages, chatInput, sendButton, pauseButton, totalCourses, courseTitles, newChatButton;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    pauseButton = document.getElementById('pauseButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Pause/interrupt button
    pauseButton.addEventListener('click', interruptGeneration);

    // New chat button
    newChatButton.addEventListener('click', handleNewChatClick);

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}

// Toggle generating state: locks/unlocks input and swaps send ↔ pause button
function setGeneratingState(isGenerating) {
    chatInput.disabled = isGenerating;
    sendButton.disabled = isGenerating;
    sendButton.style.display = isGenerating ? 'none' : '';
    pauseButton.style.display = isGenerating ? '' : 'none';
}

// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    lastQuery = query;

    // Remove any leftover interrupt options bar
    const existing = document.getElementById('interruptOptions');
    if (existing) existing.remove();

    // Lock input, show pause button
    chatInput.value = '';
    setGeneratingState(true);

    // Add user message
    addMessage(query, 'user');

    // Add loading message
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Create abort controller for this request
    currentAbortController = new AbortController();

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            }),
            signal: currentAbortController.signal
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        loadingMessage.remove();

        if (error.name === 'AbortError') {
            // User interrupted — show options rather than an error message
            showInterruptOptions();
        } else {
            addMessage(`Error: ${error.message}`, 'assistant');
        }
    } finally {
        currentAbortController = null;
        setGeneratingState(false);
        chatInput.focus();
    }
}

// Called when the user clicks the pause button
function interruptGeneration() {
    // Tell the backend to mark this session as cancelled (best-effort)
    if (currentSessionId) {
        fetch(`${API_URL}/cancel/${currentSessionId}`, { method: 'POST' }).catch(() => {});
    }
    // Abort the fetch — triggers AbortError in sendMessage catch block
    if (currentAbortController) {
        currentAbortController.abort();
    }
}

// Render the post-interrupt options bar below the chat messages
function showInterruptOptions() {
    const bar = document.createElement('div');
    bar.className = 'interrupt-options';
    bar.id = 'interruptOptions';

    bar.innerHTML = `
        <span>Generation stopped.</span>
        <button class="interrupt-option-btn" id="optionNew">New question</button>
        <button class="interrupt-option-btn" id="optionEdit">Edit previous</button>
    `;

    chatMessages.appendChild(bar);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    bar.querySelector('#optionNew').addEventListener('click', () => {
        bar.remove();
        chatInput.value = '';
        chatInput.focus();
    });

    bar.querySelector('#optionEdit').addEventListener('click', () => {
        bar.remove();
        chatInput.value = lastQuery;
        chatInput.focus();
    });
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sources.map(s => `<span class="source-chip">${s}</span>`).join('')}</div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

async function handleNewChatClick() {
    if (currentSessionId) {
        try {
            await fetch(`${API_URL}/session/${currentSessionId}`, { method: 'DELETE' });
        } catch (error) {
            console.warn('Failed to delete session on backend:', error);
        }
    }
    createNewSession();
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
