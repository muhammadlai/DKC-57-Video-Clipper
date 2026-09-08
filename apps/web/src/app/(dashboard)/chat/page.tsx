"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, MessageSquare, Plus, Send, Trash2, User } from "lucide-react";

import type { ChatMessage, ChatResponse, Conversation } from "@aitzaz/types";
import { formatDateTime } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";

const SUGGESTIONS = [
  "Hello Aitzaz",
  "Calculate 125 × 48",
  "What time is it?",
  "Remember that I prefer concise answers",
  "Remind me to review the report tomorrow",
  "Send an email to John (approval demo)",
];

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const toolCalls = message.meta?.tool_calls ?? [];

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl",
          isUser ? "bg-surface2 text-muted" : "bg-gradient-to-br from-accent-strong to-ok text-white",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </span>
      <div className={cn("max-w-[85%] min-w-0", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-accent-strong text-white"
              : "rounded-tl-sm border border-line bg-surface text-ink chat-content",
          )}
        >
          {message.content}
        </div>

        {toolCalls.length > 0 ? (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {toolCalls.map((call, index) => (
              <span
                key={index}
                title={call.error ?? JSON.stringify(call.result ?? "")}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                  call.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger",
                )}
              >
                {call.ok ? "🧰" : "⚠️"} {call.slug} · {call.ok ? "ok" : "failed"} · {call.duration_ms}ms
              </span>
            ))}
          </div>
        ) : null}

        <p className={cn("mt-1 text-[10px] text-muted", isUser && "text-right")}>
          {formatDateTime(message.created_at)}
          {!isUser && message.meta?.demo_mode ? " · Demo AI" : ""}
        </p>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full" />}>
      <ChatWindow />
    </Suspense>
  );
}

function ChatWindow() {
  const searchParams = useSearchParams();
  const initialConversation = searchParams.get("conversation");
  const { toast } = useToast();

  const conversationsState = useApiData<Conversation[]>("/chat/conversations");
  const [activeConversation, setActiveConversation] = useState<string | null>(initialConversation);
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [demoMode, setDemoMode] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadMessages = useCallback(async (conversationId: string) => {
    setMessages(null);
    setMessagesError(null);
    try {
      const history = await api<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`);
      setMessages(history);
    } catch (error) {
      setMessagesError(error instanceof ApiError ? error.message : "Failed to load messages.");
    }
  }, []);

  useEffect(() => {
    if (activeConversation) void loadMessages(activeConversation);
    else setMessages([]);
  }, [activeConversation, loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    setInput("");
    setSending(true);

    // optimistic user message
    const optimistic: ChatMessage = {
      id: `tmp-${Date.now()}`,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...(current ?? []), optimistic]);

    try {
      const response = await api<ChatResponse>("/chat", {
        method: "POST",
        body: { message, conversation_id: activeConversation },
      });
      setDemoMode(response.demo_mode);
      setActiveConversation(String(response.conversation_id));
      setMessages((current) => [
        ...(current ?? []).filter((m) => m.id !== optimistic.id),
        response.user_message,
        response.assistant_message,
      ]);
      conversationsState.refresh();
    } catch (error) {
      setMessages((current) => (current ?? []).filter((m) => m.id !== optimistic.id));
      toast({
        title: "Message failed",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSending(false);
    }
  }

  async function clearConversation() {
    if (!activeConversation) return;
    if (!window.confirm("Clear this conversation permanently?")) return;
    try {
      await api(`/chat/conversations/${activeConversation}`, { method: "DELETE" });
      setActiveConversation(null);
      setMessages([]);
      conversationsState.refresh();
      toast({ title: "Conversation cleared", variant: "success" });
    } catch (error) {
      toast({
        title: "Could not clear conversation",
        description: error instanceof ApiError ? error.message : undefined,
        variant: "error",
      });
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">AI Chat</h1>
          <p className="mt-0.5 text-sm text-muted">
            Chat with your Personal Assistant.
            {demoMode !== false
              ? " Running as Demo AI — a rule-based mock, not a real LLM (Phase 2)."
              : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {demoMode !== false ? (
            <Badge variant="warn" dot>
              Demo AI
            </Badge>
          ) : null}
          <Button variant="secondary" size="sm" onClick={() => { setActiveConversation(null); setMessages([]); }}>
            <Plus className="h-4 w-4" /> New chat
          </Button>
          <Button variant="destructive" size="sm" onClick={clearConversation} disabled={!activeConversation}>
            <Trash2 className="h-4 w-4" /> Clear
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
        {/* Conversations */}
        <aside className="card-shadow hidden max-h-[70vh] overflow-y-auto rounded-2xl border border-line bg-surface/70 p-2 lg:block">
          <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Conversations
          </p>
          {conversationsState.loading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : !conversationsState.data?.length ? (
            <p className="px-3 py-3 text-xs text-muted">No conversations yet.</p>
          ) : (
            <ul className="space-y-0.5">
              {conversationsState.data.map((conversation) => (
                <li key={conversation.id}>
                  <button
                    type="button"
                    onClick={() => setActiveConversation(String(conversation.id))}
                    className={cn(
                      "w-full rounded-lg px-3 py-2 text-left text-sm transition",
                      activeConversation === String(conversation.id)
                        ? "bg-accent/10 text-accent"
                        : "text-muted hover:bg-surface2 hover:text-ink",
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
                      <span className="shrink-0 text-[10px]">{conversation.message_count}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* Chat window */}
        <section className="card-shadow flex min-h-[60vh] flex-col rounded-2xl border border-line bg-surface/70">
          <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
            {messagesError ? (
              <ErrorState
                message={messagesError}
                onRetry={() => activeConversation && loadMessages(activeConversation)}
              />
            ) : messages === null ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-2/3" />
                ))}
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 py-10 text-center">
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-strong to-ok text-white">
                  <Bot className="h-7 w-7" />
                </span>
                <div>
                  <p className="text-sm font-medium text-ink">Say hello to Aitzaz AI</p>
                  <p className="mx-auto mt-1 max-w-sm text-xs text-muted">
                    Demo AI understands a few patterns for now: math, time, tasks, memories and
                    approval requests. Try a suggestion below.
                  </p>
                </div>
                <div className="flex max-w-lg flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => void send(suggestion)}
                      className="rounded-full border border-line bg-surface2/40 px-3 py-1.5 text-xs text-muted transition hover:border-accent/40 hover:text-ink"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}

            {sending ? (
              <div className="flex gap-3">
                <span className="mt-1 flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-accent-strong to-ok text-white">
                  <Bot className="h-4 w-4" />
                </span>
                <div className="rounded-2xl rounded-tl-sm border border-line bg-surface px-4 py-3">
                  <span className="flex gap-1">
                    <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted" />
                    <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted [animation-delay:200ms]" />
                    <span className="h-2 w-2 animate-pulse-soft rounded-full bg-muted [animation-delay:400ms]" />
                  </span>
                </div>
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          {/* Composer */}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void send(input);
            }}
            className="border-t border-line p-3 sm:p-4"
          >
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void send(input);
                  }
                }}
                rows={1}
                placeholder="Tell Aitzaz what you need… (Enter to send, Shift+Enter for a new line)"
                className="max-h-40 min-h-[44px] flex-1 resize-y rounded-xl border border-line bg-surface2/50 px-4 py-2.5 text-sm text-ink placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/50"
                aria-label="Message"
              />
              <Button
                type="submit"
                size="lg"
                loading={sending}
                disabled={!input.trim()}
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
