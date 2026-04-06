# Phase 04: Paywall + Stripe

## Context Links
- [Business Viability](../../plans/reports/researcher-260406-1252-business-viability-analysis.md)
- [Brainstorm -- Pricing](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#proposed-product-tiers)

## Overview
- **Priority:** P1 (MVP -- revenue validation)
- **Status:** pending
- **Effort:** 2-3 days
- **Depends on:** Phase 01 (single-screen input), Phase 02 (hero doc)
- **Description:** Simple paywall: 3 free jobs, then $19/mo to continue. No credit system yet (Phase 10). Stripe Checkout for payment. Gate job creation after free quota exhausted.

## Key Insights
- Breakeven at 6 paid users ($114/mo covers infra)
- No credit system needed for MVP -- just "3 free jobs, then subscribe"
- Stripe Checkout is simplest integration (hosted page, webhook for subscription status)
- Free tier: Full mode, 3 sources max, no Script/Blog generation
- Pro tier: Full mode, unlimited sources, Script + Blog + Social, Sonnet polish

## Requirements

### Functional
- Track job count per user (Supabase `research_jobs` table already has `user_id`)
- After 3 completed jobs, show paywall: "Upgrade to Pro -- $19/mo"
- Paywall blocks "Start Research" button with upgrade CTA
- Stripe Checkout: redirect to Stripe hosted page, return to app on success
- Stripe webhook: update user subscription status in Supabase
- Pro badge in UI for subscribed users
- Manage subscription link (Stripe Customer Portal)

### Non-Functional
- Paywall check must be fast (< 100ms, local DB query)
- Stripe webhook must be idempotent
- Handle edge cases: expired card, cancelled subscription, webhook delay

## Architecture

### Data Model
```sql
-- Add to existing users/profiles table or create new
ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS
  stripe_customer_id TEXT,
  subscription_status TEXT DEFAULT 'free',  -- free, active, past_due, cancelled
  subscription_id TEXT,
  job_count INTEGER DEFAULT 0;
```

Or use a separate `subscriptions` table:
```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT DEFAULT 'free',  -- free, active, past_due, cancelled
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Payment Flow
```
User clicks "Upgrade" -> Backend creates Stripe Checkout session
-> Redirect to Stripe -> User pays -> Stripe webhook -> Backend updates status
-> Frontend polls/reads updated status -> Paywall removed
```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/app/routes/jobs_routes.py` | Add subscription check before job creation (line ~120) |
| `backend/state/impl/supabase_store.py` | Add `get_job_count(user_id)` and `get_subscription(user_id)` |
| `backend/config.py` | Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID` |
| `frontend/components/dashboard/single-screen-input.tsx` | Disable submit + show paywall when quota exceeded |
| `frontend/store/jobs.ts` | Add subscription status to user state |
| `frontend/lib/constants.ts` | Add `FREE_JOB_LIMIT = 3`, `PRO_PRICE = 19` |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/app/routes/billing_routes.py` | Stripe checkout session, webhook, portal | ~120 |
| `backend/services/billing_service.py` | Stripe business logic (create customer, check sub) | ~80 |
| `frontend/components/paywall/upgrade-banner.tsx` | "Upgrade to Pro" CTA component | ~60 |
| `frontend/components/paywall/subscription-badge.tsx` | Pro/Free badge in sidebar | ~30 |
| `frontend/hooks/use-subscription.ts` | Hook to fetch/cache subscription status | ~40 |

### New Dependencies
- `stripe` Python package in `requirements.txt`
- NO frontend Stripe SDK needed (using Checkout redirect, not Elements)

## Implementation Steps

### Task 4.1: Add Stripe Python package
1. Add `stripe>=8.0.0` to `requirements.txt`
2. Add config vars to `backend/config.py`:
   - `STRIPE_SECRET_KEY: str = ""`
   - `STRIPE_WEBHOOK_SECRET: str = ""`
   - `STRIPE_PRICE_ID: str = ""` (Pro monthly price)
3. Create Stripe product + price in Stripe Dashboard: "Research Agent Pro", $19/mo, recurring

### Task 4.2: Create subscriptions table
1. Create Supabase migration or SQL:
   ```sql
   CREATE TABLE IF NOT EXISTS subscriptions (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     user_id UUID NOT NULL,
     stripe_customer_id TEXT,
     stripe_subscription_id TEXT,
     status TEXT DEFAULT 'free',
     current_period_end TIMESTAMPTZ,
     created_at TIMESTAMPTZ DEFAULT now(),
     updated_at TIMESTAMPTZ DEFAULT now()
   );
   CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
   ```
2. Add RLS policy: users can read their own subscription

### Task 4.3: Create billing service
1. Create `backend/services/billing_service.py`
2. Functions:
   - `get_or_create_stripe_customer(user_id, email) -> str` (customer_id)
   - `create_checkout_session(user_id, success_url, cancel_url) -> str` (session_url)
   - `get_subscription_status(user_id) -> SubscriptionStatus`
   - `handle_webhook_event(payload, sig_header) -> None`
   - `get_job_count(user_id) -> int` (query research_jobs table)
   - `can_create_job(user_id) -> tuple[bool, str]` (True/False + reason)

### Task 4.4: Create billing routes
1. Create `backend/app/routes/billing_routes.py`
2. Endpoints:
   - `POST /billing/checkout` -- create Checkout session, return URL
   - `POST /billing/webhook` -- Stripe webhook handler (no auth, signature verified)
   - `GET /billing/subscription` -- get current user's subscription status + job count
   - `POST /billing/portal` -- create Stripe Customer Portal session for managing subscription
3. Register router in `backend/app/main.py`

### Task 4.5: Gate job creation
1. In `backend/app/routes/jobs_routes.py`, `create_job_endpoint()`:
   - Before creating job, call `billing_service.can_create_job(user.id)`
   - If False, return 402 with `{ "error": "subscription_required", "jobs_used": N, "limit": 3 }`
2. Handle 402 in frontend API client

### Task 4.6: Frontend paywall UI
1. Create `frontend/hooks/use-subscription.ts`:
   - Fetch `GET /billing/subscription` on mount
   - Cache with TanStack Query, stale time 60s
   - Returns `{ status, jobsUsed, jobLimit, canCreate }`
2. Create `frontend/components/paywall/upgrade-banner.tsx`:
   - Shows when `canCreate === false`
   - "You've used 3/3 free research jobs. Upgrade to Pro for unlimited."
   - "Upgrade -- $19/mo" button -> calls `POST /billing/checkout` -> redirect to Stripe
3. Create `frontend/components/paywall/subscription-badge.tsx`:
   - Shows "Pro" badge in sidebar for active subscribers
   - Shows "Free (2/3)" for free users
4. In `frontend/components/dashboard/single-screen-input.tsx`:
   - If `canCreate === false`, disable submit button, show `UpgradeBanner` inline

### Task 4.7: Webhook handling
1. Handle these Stripe events in webhook:
   - `checkout.session.completed` -- create/update subscription, status = "active"
   - `customer.subscription.updated` -- update status, period_end
   - `customer.subscription.deleted` -- status = "cancelled"
   - `invoice.payment_failed` -- status = "past_due"
2. All webhook handlers must be idempotent (check if already processed)

### Task 4.8: Test
1. Backend: unit test `can_create_job()` with 0, 3, 4 jobs
2. Backend: unit test webhook handler with sample Stripe events
3. Manual: Stripe test mode -- create account, subscribe, verify paywall removed
4. Manual: cancel subscription, verify paywall returns
5. `pytest backend/tests/ -v`

## Todo Checklist
- [ ] 4.1 Add Stripe package + config
- [ ] 4.2 Create subscriptions table in Supabase
- [ ] 4.3 Create billing service
- [ ] 4.4 Create billing routes (checkout, webhook, subscription, portal)
- [ ] 4.5 Gate job creation with subscription check
- [ ] 4.6 Frontend paywall UI (banner, badge, hook)
- [ ] 4.7 Implement Stripe webhook handlers
- [ ] 4.8 Test: unit + manual with Stripe test mode

## Success Criteria
- Free users get exactly 3 jobs, then see paywall
- Stripe Checkout redirects work (test mode)
- Webhook updates subscription status within seconds
- Pro users have unlimited job creation
- Subscription badge visible in UI
- Manage subscription (cancel/update card) works via Stripe Portal

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Stripe account not created yet | BLOCKER | Human action required: create Stripe account before implementing |
| Webhook delivery delay | LOW | Frontend polls subscription status as fallback |
| Free tier abuse (multiple accounts) | MEDIUM | Rate limit by IP for unauthenticated. Auth required for jobs. |
| Payment disputes/chargebacks | LOW | Stripe handles disputes. Low-value transactions ($19). |

## Security Considerations
- `STRIPE_SECRET_KEY` in env vars only, never committed
- Webhook signature verification mandatory (prevent spoofed events)
- No PII stored locally -- Stripe handles all payment data
- RLS on subscriptions table: users read own row only
- Checkout session created server-side only (no client-side key exposure)
