import { useState } from "react";
import { FiSend } from "react-icons/fi";

function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput("");
  };

  return (
    <div className="input-container">
      <input
        value={input}
        disabled={disabled}
        placeholder="Ask about your order, billing, refund or product..."
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") handleSend();
        }}
      />
      <button type="button" onClick={handleSend} disabled={disabled}>
        <FiSend />
        Send
      </button>
    </div>
  );
}

export default ChatInput;
