# MoodFeed REST API Documentation

Base URL: `https://moodfeed-api.up.railway.app/v1`

## Endpoints

### 1. Mood AI & Posts
- `GET /v1/posts` - List posts with emotional metadata
- `POST /v1/posts` - Create a post with automated Mood AI scoring
- `POST /v1/posts/{id}/like` - Toggle like
- `POST /v1/posts/{id}/comments` - Add nested comment with Mood score
- `GET /v1/search?q={query}&mood={happy|sad|angry|anxious|neutral}` - Search & mood filter

### 2. User & Social Graph
- `GET /v1/users/{id}/profile` - User profile, statistics, and follow status
- `POST /v1/users/{id}/follow` - Follow user
- `DELETE /v1/users/{id}/follow` - Unfollow user

### 3. Notifications & Activity
- `GET /v1/notifications` - Get real-time notifications
- `PATCH /v1/notifications/read-all` - Mark all notifications as read

### 4. Billing & Stripe
- `GET /v1/billing/plans` - List available pricing plans
- `POST /v1/billing/checkout` - Create Stripe Checkout session

### 5. Admin & Analytics
- `GET /v1/admin/stats` - SaaS KPIs (DAU, MAU, MRR)
- `GET /v1/analytics/dashboard` - Personal 7-day mood trends and engagement
