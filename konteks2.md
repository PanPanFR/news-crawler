# Updated Frontend Design for News Aggregator with AI Summarizer (No Login)

---

## Backend Architecture Overview

The backend follows an optimized microservices architecture with the following components:

### System Architecture
```
[Crawler] -> [Database PostgreSQL] -> [Skrip Prioritas] -> [Antrian Prioritas REDIS] -> [Worker Summarizer] -> [Database PostgreSQL (Update)]
```

### Backend Components
- **Web Service**: Handles API requests and serves the frontend
- **Redis Queue**: Manages prioritized news summarization tasks
- **Background Worker**: Processes the summarization queue
- **Cron Job**: Triggers crawling every 40 minutes
- **Supabase Database**: Stores news articles with summaries

### API Endpoints
- `GET /api/news`: List news with filters and pagination
- `GET /api/news/{id}`: Get specific news item
- `POST /api/news/crawl`: Trigger manual crawling
- `POST /api/news/prioritize`: Trigger prioritization of unsummarized news
- `POST /api/news/summarize`: Trigger summarization batch
- `POST /api/news/cleanup`: Trigger data cleanup
- `POST /trigger-crawl`: Cron job endpoint to start crawling and prioritization

### Tech Stack

| Layer             | Technology / Library                   | Purpose                                          |
|-------------------|--------------------------------------|--------------------------------------------------|
| Framework         | Next.js                              | React framework with SSR & SSG                    |
| Animation         | Framer Motion                        | Smooth, interactive UI animations                 |
| Styling           | Tailwind CSS / CSS Modules / globals.css | UI styling and responsive layout                 |
| State Management  | React Context or Zustand/SWR         | Global state and data fetching/caching            |
| Data Fetching     | SWR or React Query                   | Efficient client-side data fetching and caching   |
| API Interaction   | Fetch API or Axios                   | Backend API communication                          |
| Routing           | Next.js built-in routing             | Page navigation                                  |
| Notifications     | Toast UI or similar                  | Error and info feedback                            |

---

## User Flow & Screens

### 1. Homepage (News List)
- Lists latest news with headlines and AI-generated summaries if available.
- Category filter tabs or dropdown.
- Search bar for keyword searching.
- Infinite scroll or pagination.
- Framer Motion animations for news card fade-in, list updates, and filter transitions.

### 2. News Detail Page
- Full AI summary or loading indicator if summary is processing.
- Link to original news article.
- Share button and optional save/bookmark functionality stored locally.
- Page transition animations with Framer Motion.

### 3. History / Saved News Panel (Optional)
- Shows locally saved news articles.
- Slide-in panel with animated add/remove of items.
- Easily dismissable.

### 4. Loading & Error States
- Animated loading skeletons for content fetch.
- Subtle animated toasts for errors or notifications.

---

## Backend Integration Considerations

### News Summaries
- Summaries are processed asynchronously by the worker with 2-second intervals
- The frontend should handle cases where summaries are not yet available
- Unsummarized articles will have NULL summary fields in the API response

### API Interaction
- The frontend primarily consumes the `/api/news` endpoints
- Summaries are pre-processed by the background worker to optimize response times
- Implement optimistic UI where appropriate to improve user experience

### Loading States
- Implement skeleton loaders for news cards while API calls are in progress
- For articles without summaries, show a "Summary being processed..." message
- Use SWR or React Query for smart caching and background data updating

---

## Navigation & Interaction

- User visits homepage, sees news list with summaries (when available).
- Filters or searches news, with animated UI response.
- Selects news to view detail page with full summary and source.
- Uses saved/history panel for revisiting news (if applicable).
- Smooth animated transitions at every step.

---

## Important Notes

- No login system: All saved/history data is kept in localStorage.
- Summaries are processed asynchronously by the background worker and fetched when available.
- Framer Motion used extensively for transitions, layout shifts, entrance/exit animations.
- Responsive design for mobile and desktop with Tailwind CSS.
- Prefetch data on hover/link focus to optimize navigation speed.
- UI elements accessible with proper ARIA roles and keyboard navigation.
- Handle scenarios where API summaries are not yet available with appropriate loading states.

---

This design ensures a responsive, smooth, and user-friendly news browsing experience with integrated AI summaries while keeping everything simple with no login requirement. The frontend is designed to work seamlessly with the optimized backend architecture featuring Redis queues, background processing, and cron-scheduled updates.
