# demo-api — Project Status

## Current Status

Backend API for user management and authentication. Currently implementing OAuth2 flow with Google provider.

**Sprint:** 3 of 6
**Progress:** 65%

## Blockers

- Waiting for DevOps to provision Redis instance for session storage
- Google OAuth credentials not yet configured in staging environment

## Next Steps

1. Complete OAuth2 callback handler once Redis is available
2. Add refresh token rotation logic
3. Write integration tests for full auth flow
4. Deploy to staging for QA

## Recent Decisions

- **Session storage**: Redis over JWT for revocation support
- **Rate limiting**: 100 req/min per user, 1000 req/min per API key
- **Token expiry**: Access 15min, refresh 7 days

## Team

- **Backend lead**: Alice
- **DevOps**: Bob
- **QA**: Charlie
