# Website Spotify Authentication Implementation Prompt

## 🎯 **Task: Implement Automatic Spotify Authentication on Website**

### **Context:**
I have a Discord bot with Spotify integration. Currently, users need to manually copy authorization codes. I want to implement automatic authentication like bleed bot where users just click a link and get automatically connected.

### **Desired Flow (Like Bleed Bot):**
1. User types `!spotify login` in Discord
2. Bot automatically opens Spotify auth in user's browser
3. User authorizes on Spotify
4. Spotify redirects to my website
5. **NEEDED: Website automatically completes the authentication**
6. User is immediately connected - no manual steps!

### **Technical Requirements:**

#### **1. Website Endpoint Needed:**
- **URL**: `https://wizardspell.netlify.app/spotify/callback`
- **Method**: GET
- **Parameters**: 
  - `code` - Authorization code from Spotify
  - `state` - Security state parameter
  - `error` - Error message (if authorization failed)

#### **2. Backend API Endpoint Needed:**
- **URL**: `https://your-backend.com/api/spotify/auth`
- **Method**: POST
- **Body**: 
  ```json
  {
    "code": "authorization_code_from_spotify",
    "state": "security_state_parameter",
    "user_id": "discord_user_id"
  }
  ```

#### **3. Frontend Implementation:**
The callback page should:
1. Extract `code` and `state` from URL parameters
2. Send POST request to backend API with the code and state
3. Show success/error message to user
4. Redirect user back to Discord or show completion message

#### **4. Backend Implementation:**
The API endpoint should:
1. Validate the state parameter (security check)
2. Exchange authorization code for access token using Spotify API
3. Store user tokens securely
4. Return success/error response

### **Example Implementation:**

#### **Frontend (JavaScript):**
```javascript
// Extract parameters from URL
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');
const error = urlParams.get('error');

if (error) {
    // Show error message
    showError(error);
} else if (code && state) {
    // Send to backend for processing
    completeAuth(code, state);
} else {
    // Invalid request
    showError('Invalid authorization request');
}

async function completeAuth(code, state) {
    try {
        const response = await fetch('https://your-backend.com/api/spotify/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: code,
                state: state
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess();
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('Failed to complete authentication');
    }
}
```

#### **Backend (Node.js/Express example):**
```javascript
app.post('/api/spotify/auth', async (req, res) => {
    const { code, state } = req.body;
    
    try {
        // Validate state parameter
        if (!validateState(state)) {
            return res.json({ success: false, error: 'Invalid state parameter' });
        }
        
        // Exchange code for token
        const tokenResponse = await fetch('https://accounts.spotify.com/api/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic ' + Buffer.from(clientId + ':' + clientSecret).toString('base64')
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: code,
                redirect_uri: 'https://wizardspell.netlify.app/spotify/callback'
            })
        });
        
        const tokens = await tokenResponse.json();
        
        if (tokens.access_token) {
            // Store tokens for user (you'll need to get user_id from state)
            await storeUserTokens(userId, tokens);
            res.json({ success: true });
        } else {
            res.json({ success: false, error: 'Failed to get access token' });
        }
    } catch (error) {
        res.json({ success: false, error: 'Authentication failed' });
    }
});
```

### **Spotify API Credentials:**
- **Client ID**: `e90e80ecde3145a3beb5e02980f1bad6`
- **Client Secret**: `edd6cee9fe3b433d99b18590a2d0d3b3`
- **Redirect URI**: `https://wizardspell.netlify.app/spotify/callback`

### **Security Considerations:**
1. **State Parameter**: Use cryptographically secure random strings
2. **Token Storage**: Store access tokens securely (encrypted)
3. **HTTPS**: All communication must be over HTTPS
4. **CORS**: Configure CORS properly for your domain

### **User Experience:**
1. User types `!spotify login` in Discord
2. Bot automatically opens Spotify auth in browser
3. User authorizes on Spotify
4. Gets redirected to your website
5. Sees "✅ Spotify Authorized! You can now use music commands in Discord."
6. User is immediately connected - can use `play <song>` commands right away!

### **Error Handling:**
- Invalid authorization code
- Expired authorization code
- Network errors
- Invalid state parameter
- Spotify API errors

### **Testing:**
1. Test with valid authorization flow
2. Test with invalid/expired codes
3. Test error scenarios
4. Test on mobile devices
5. Test with different browsers

### **Files to Create/Modify:**
1. **Frontend**: `spotify/callback.html` (or appropriate page)
2. **Backend**: API endpoint for token exchange
3. **Database**: User token storage
4. **Configuration**: Environment variables for Spotify credentials

### **Success Criteria:**
- ✅ User types `!spotify login` in Discord
- ✅ Bot automatically opens Spotify auth
- ✅ User authorizes on Spotify
- ✅ Gets redirected to website
- ✅ Sees success message
- ✅ Can use Spotify commands in Discord immediately
- ✅ No manual steps required - completely automatic!

### **Additional Notes:**
- The Discord bot will need to be updated to use the new state-based authentication
- Consider implementing token refresh logic
- Add logging for debugging authentication issues
- Consider rate limiting for the API endpoint

---

**Goal**: Make the Spotify authentication as seamless as bleed bot - one click and done!
