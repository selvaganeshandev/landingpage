# Testing Competitor APIs Integration

## Quick Test Steps

1. **Open Browser Console** (F12 → Console tab)
2. **Navigate to** `http://localhost:8080/competitors`
3. **Look for these console messages:**

### Expected Console Output:

```
🔵 API CALL: Loading competitive strength analysis for domain: 1
🔵 API URL: /competitors/competitive-strength-analysis?domain_id=1
✅ Competitive strength analysis response: [...]
✅ Response type: object Is array: true

🔵 API CALL: Loading competitive insights for domain: 1
🔵 API URL: /competitors/competitive-insights?domain_id=1
✅ Competitive insights response: [...]
✅ Response type: object Is array: true

🔵 API CALL: Loading answer gap analysis for domain: 1
🔵 API URL: /competitors/answer-gap-analysis?domain_id=1
✅ Answer gap analysis response: [...]
✅ Response type: object Is array: true
```

### If You See Errors:

```
❌ Failed to load competitive strength analysis: Error: ...
❌ Error message: ...
❌ Error stack: ...
```

## Check Network Tab

1. Open **DevTools → Network tab**
2. Filter by: `competitive` or `answer-gap`
3. Check each request:
   - **Status**: Should be 200 (OK)
   - **Response**: Should show JSON data
   - **Request URL**: Should match the console logs

## Manual API Test (using curl or browser)

### Test Competitive Strength Analysis:
```
http://localhost:8000/competitors/competitive-strength-analysis/?domain_id=1
```

### Test Competitive Insights:
```
http://localhost:8000/competitors/competitive-insights/?domain_id=1
```

### Test Answer Gap Analysis:
```
http://localhost:8000/competitors/answer-gap-analysis/?domain_id=1
```

## Common Issues:

1. **404 Not Found**: Backend server not running or URLs not registered
2. **401 Unauthorized**: Need to login first
3. **500 Server Error**: Check backend logs for errors
4. **CORS Error**: Backend CORS settings need to allow frontend origin
5. **Empty Arrays**: Database has no competitor/analytics data

## Next Steps:

If APIs are returning empty arrays, you need to:
1. Add competitors to the database
2. Process competitors (run competitor processing)
3. Ensure analytics data exists

