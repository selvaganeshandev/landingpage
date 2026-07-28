# Favicon Fallback System

## Problem Solved
Many websites work with **either** `www.domain.com` **or** `domain.com` (but not both). This causes favicons to fail when the stored URL doesn't match the variant that actually works.

Example:
- Stored: `edelweisslife.in` ❌ (doesn't resolve)
- Works: `www.edelweisslife.in` ✅ (resolves correctly)

## Solution
A **cascading fallback system** that automatically tries multiple URL variants:

1. **Primary**: Uses URL as stored (`edelweisslife.in`)
2. **Alternative**: Tries www/non-www toggle (`www.edelweisslife.in`)
3. **Fallback**: Uses UI Avatars with company initial
4. **Final**: Hides image if all fail

## How It Works

### 1. Helper Functions (`/src/utils/faviconHelper.ts`)

```typescript
// Get favicon URL with HTTPS protocol
getFaviconUrl(url, size)
// → "https://www.google.com/s2/favicons?domain=https://example.com&sz=32"

// Get alternative variant (toggle www)
getAlternativeFaviconUrl(url, size)
// → If "example.com" → tries "www.example.com"
// → If "www.example.com" → tries "example.com"

// Get fallback placeholder
getFallbackIconUrl(name)
// → "https://ui-avatars.com/api/?name=E&background=3b82f6&color=fff"

// Handle errors automatically
handleFaviconError(event, url, name, size)
// → Cascades through: primary → alternative → fallback → hide
```

### 2. Usage in Components

**Old Way (no fallback):**
```typescript
<img
  src={`https://www.google.com/s2/favicons?domain=${domain.url}&sz=32`}
  onError={(e) => e.currentTarget.style.display = 'none'}
/>
```

**New Way (automatic fallback):**
```typescript
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

<img
  src={getFaviconUrl(domain.url, 32)}
  alt={domain.name}
  onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
/>
```

## Components Updated

✅ **DomainSelector.tsx** - Fully updated with cascading fallback
✅ **Sidebar.tsx** - Fully updated with cascading fallback

## Components To Update

The following components still have the old favicon implementation and should be updated:

- [ ] `CompetitorHeatmap.tsx`
- [ ] `GenerateNowDialog.tsx`
- [ ] `report-templates/ExecutiveDashboardTemplate.tsx`
- [ ] `report-templates/DetailedAnalyticsTemplate.tsx`
- [ ] `pages/DomainSettings.tsx`
- [ ] `pages/CompetitorDetail.tsx`
- [ ] `pages/OrganizationSettings.tsx`
- [ ] `pages/Citations.tsx`
- [ ] `pages/Reports.tsx`

## How to Update Remaining Components

For each file:

### 1. Add Import
```typescript
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
```

### 2. Remove Local getFaviconUrl Function
Delete the local helper function if it exists.

### 3. Update Image Tags
Replace:
```typescript
<img
  src={`https://www.google.com/s2/favicons?domain=${url}&sz=32`}
  onError={(e) => e.currentTarget.style.display = 'none'}
/>
```

With:
```typescript
<img
  src={getFaviconUrl(url, 32)}
  onError={(e) => handleFaviconError(e, url, name, 32)}
/>
```

## Testing

Test with these scenarios:

1. **www variant**: `www.example.com` (should work)
2. **non-www variant**: `example.com` (should fallback to www)
3. **Invalid domain**: `invalid-domain-xyz.com` (should show placeholder)
4. **Edelweiss**: `edelweisslife.in` → should automatically try `www.edelweisslife.in` ✅

## Benefits

- ✅ **Automatic www/non-www fallback**
- ✅ **Always uses HTTPS protocol**
- ✅ **Graceful degradation** (placeholder → hide)
- ✅ **No broken images**
- ✅ **No manual URL fixes needed**
- ✅ **Better UX** - users see something instead of broken icons

## Example: Edelweiss Case

**Before:**
- Stored URL: `edelweisslife.in`
- Result: ❌ Broken favicon (domain doesn't resolve)

**After:**
1. Tries: `edelweisslife.in` → fails
2. Tries: `www.edelweisslife.in` → ✅ **works!**
3. Favicon loads successfully

No database update needed!
