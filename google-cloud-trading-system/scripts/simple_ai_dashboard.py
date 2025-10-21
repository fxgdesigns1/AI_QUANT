from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Simple AI Test</title>
    <style>
        .ai-panel {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 300px;
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 10px;
        }
        
        .ai-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 20px;
            cursor: pointer;
        }
        
        .messages {
            height: 200px;
            overflow-y: auto;
            border: 1px solid #eee;
            padding: 10px;
            margin-bottom: 10px;
        }
        
        .message {
            margin-bottom: 10px;
            padding: 5px;
        }
        
        .user { background: #e3f2fd; }
        .ai { background: #f5f5f5; }
    </style>
</head>
<body>
    <div class="ai-panel" id="aiPanel">
        <h3>AI Assistant</h3>
        <div class="messages" id="messages"></div>
        <input type="text" id="messageInput" style="width: 80%">
        <button onclick="sendMessage()">Send</button>
    </div>
    
    <button class="ai-button" onclick="togglePanel()">🤖</button>
    
    <script>
        // Simple global state
        let panelVisible = true;
        
        // Simple toggle function
        function togglePanel() {
            console.log('Toggle clicked');
            const panel = document.getElementById('aiPanel');
            panelVisible = !panelVisible;
            panel.style.display = panelVisible ? 'block' : 'none';
        }
        
        // Simple message sender
        function sendMessage() {
            console.log('Send clicked');
            const input = document.getElementById('messageInput');
            const message = input.value;
            
            if (!message) return;
            
            // Add user message
            addMessage('user', message);
            
            // Clear input
            input.value = '';
            
            // Send to backend
            fetch('/ai/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            })
            .then(response => response.json())
            .then(data => {
                addMessage('ai', data.reply);
            })
            .catch(error => {
                console.error('Error:', error);
                addMessage('ai', 'Sorry, there was an error.');
            });
        }
        
        // Simple message display
        function addMessage(type, text) {
            console.log('Adding message:', type, text);
            const messages = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.textContent = text;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Handle Enter key
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Log when loaded
        console.log('AI Assistant loaded');
    </script>
</body>
</html>
    ''')

@app.route('/ai/message', methods=['POST'])
def ai_message():
    data = request.json
    message = data.get('message', '').lower()
    
    # Simple responses
    if 'market' in message:
        reply = "Current market conditions are stable. EUR/USD at 1.0850."
    elif 'position' in message:
        reply = "You have 3 open positions with +1.2% total P/L."
    elif 'status' in message:
        reply = "All systems operational and running normally."
    else:
        reply = "I understand you're asking about: " + message
    
    return jsonify({'reply': reply})

if __name__ == '__main__':
    print("🤖 Starting Simple AI Dashboard Test...")
    print("📊 Open http://localhost:5005 in your browser")
    app.run(host='0.0.0.0', port=5005, debug=True)

