/**
 * Chat functionality for Geodaten Assistant
 * Maintains conversation history for context-aware follow-up questions
 */

// Conversation history for context
let conversationHistory = [];

// Predetermined prompt suggestions
const promptSuggestions = [
    {
        icon: "🚂",
        text: "Wo liegt der Bahnhof Luzern? Auf wie viel Höhenmetern über dem Meer?",
        category: "Location"
    },
    {
        icon: "🐝",
        text: "Zeig mir Bienenstandorte in Luzern.",
        category: "Location"
    },
    {
        icon: "🛑",
        text: "Zeige mir Gefahrengebiete auf der Karte",
        category: "Visualisierung"
    }
];

// Initialize prompt suggestions on page load
function initializePromptSuggestions() {
    const suggestionsContainer = document.getElementById('prompt-suggestions');
    if (!suggestionsContainer) return;

    // Clear existing suggestions
    suggestionsContainer.innerHTML = '';

    // Add each suggestion
    promptSuggestions.forEach(suggestion => {
        const suggestionDiv = document.createElement('div');
        suggestionDiv.className = 'prompt-suggestion';
        suggestionDiv.innerHTML = `
            <span class="suggestion-icon">${suggestion.icon}</span>
            <span class="suggestion-text">${suggestion.text}</span>
        `;

        // Add click handler to use the suggestion
        suggestionDiv.addEventListener('click', function() {
            useSuggestion(suggestion.text);
        });

        suggestionsContainer.appendChild(suggestionDiv);
    });
}

// Use a suggestion as the user's message
function useSuggestion(text) {
    const input = document.getElementById('chat-input');
    input.value = text;
    sendMessage();
}

// Hide suggestions after first message
function hideSuggestions() {
    const suggestionsContainer = document.getElementById('prompt-suggestions');
    if (suggestionsContainer) {
        suggestionsContainer.style.display = 'none';
    }
}

// Show suggestions when chat is cleared
function showSuggestions() {
    const suggestionsContainer = document.getElementById('prompt-suggestions');
    if (suggestionsContainer) {
        suggestionsContainer.style.display = 'flex';
    }
}

// Toggle chat visibility
document.getElementById('toggle-chat').addEventListener('click', function() {
    const chatSection = document.getElementById('chat-section');
    chatSection.classList.toggle('hidden');
});

// Clear conversation history
document.getElementById('clear-chat').addEventListener('click', function() {
    conversationHistory = [];
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="message assistant">
            <div class="message-content">
                Hallo! Ich bin Ihr Geodaten-Assistent für den Kanton Luzern. Wie kann ich Ihnen helfen?
            </div>
        </div>
    `;

    // Clear map layers and markers
    if (typeof window.clearDynamicWmsLayers === 'function') {
        window.clearDynamicWmsLayers();
    }
    if (typeof window.clearMarkers === 'function') {
        window.clearMarkers();
    }

    console.log('Konversation zurückgesetzt');
});

// Send message function with loading indicator
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // Disable input while processing
    input.disabled = true;
    document.getElementById('send-button').disabled = true;

    // Hide suggestions after first user message
    hideSuggestions();

    // Add user message to chat
    addMessage(message, 'user');

    // Clear input
    input.value = '';

    // Add user message to history
    conversationHistory.push({
        role: 'user',
        content: message
    });

    // Add loading indicator
    const messagesContainer = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant loading-message';
    loadingDiv.id = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="loading-spinner">
                <div class="spinner"></div>
                <span>Suche nach Datensätzen...</span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        // Send request
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_history: conversationHistory
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();

        // Remove loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }

        // Add assistant response to history
        conversationHistory.push({
            role: 'assistant',
            content: data.response
        });

        // Handle location data if present
        if (data.location_data) {
            console.log('Location data found:', data.location_data);

            const loc = data.location_data;

            // Clear existing markers
            if (typeof window.clearMarkers === 'function') {
                window.clearMarkers();
            }

            // Zoom to location with marker
            if (typeof window.zoomToLocation === 'function') {
                window.zoomToLocation(loc.x, loc.y, loc.zoom || 16, true);

                // Add notification to response
                const locationNote = `\n\n📍 *Karte zentriert auf: ${loc.name || 'Standort'}*`;
                data.response += locationNote;
            }
        }

        // Handle WMS layers if present
        if (data.wms_urls && data.wms_urls.length > 0) {
            console.log('WMS URLs found:', data.wms_urls);

            // Clear existing dynamic layers before adding new ones
            if (typeof window.clearDynamicWmsLayers === 'function') {
                window.clearDynamicWmsLayers();
            }

            // Add each WMS layer to the map
            data.wms_urls.forEach((url, index) => {
                if (typeof window.addWmsLayer === 'function') {
                    // Extract a layer name from the URL if possible
                    const layerName = extractLayerNameFromUrl(url) || `Datensatz ${index + 1}`;
                    window.addWmsLayer(url, layerName);
                }
            });

            // Add a note to the response about the map layers
            if (data.wms_urls.length > 0) {
                const layerNote = `\n\n📍 *${data.wms_urls.length} WMS Layer wurden auf der Karte angezeigt.*`;
                data.response += layerNote;
            }
        }

        // Add assistant response to chat
        addMessage(data.response, 'assistant');

    } catch (error) {
        console.error('Error:', error);

        // Remove loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }

        addMessage('Entschuldigung, es gab einen Fehler bei der Verarbeitung Ihrer Anfrage.', 'assistant');
    } finally {
        // Re-enable input
        input.disabled = false;
        document.getElementById('send-button').disabled = false;
        input.focus();
    }
}

// Add message to chat display
function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Render markdown for assistant messages, plain text for user messages
    if (sender === 'assistant' && typeof marked !== 'undefined') {
        contentDiv.innerHTML = marked.parse(text);
    } else {
        contentDiv.textContent = text;
    }

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Allow Enter key to send message
document.getElementById('chat-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Helper function to extract layer name from WMS URL
function extractLayerNameFromUrl(url) {
    try {
        // Try to extract service name from URL path
        const urlParts = url.split('/');
        for (let i = 0; i < urlParts.length; i++) {
            if (urlParts[i] === 'managed' && i + 1 < urlParts.length) {
                // Extract the service identifier (e.g., "EWNUTZXX_COL_V3_MP")
                return urlParts[i + 1].replace(/_/g, ' ');
            }
        }

        // Fallback: use last meaningful part of path
        const pathParts = url.split('/').filter(p => p && p !== 'WMSServer' && p !== 'MapServer');
        if (pathParts.length > 0) {
            return pathParts[pathParts.length - 1].replace(/_/g, ' ').substring(0, 30);
        }
    } catch (e) {
        console.error('Error extracting layer name:', e);
    }
    return null;
}

// Initialize suggestions on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        initializePromptSuggestions();
    });
} else {
    // DOM already loaded, initialize immediately
    initializePromptSuggestions();
}

console.log('Chat functionality loaded');
