# Testing Rules

## Test Requirements

### Backend (Python)
- Run tests with: `pytest`
- Test location: `backend/tests/`
- Mock external APIs in tests
- Never make real API calls in tests

### Frontend (Next.js)
- Run tests with: `npm test`
- Test location: `frontend/__tests__/`
- Use React Testing Library

## Before Commit

```bash
# Backend
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
pytest

# Frontend
cd frontend
npm run lint
npm run build
```

## Before Push

- All tests must pass
- No TypeScript errors
- No linting errors
- API keys must not be committed
