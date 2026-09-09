import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState("checking");

  useEffect(() => {
    async function checkHealth() {
      try {
        const response = await fetch("http://127.0.0.1:8000/health");

        if (!response.ok) {
          setSystemStatus("offline");
          return;
        }

        const data = await response.json();

        if (data.status === "healthy" && data.mcp === "online") {
          setSystemStatus("online");
        } else {
          setSystemStatus("offline");
        }
      } catch (error) {
        console.error("Health check failed:", error);
        setSystemStatus("offline");
      }
    }

    checkHealth();

    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage || isLoading) {
      return;
    }

    const userMessage = {
      role: "user",
      content: trimmedMessage,
    };

    const assistantMessage = {
      role: "assistant",
      content: "",
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
      assistantMessage,
    ]);

    setMessage("");
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmedMessage,
        }),
      });

      if (!response.ok) {
        throw new Error("Sunucudan cevap alınamadı.");
      }

      if (!response.body) {
        throw new Error("Streaming desteklenmiyor.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let receivedText = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });

        receivedText += chunk;

        setMessages((currentMessages) => {
          const updatedMessages = [...currentMessages];
          const lastIndex = updatedMessages.length - 1;
          const lastMessage = updatedMessages[lastIndex];

          updatedMessages[lastIndex] = {
            ...lastMessage,
            content: lastMessage.content + chunk,
          };

          return updatedMessages;
        });
      }

      if (!receivedText.trim()) {
        setMessages((currentMessages) => {
          const updatedMessages = [...currentMessages];
          const lastIndex = updatedMessages.length - 1;

          updatedMessages[lastIndex] = {
            role: "assistant",
            content:
              "Bu soru için bir yanıt oluşturulamadı. Lütfen tekrar deneyin.",
          };

          return updatedMessages;
        });
      }
    } catch (error) {
      console.error("Chat request failed:", error);

      setMessages((currentMessages) => {
        const updatedMessages = [...currentMessages];
        const lastIndex = updatedMessages.length - 1;

        updatedMessages[lastIndex] = {
          role: "assistant",
          content:
            "Yanıt alınamadı. Lütfen bağlantınızı kontrol edip tekrar deneyin.",
        };

        return updatedMessages;
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Mevzuat Chatbot</h1>
          <p>Türk mevzuatı için yapay zekâ destekli asistan</p>
        </div>

        <div className={`status-badge ${systemStatus}`}>
          <span className="status-dot" />

          {systemStatus === "checking"
            ? "Kontrol ediliyor"
            : systemStatus === "online"
              ? "Sistem hazır"
              : "Bağlantı sorunu"}
        </div>
      </header>

      <main className="chat-area">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2>Mevzuat hakkında bir soru sorun</h2>

            <p>
              Kanunlar, maddeler ve hukuki kavramlar hakkında soru
              sorabilirsiniz.
            </p>

            <div className="suggestions">
              <button
                type="button"
                onClick={() =>
                  setMessage(
                    "6698 sayılı Kişisel Verilerin Korunması Kanununda açık rıza nedir?",
                  )
                }
              >
                KVKK&apos;da açık rıza nedir?
              </button>

              <button
                type="button"
                onClick={() =>
                  setMessage(
                    "4857 sayılı İş Kanununda haftalık normal çalışma süresi kaç saattir?",
                  )
                }
              >
                İş Kanununda çalışma süresi
              </button>
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((chatMessage, index) => (
              <div key={index} className={`message-row ${chatMessage.role}`}>
                <div className="message-bubble">
                  {chatMessage.content ? (
                    chatMessage.role === "assistant" ? (
                      <ReactMarkdown>{chatMessage.content}</ReactMarkdown>
                    ) : (
                      chatMessage.content
                    )
                  ) : isLoading && index === messages.length - 1 ? (
                    <div className="thinking">
                      <span />
                      <span />
                      <span />
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <div className="composer-wrapper">
        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event);
              }
            }}
            placeholder="Mevzuat hakkında bir soru sorun..."
            rows={1}
            disabled={isLoading}
          />

          <button
            className="send-button"
            type="submit"
            disabled={!message.trim() || isLoading}
            aria-label="Mesaj gönder"
          >
            ↑
          </button>
        </form>

        <p className="disclaimer">Technical case study</p>
      </div>
    </div>
  );
}

export default App;
