import { useState } from 'react';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault(); // Stop page refresh
    if (!question.trim()) return; // Don't send empty messages

    // 1. Add user's message
    setMessages((currentMessages) => [
      ...currentMessages,
      { sender: 'You', text: question }
    ]);

    const userQuestion = question; // Save current question
    setQuestion(''); // Clear input box

    try {
      // 2. Send to FastAPI Backend
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQuestion })
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();

      // 3. Add AI's response
      setMessages((currentMessages) => [
        ...currentMessages,
        { sender: 'AI', text: data.answer || data.response || "Received your message!" }
      ]);

    } catch (error) {
      setMessages((currentMessages) => [
        ...currentMessages,
        { sender: 'AI', text: "Error connecting to backend. Please check if the server is running on port 8000." }
      ]);
    }
  };

  // THIS RETURN STATEMENT IS WHAT DRAWS THE UI. DO NOT DELETE IT.
  return (
    <div style={styles.container}>
      <h1 style={styles.heading}>AI Assistant</h1>
      
      <div style={styles.chatBox}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <p>Hello! Upload your study materials and ask me anything about your subjects.</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div 
            key={index} 
            style={msg.sender === 'You' ? styles.userMessage : styles.aiMessage}
          >
            <strong>{msg.sender}:</strong> {msg.text}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} style={styles.form}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your study material..."
          style={styles.input}
        />
        <button type="submit" style={styles.button}>
          Send
        </button>
      </form>
    </div>
  );
}

// Basic styling to match your dark dashboard theme
const styles = {
  container: {
    maxWidth: '800px',
    margin: '40px auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif',
    color: '#ffffff',
  },
  heading: {
    fontSize: '28px',
    marginBottom: '20px',
    textAlign: 'center',
  },
  chatBox: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    padding: '20px',
    minHeight: '400px',
    maxHeight: '500px',
    overflowY: 'auto',
    marginBottom: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  emptyState: {
    textAlign: 'center',
    color: '#94a3b8',
    marginTop: '150px',
  },
  userMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#3b82f6',
    padding: '10px 15px',
    borderRadius: '10px',
    maxWidth: '70%',
  },
  aiMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#334155',
    padding: '10px 15px',
    borderRadius: '10px',
    maxWidth: '70%',
  },
  form: {
    display: 'flex',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '15px',
    borderRadius: '8px',
    border: '1px solid #475569',
    backgroundColor: '#0f172a',
    color: 'white',
    fontSize: '16px',
  },
  button: {
    padding: '15px 30px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#3b82f6',
    color: 'white',
    fontSize: '16px',
    cursor: 'pointer',
    fontWeight: 'bold',
  }
};

export default Chat;