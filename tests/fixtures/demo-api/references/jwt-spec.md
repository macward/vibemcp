# JWT Specification

## Token Structure

### Access Token

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1707500000,
  "iat": 1707499100,
  "type": "access"
}
```

### Refresh Token

```json
{
  "sub": "user_id",
  "jti": "unique_token_id",
  "exp": 1708103900,
  "iat": 1707499100,
  "type": "refresh"
}
```

## Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Algorithm | HS256 | Symmetric, simple |
| Access TTL | 900s (15min) | Short-lived |
| Refresh TTL | 604800s (7d) | Long-lived |
| Issuer | demo-api | Validate on verify |

## Refresh Flow

1. Client sends refresh token to `/auth/refresh`
2. Server validates token and checks Redis blacklist
3. Server issues new access + refresh token pair
4. Old refresh token is blacklisted in Redis

## Security Notes

- Refresh tokens must be stored securely (HttpOnly cookie or secure storage)
- Implement token rotation to detect token theft
- Redis TTL matches token expiry for automatic cleanup
