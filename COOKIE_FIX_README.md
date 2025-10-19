# Cookie Authentication Fix for Production

## Problem
When accessing the application via the production Cloudflare domain, users were:
- Redirected to login after posting jobs
- Seeing navigation elements (indicating token storage issues)
- Experiencing authentication state inconsistencies

## Root Cause
Cookies in production were not being set with the correct `domain` parameter, causing the browser to reject them when accessed through the Cloudflare proxied domain.

## Changes Made

### 1. `config.py`
Added `COOKIE_DOMAIN` configuration:
```python
COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', 'find-tradespeople.com' if IS_PRODUCTION else None)
```

### 2. `resources/auth.py`
Updated `Register`, `Login`, and `Logout` classes to:
- Use the `COOKIE_DOMAIN` from config
- Set domain parameter on cookies when in production
- Added debug logging for cookie settings

### 3. `app.py`
Updated JWT refresh logic to:
- Use `COOKIE_DOMAIN` from config
- Apply domain parameter on refreshed tokens
- Enhanced logging to show cookie configuration

## Deployment Steps

### For Local Development
No changes needed. The app will continue to work on:
- `http://localhost:8000`
- `http://192.168.0.46:8000`
- `http://192.168.0.37:8000`

### For Production (Cloud Run + Cloudflare)

#### 1. Environment Variables
Add to your Cloud Run environment:
```bash
FLASK_ENV=production
COOKIE_DOMAIN=find-tradespeople.com
```

#### 2. Cloudflare SSL/TLS Settings
**CRITICAL**: Ensure Cloudflare SSL/TLS mode is set to **Full (strict)** or **Full**:
- Go to Cloudflare Dashboard
- Select your domain
- Go to SSL/TLS tab
- Set to "Full (strict)" (recommended) or "Full"
- **DO NOT use "Flexible"** - it will break secure cookies

#### 3. Cloudflare Cookie Settings
Ensure cookies are not being blocked:
- Go to Rules → Configuration Rules
- Check that `find-tradespeople.com` allows cookies
- Disable "Always Use HTTPS" if it's causing issues (the backend already handles this)

#### 4. Deploy to Cloud Run
```bash
gcloud run deploy backendconstrution \
  --source . \
  --region us-central1 \
  --set-env-vars FLASK_ENV=production,COOKIE_DOMAIN=find-tradespeople.com \
  --allow-unauthenticated
```

#### 5. Verify CORS Origins
Ensure your production frontend URL is in the CORS origins list in `app.py`:
```python
origins=[
    "http://localhost:8000",
    "http://192.168.0.46:8000",
    "http://192.168.0.37:8000",
    "https://find-tradespeople.com"  # ✅ Already present
],
```

## Testing After Deployment

### 1. Check Backend Logs
After deployment, check Cloud Run logs for:
```
🚀 Starting backend in PRODUCTION mode
   Cookie settings: secure=True, samesite=None, domain=find-tradespeople.com
```

### 2. Test Authentication Flow
1. Register a new user
2. Check browser DevTools → Application → Cookies
3. Verify `access_token` cookie has:
   - Domain: `.find-tradespeople.com` or `find-tradespeople.com`
   - Secure: ✓
   - HttpOnly: ✓
   - SameSite: None

### 3. Test Job Posting
1. Post a job
2. Verify you're redirected to job details (not login)
3. Check that nav elements show correctly

## Troubleshooting

### Issue: Still redirected to login
**Check:**
1. Browser console for errors
2. Network tab for failed requests
3. Cookie is being set (DevTools → Application → Cookies)
4. Cloudflare SSL/TLS is "Full" or "Full (strict)"

### Issue: Cookie not visible in browser
**Check:**
1. `COOKIE_DOMAIN` environment variable is set correctly
2. Cloudflare is not blocking third-party cookies
3. Browser is not in strict privacy mode
4. SSL/TLS encryption is end-to-end

### Issue: CORS errors
**Check:**
1. Frontend origin matches one in CORS config
2. Cloud Run allows credentials
3. Cloudflare is not modifying headers

## Frontend Considerations

Your frontend should:
1. Use `credentials: 'include'` in fetch requests
2. Not send `Authorization` header (cookies are used)
3. Handle 401 responses by redirecting to login

Example fetch configuration:
```typescript
fetch('https://api.find-tradespeople.com/endpoint', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(data)
})
```

## Security Notes

### Production Security
- ✅ Cookies are `httpOnly` (prevents XSS)
- ✅ Cookies are `secure` (HTTPS only)
- ✅ `SameSite=None` for cross-domain (Cloudflare → Cloud Run)
- ✅ Domain scoped to prevent cookie theft

### Development Security
- Cookies use `SameSite=Lax` (same-site only)
- `secure=False` (allows HTTP in development)
- No domain scoping (works on any localhost/IP)

## Next Steps

1. Deploy with the new environment variables
2. Test authentication flow in production
3. Monitor Cloud Run logs for cookie-related messages
4. If issues persist, check Cloudflare settings

## Support

If you continue to experience issues:
1. Share Cloud Run logs (with cookie settings print statements)
2. Share browser DevTools → Network tab showing cookie headers
3. Confirm Cloudflare SSL/TLS mode

