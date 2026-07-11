import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Send, User, Bot, Loader2 } from 'lucide-react';

const InterviewUI = () => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => scrollToBottom(), [messages]);

  // Initialize WebSocket
  useEffect(() => {
    // Replace with your actual FastAPI server URL
    ws.current = new WebSocket("ws://localhost:8000/ws/interview?session_id=ui_test");

    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "assistant") {
        setMessages((prev) => [...prev, { role: "assistant", text: data.text }]);
        
        // Play the base64 audio if it exists
        if (data.audio) {
          playBase64Audio(data.audio);
        }
      } else if (data.type === "user_transcript") {
        setMessages((prev) => [...prev, { role: "user", text: data.text }]);
      } else if (data.type === "error") {
        setMessages((prev) => [...prev, { role: "system", text: `Error: ${data.text}` }]);
      }
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  // Handle Base64 Audio Playback
  const playBase64Audio = (base64String) => {
    setIsAiSpeaking(true);
    const audio = new Audio(`data:audio/mp3;base64,${base64String}`);
    audio.onended = () => setIsAiSpeaking(false);
    audio.play().catch(e => console.error("Error playing audio:", e));
  };

  // Send Text Message
  const sendText = (e) => {
    e.preventDefault();
    if (!inputText.trim() || !isConnected) return;

    ws.current.send(JSON.stringify({
      type: "text",
      text: inputText
    }));
    setInputText("");
  };

  // Convert Float32 PCM samples to a WAV Blob
  const encodeWAV = (samples, sampleRate) => {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample

    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([buffer], { type: 'audio/wav' });
  };

  // Handle Microphone Recording using AudioContext for WAV output
  const audioContextRef = useRef(null);
  const scriptProcessorRef = useRef(null);
  const recordedSamplesRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      recordedSamplesRef.current = [];

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0);
        recordedSamplesRef.current.push(new Float32Array(channelData));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      alert("Please allow microphone access to use voice features.");
    }
  };

  const stopRecording = () => {
    if (!isRecording) return;
    setIsRecording(false);

    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }

    const sampleRate = audioContextRef.current?.sampleRate || 44100;

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Merge all recorded chunks into one Float32Array
    const chunks = recordedSamplesRef.current;
    const totalLength = chunks.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    const wavBlob = encodeWAV(merged, sampleRate);

    const reader = new FileReader();
    reader.readAsDataURL(wavBlob);
    reader.onloadend = () => {
      const base64data = reader.result.split(',')[1];
      if (ws.current && isConnected) {
        ws.current.send(JSON.stringify({
          type: "audio",
          data: base64data
        }));
      }
    };
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans">
      {/* Header */}
      <header className="bg-slate-900 text-white p-4 shadow-md flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Technical Interviewer</h1>
          <div className="flex items-center gap-2 mt-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-500'}`}></div>
            <span className="text-xs text-slate-300">
              {isConnected ? "Connected to Engine" : "Connecting..."}
            </span>
          </div>
        </div>
        {isAiSpeaking && (
          <div className="flex items-center gap-2 text-green-400 text-sm font-medium animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin" /> Interviewer is speaking...
          </div>
        )}
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex gap-4 max-w-[80%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              {/* Avatar */}
              <div className={`w-10 h-10 shrink-0 flex items-center justify-center rounded-full shadow-sm 
                ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-slate-800 text-white"}`}>
                {msg.role === "user" ? <User size={20} /> : <Bot size={20} />}
              </div>
              
              {/* Bubble */}
              <div className={`p-4 rounded-2xl shadow-sm leading-relaxed
                ${msg.role === "user" 
                  ? "bg-blue-600 text-white rounded-tr-none" 
                  : msg.role === "system" 
                    ? "bg-red-100 text-red-800"
                    : "bg-white text-slate-800 border border-slate-200 rounded-tl-none"}`}>
                {msg.text}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-slate-200 p-4 shrink-0">
        <form onSubmit={sendText} className="max-w-4xl mx-auto flex gap-4 items-center">
          
          {/* Voice Button */}
          <button
            type="button"
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={!isConnected}
            className={`p-4 rounded-full transition-all flex items-center justify-center shadow-sm
              ${isRecording 
                ? "bg-red-500 hover:bg-red-600 text-white animate-pulse scale-110" 
                : "bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200"} 
              disabled:opacity-50 disabled:cursor-not-allowed`}
            title="Hold to speak"
          >
            {isRecording ? <Square size={24} fill="currentColor" /> : <Mic size={24} />}
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={!isConnected}
            placeholder={isRecording ? "Listening..." : "Type your answer or hold the mic..."}
            className="flex-1 p-4 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-50"
          />
          
          {/* Send Button */}
          <button
            type="submit"
            disabled={!inputText.trim() || !isConnected}
            className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            <Send size={24} />
          </button>
        </form>
        <div className="text-center mt-2 text-xs text-slate-400">
          Hold the microphone button to speak, or type your response.
        </div>
      </footer>
    </div>
  );
};

export default InterviewUI;