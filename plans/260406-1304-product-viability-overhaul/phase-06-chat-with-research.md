# Phase 06: Chat with Research

## Context Links
- [Brainstorm -- Chat](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#chat-with-your-research-phase-1--high-priority)
- Current ChatSheet: `frontend/components/job-detail-v2/chat-sheet.tsx` (170 lines)
- Iterate modes: deep_dive, expand_sources, deeper, different_angle, custom, inline_edit

## Overview
- **Priority:** P2 (Phase 1 -- Product Feel)
- **Status:** pending
- **Effort:** 5-7 days
- **Depends on:** Phase 02 (hero doc -- needs Doc 0/2 displayed)
- **Description:** Add conversational Q&A over completed research. User asks questions like "What did Source 3 say about X?" or "Find contradictions between these experts." Uses Gemini Flash with Doc 0 + Doc 2 as context.

## Key Insights
- NotebookLM's killer feature is chat-with-sources. Creators want to ASK questions, not just read.
- ChatSheet already exists with iterate modes -- EXTEND it, don't replace it
- Cost: ~$0.012/message (Gemini Flash, 30K context + 1K response)
- Chat is FREE for Pro users (included, not credit-based) -- sticky feature
- Context: send Doc 0 (source ledger) + Doc 2 (research brief) as system context
- Conversation history maintained per job (multi-turn)

## Requirements

### Functional
- New "Chat" tab in ChatSheet alongside existing "Iterate" and "Brainstorm" tabs
- Free-form text input for questions about the research
- Multi-turn conversation with history (stored per job)
- Context: Doc 0 + Doc 2 sent as system message to Gemini Flash
- Source-aware answers: model cites which source supports each answer
- Quick-action suggestions: "What contradictions exist?", "Summarize Source 2", "What's missing?"
- Conversation persisted in Supabase (reload page = history preserved)

### Non-Functional
- Response time: < 3s for typical question
- Conversation history: max 20 messages per job (truncate oldest if exceeded)
- Mobile-friendly: ChatSheet already responsive

## Architecture

### Backend
New endpoint: `POST /jobs/{job_id}/chat`

```json
// Request
{
  "message": "What did the second source say about market size?",
  "conversation_id": "conv_abc123"  // optional, for multi-turn
}

// Response
{
  "response": "According to [Source 2 - TechReview], the market size...",
  "sources_cited": ["SRC_2"],
  "conversation_id": "conv_abc123"
}
```

### Context Building
```python
def build_chat_context(job_id: str) -> str:
    doc_0 = get_document(job_id, "doc_0")  # Source ledger
    doc_2 = get_document(job_id, "doc_2")  # Research brief
    return f"""
    You are a research assistant. The user has completed a research job.
    Below are the sources and findings. Answer questions based ONLY on this data.
    Cite sources using [Source Name] format.

    === SOURCES ===
    {format_doc_0(doc_0)}

    === RESEARCH FINDINGS ===
    {format_doc_2(doc_2)}
    """
```

### Conversation Storage
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL,
  user_id UUID NOT NULL,
  role TEXT NOT NULL,  -- 'user' or 'assistant'
  content TEXT NOT NULL,
  sources_cited TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_chat_messages_job_id ON chat_messages(job_id);
```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `frontend/components/job-detail-v2/chat-sheet.tsx` | Add "Chat" tab with free-form conversation UI |
| `frontend/store/jobs.ts` | Add `chatMessages` state and `sendChatMessage()` action |
| `backend/app/routes/jobs_routes.py` | Add `POST /jobs/{id}/chat` and `GET /jobs/{id}/chat/history` |
| `backend/app/main.py` | Register chat routes (or add to jobs router) |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/services/chat_service.py` | Chat context building, Gemini call, history management | ~100 |
| `frontend/components/job-detail-v2/chat-conversation.tsx` | Message list + input for chat tab | ~120 |
| `frontend/components/job-detail-v2/chat-message-bubble.tsx` | Individual message with citation highlights | ~50 |
| `frontend/components/job-detail-v2/chat-quick-actions.tsx` | Suggested question chips | ~40 |
| `frontend/hooks/use-chat.ts` | TanStack mutation for sending messages + query for history | ~50 |

## Implementation Steps

### Task 6.1: Create chat_messages table
1. Create Supabase migration:
   ```sql
   CREATE TABLE IF NOT EXISTS chat_messages (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     job_id UUID NOT NULL,
     user_id UUID NOT NULL,
     role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
     content TEXT NOT NULL,
     sources_cited TEXT[] DEFAULT '{}',
     created_at TIMESTAMPTZ DEFAULT now()
   );
   CREATE INDEX idx_chat_messages_job_id ON chat_messages(job_id);
   ```
2. RLS: users read/write own messages only

### Task 6.2: Create chat service
1. Create `backend/services/chat_service.py`
2. `build_chat_context(job_id: str) -> str`:
   - Load Doc 0 and Doc 2 from job artifacts
   - Format into structured system prompt
   - Include source names and IDs for citation
3. `send_chat_message(job_id: str, user_id: str, message: str) -> ChatResponse`:
   - Load conversation history (last 10 messages for context window)
   - Build system prompt with `build_chat_context()`
   - Call Gemini Flash at temperature 0.3
   - Parse response, extract cited source IDs
   - Store user message + assistant response in `chat_messages`
   - Track cost in `cost_tracker`
4. `get_chat_history(job_id: str, user_id: str, limit: int = 20) -> list[ChatMessage]`

### Task 6.3: Create chat API endpoints
1. In `backend/app/routes/jobs_routes.py` (or new `chat_routes.py`):
   - `POST /jobs/{job_id}/chat` -- send message, get response
   - `GET /jobs/{job_id}/chat/history` -- get conversation history
2. Auth: verify user owns the job
3. Rate limit: 10 messages/minute per user

### Task 6.4: Create frontend chat components
1. Create `frontend/components/job-detail-v2/chat-message-bubble.tsx`:
   - User messages: right-aligned, dark background
   - Assistant messages: left-aligned, with source citations highlighted
   - Citations rendered as `CitationLink` components (from Phase 02)
2. Create `frontend/components/job-detail-v2/chat-quick-actions.tsx`:
   - Row of chips: "What contradictions exist?", "Summarize key findings", "What's missing?"
   - Clicking a chip populates the input and submits
3. Create `frontend/components/job-detail-v2/chat-conversation.tsx`:
   - Message list (scrollable, newest at bottom)
   - Text input with send button
   - Loading state while waiting for response
   - Quick action chips shown when conversation empty
4. Create `frontend/hooks/use-chat.ts`:
   - `useChatHistory(jobId)` -- TanStack Query for loading history
   - `useSendMessage(jobId)` -- TanStack Mutation for sending

### Task 6.5: Integrate into ChatSheet
1. In `frontend/components/job-detail-v2/chat-sheet.tsx`:
   - Add third tab: "Chat" alongside "Iterate" and "Brainstorm"
   - Chat tab renders `ChatConversation` component
   - Tab only enabled when job is completed (not while running)
2. Keep existing Iterate and Brainstorm tabs unchanged

### Task 6.6: Test
1. Backend: unit test `build_chat_context()` with sample doc data
2. Backend: integration test chat endpoint with mocked Gemini response
3. Manual: complete a job, open Chat tab, ask questions
4. Manual: verify multi-turn conversation persists across page reloads
5. Manual: verify source citations in responses are accurate
6. `pytest backend/tests/ -v` && `npm run build`

## Todo Checklist
- [ ] 6.1 Create `chat_messages` table in Supabase
- [ ] 6.2 Create `chat_service.py` (context building, Gemini call, history)
- [ ] 6.3 Create chat API endpoints (POST /chat, GET /chat/history)
- [ ] 6.4 Create frontend chat components (conversation, bubbles, quick actions)
- [ ] 6.5 Integrate Chat tab into existing ChatSheet
- [ ] 6.6 Test: unit, integration, manual

## Success Criteria
- User can ask free-form questions about their research
- Responses cite specific sources by name
- Conversation history persists across page reloads
- Quick action chips provide useful starting questions
- Cost per message: ~$0.012
- Response time: < 3s

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini hallucinates beyond research context | MEDIUM | System prompt: "Answer ONLY from provided context. Say 'I don't have that info' otherwise." |
| Context too large for Gemini Flash | LOW | Doc 0+2 typically < 50K tokens. Flash has 1M context. |
| Chat message cost accumulation | LOW | $0.012/msg. 100 msgs = $1.20. Include in Pro tier. |
| Conversation history grows too long | LOW | Cap at 20 messages. Summarize older messages if needed. |

## Security Considerations
- Chat messages stored per user_id -- RLS enforced
- Rate limiting: 10 messages/minute prevents abuse
- No arbitrary code execution in chat responses
- User message content sanitized before storage
