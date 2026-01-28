# Social Creator

AI-powered social media post generation with human-in-the-loop approval.

## Features

- **Chat Interface**: Conversational UI to describe what you want to post
- **Web Research**: Uses Perplexity API to find current information
- **Image Generation**: Uses Nano Banana (Google Gemini) for visuals
- **Multi-Platform**: Creates posts for Twitter, LinkedIn, and Instagram
- **HITL Approval**: Review and edit content before posting
- **Real-time Updates**: SSE streaming shows AI thinking in real-time

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│            (apps/social-creator)                         │
│  ┌─────────────┐  ┌─────────────────────────────────┐   │
│  │   Chat UI   │  │         Bento Grid              │   │
│  │  SSE Stream │  │    Post Cards + Approval        │   │
│  └─────────────┘  └─────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ SSE + REST
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 FlowForge Server                         │
│  /api/v1/runs/{id}/stream  - SSE streaming              │
│  /api/v1/approvals         - HITL approve/reject        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              FlowForge Worker                            │
│  (examples/social-creator/workflow.py)                  │
│                                                          │
│  step.agent() with tools:                                │
│  - web_search (Perplexity)                               │
│  - generate_image (Nano Banana)                          │
│  - post_to_twitter (HITL)                                │
│  - post_to_linkedin (HITL)                               │
│  - post_to_instagram (HITL)                              │
└─────────────────────────────────────────────────────────┘
```

## Setup

### 1. Start FlowForge Infrastructure

```bash
cd flowforge
docker-compose up -d
```

### 2. Start the Worker

```bash
cd examples/social-creator
python -m workflow
```

### 3. Start the Frontend

```bash
cd apps/social-creator
pnpm install
pnpm dev
```

Open http://localhost:3000

## Environment Variables

```bash
# FlowForge Server (required)
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379

# AI Provider (one required)
OPENAI_API_KEY=...
# or
ANTHROPIC_API_KEY=...

# Optional: Real web search
PERPLEXITY_API_KEY=...

# Optional: Real image generation
GOOGLE_API_KEY=...

# Optional: Real social posting
TWITTER_BEARER_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
INSTAGRAM_ACCESS_TOKEN=...
```

## Usage

1. Type what you want to post about in the chat
2. AI researches the topic and generates content
3. Review generated posts in the bento grid
4. Edit content if needed
5. Approve to "post" (simulated without API keys)

## Example Prompts

- "Create a post announcing our new AI product launch"
- "Share insights about the latest trends in remote work"
- "Promote our upcoming webinar on machine learning"
