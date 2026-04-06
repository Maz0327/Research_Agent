# Phase 10: Credit System + Billing Tiers

## Context Links
- [Brainstorm -- Pricing Tiers](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#proposed-product-tiers)
- [Business Viability](../../plans/reports/researcher-260406-1252-business-viability-analysis.md#4-unit-economics-by-tier)
- Phase 04 (Paywall): simple $19/mo already implemented

## Overview
- **Priority:** P3 (Phase 2 -- Growth)
- **Status:** pending
- **Effort:** 1-2 weeks
- **Depends on:** Phase 04 (Stripe paywall already working)
- **Description:** Upgrade from simple paywall to credit-based system with tiers. Free (3 jobs), Pro ($19/mo, 50 credits), Studio ($49/mo, 200 credits). Credit costs vary by operation.

## Key Insights
- Phase 04 implements simple "3 free jobs then $19/mo." This phase adds granularity.
- Credit pricing allows different costs for different operations (Quick=1, Full=3, Script=2)
- Chat is free for all paid tiers (included, not credit-based) -- sticky feature
- Need usage dashboard so users see remaining credits
- Overage handling: block or allow purchase of credit packs

## Requirements

### Functional
- Three tiers: Free, Pro ($19/mo), Studio ($49/mo)
- Credit allocation per tier per billing cycle
- Credit costs per operation:
  - Quick research: 1 credit
  - Full research: 3 credits
  - Script generation: 2 credits
  - Blog generation: 2 credits
  - Social kit: 1 credit
  - Chat: free (included for Pro+)
  - Creator Brief (Doc 3): 1 credit
  - Producer Packet (Doc 4): 5 credits
- Usage dashboard: credits used / remaining / reset date
- Upgrade/downgrade flow via Stripe
- Studio tier: priority queue, API access (placeholder)

### Non-Functional
- Credit check must be fast (< 50ms, DB query)
- Credit deduction atomic (prevent race conditions)
- Monthly reset via Stripe webhook (subscription renewal)

## Architecture

### Data Model
```sql
-- Extend subscriptions table from Phase 04
ALTER TABLE subscriptions ADD COLUMN
  tier TEXT DEFAULT 'free',  -- free, pro, studio
  credits_total INTEGER DEFAULT 3,
  credits_used INTEGER DEFAULT 0,
  credits_reset_at TIMESTAMPTZ;

-- Credit usage log for analytics
CREATE TABLE credit_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  job_id UUID,
  operation TEXT NOT NULL,  -- quick, full, script, blog, social, brief, producer
  credits_spent INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_credit_usage_user_id ON credit_usage(user_id);
```

### Credit Constants
```python
TIER_CREDITS = {
    "free": 3,       # 3 jobs total (not monthly)
    "pro": 50,       # 50 credits/month
    "studio": 200,   # 200 credits/month
}

OPERATION_COSTS = {
    "quick": 1,
    "full": 3,
    "script": 2,
    "blog": 2,
    "social": 1,
    "brief": 1,
    "producer": 5,
    "chat": 0,  # free for paid tiers
}
```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/services/billing_service.py` | Add credit checking, deduction, reset logic |
| `backend/app/routes/billing_routes.py` | Add credit balance endpoint, upgrade/downgrade |
| `backend/app/routes/jobs_routes.py` | Replace simple job-count check with credit check |
| `backend/worker.py` | Deduct credits on job start (not completion, to prevent free runs on failure) |
| `frontend/hooks/use-subscription.ts` | Extend to include credit balance |
| `frontend/components/paywall/upgrade-banner.tsx` | Show credit balance, tier upgrade options |
| `frontend/components/dashboard/single-screen-input.tsx` | Show credit cost before submit |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/services/credit_service.py` | Credit management: check, deduct, reset, log | ~100 |
| `frontend/components/settings-v2/usage-dashboard.tsx` | Credits used/remaining/history | ~120 |
| `frontend/components/settings-v2/tier-comparison.tsx` | Feature comparison table for upgrade | ~80 |
| `frontend/components/common/credit-cost-badge.tsx` | Shows "3 credits" next to action buttons | ~30 |

## Implementation Steps

### Task 10.1: Create credit service
1. Create `backend/services/credit_service.py`
2. Functions:
   - `get_credit_balance(user_id) -> CreditBalance` (total, used, remaining, reset_date)
   - `check_credits(user_id, operation) -> tuple[bool, str]` (can afford + reason)
   - `deduct_credits(user_id, operation, job_id) -> bool` (atomic deduction)
   - `reset_credits(user_id, tier) -> None` (called on subscription renewal)
   - `log_credit_usage(user_id, job_id, operation, credits)` (audit trail)
3. Use `SELECT ... FOR UPDATE` for atomic credit deduction (prevent race conditions)

### Task 10.2: Create Stripe products for tiers
1. In Stripe Dashboard: create "Pro" ($19/mo) and "Studio" ($49/mo) prices
2. Update `backend/config.py` with `STRIPE_PRO_PRICE_ID` and `STRIPE_STUDIO_PRICE_ID`
3. Update billing routes: checkout session accepts tier parameter

### Task 10.3: Update billing webhook for tiers
1. In `backend/services/billing_service.py`:
   - On `checkout.session.completed`: set tier based on price ID, allocate credits
   - On `customer.subscription.updated`: handle tier change (upgrade/downgrade), adjust credits
   - On `invoice.paid` (renewal): reset credits for new billing cycle
2. Handle proration: if upgrading mid-cycle, grant additional credits proportionally

### Task 10.4: Replace job-count gate with credit gate
1. In `backend/app/routes/jobs_routes.py`:
   - Replace `can_create_job()` (Phase 04) with `credit_service.check_credits(user_id, operation)`
   - Return 402 with `{ credits_remaining, credits_required, tier, upgrade_url }`
2. In `backend/worker.py`:
   - Deduct credits at job START (after validation, before pipeline runs)
   - If pipeline fails, credits NOT refunded (prevents abuse)
   - Log usage

### Task 10.5: Frontend credit UI
1. Create `frontend/components/common/credit-cost-badge.tsx`:
   - Shows credit cost next to actions: "Start Research (3 credits)"
2. Create `frontend/components/settings-v2/usage-dashboard.tsx`:
   - Circular progress: "35/50 credits used"
   - Reset date display
   - Usage history table (last 20 operations)
3. Create `frontend/components/settings-v2/tier-comparison.tsx`:
   - Three columns: Free / Pro / Studio
   - Features per tier, credit limits, pricing
   - "Current plan" badge, "Upgrade" buttons
4. Update `frontend/components/dashboard/single-screen-input.tsx`:
   - Show credit cost before submit
   - If insufficient credits, show upgrade prompt

### Task 10.6: Test
1. Unit test: credit deduction atomicity (concurrent requests)
2. Unit test: tier credit allocation and reset
3. Integration test: create job -> credits deducted -> balance updated
4. Manual: Stripe test mode -- subscribe to Pro, use credits, verify balance
5. Manual: exhaust credits, verify paywall with upgrade option
6. `pytest backend/tests/ -v` && `npm run build`

## Todo Checklist
- [ ] 10.1 Create `credit_service.py`
- [ ] 10.2 Create Stripe products for Pro + Studio tiers
- [ ] 10.3 Update webhook handlers for tier management + credit reset
- [ ] 10.4 Replace job-count gate with credit-based gate
- [ ] 10.5 Frontend: credit badges, usage dashboard, tier comparison
- [ ] 10.6 Test: unit, integration, manual with Stripe

## Success Criteria
- Credits deducted atomically per operation
- Pro users get 50 credits/month, Studio gets 200
- Usage dashboard shows accurate balance
- Tier upgrade/downgrade works via Stripe
- Credits reset on billing cycle renewal
- 402 response when insufficient credits includes helpful upgrade info

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Race condition on credit deduction | MEDIUM | `SELECT FOR UPDATE` or Supabase RPC with atomic check-and-deduct |
| Credit refund requests on failures | LOW | Policy: no refunds on pipeline failure. Job attempted = credits spent. |
| Studio tier margin erosion at max usage | MEDIUM | 200 credits * $0.31 avg = $62 cost on $49 revenue. Monitor. Add overage if needed. |
| Proration complexity | LOW | Stripe handles proration natively for plan changes |

## Security Considerations
- Credit balance only readable by owning user (RLS)
- Credit deduction only via backend (no client-side credit manipulation)
- Stripe webhook signature verification (same as Phase 04)
- Rate limit billing endpoints
