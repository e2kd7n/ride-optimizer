# GitHub Issue: First-Time User Experience (FTUE) - Strava API Setup

**Title:** Implement guided FTUE for Strava API key setup with in-app configuration

**Labels:** `P1-high`, `enhancement`, `UX`, `onboarding`, `design-needed`

**Epic:** User Onboarding & Setup

---

## Problem Statement

New users face a significant barrier to entry when setting up Ride Optimizer:
1. They must manually create a Strava API application
2. They need to understand OAuth concepts and callback URLs
3. They must manually edit `.env` files or use command-line tools
4. There's no guidance or validation during setup
5. Errors are cryptic and don't guide users to solutions

**Current friction points:**
- No in-app setup flow
- Requires technical knowledge (environment variables, OAuth)
- No visual feedback or progress indicators
- Users can't verify their setup worked until they try to use the app

---

## Proposed Solution

Create a delightful, guided First-Time User Experience (FTUE) that:
1. **Detects** when the app is unconfigured (missing or invalid API keys)
2. **Guides** users through Strava API application creation with clear instructions
3. **Collects** API credentials directly in the UI (no file editing required)
4. **Validates** credentials in real-time with helpful error messages
5. **Celebrates** successful setup and guides users to their first action

---

## User Flow

### 1. Detection & Welcome Screen
**Trigger:** User visits app for first time (no valid credentials in `.env`)

**Screen:** Welcome Modal (full-screen overlay, cannot be dismissed)
```
┌─────────────────────────────────────────────────────────┐
│  🚴 Welcome to Ride Optimizer!                          │
│                                                          │
│  To get started, we need to connect to your Strava      │
│  account. This will take about 2 minutes.               │
│                                                          │
│  [Get Started] ──────────────────────────────────────>  │
│                                                          │
│  Already have API keys? [Enter them manually]           │
└─────────────────────────────────────────────────────────┘
```

### 2. Step-by-Step Guide
**Progress Indicator:** "Step 1 of 4" with visual progress bar

#### Step 1: Create Strava API Application
```
┌─────────────────────────────────────────────────────────┐
│  Step 1 of 4: Create Your Strava API Application        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  1. Click the button below to open Strava's API page    │
│     in a new tab                                         │
│                                                          │
│  [Open Strava API Settings] 🔗                          │
│                                                          │
│  2. Log in to your Strava account if prompted           │
│                                                          │
│  3. Click "Create an App" or "My API Application"       │
│                                                          │
│  ℹ️  Keep this window open - you'll need to copy        │
│     information from Strava in the next step            │
│                                                          │
│  [Back]                              [Next Step] ──────> │
└─────────────────────────────────────────────────────────┘
```

#### Step 2: Fill Out Strava Form
```
┌─────────────────────────────────────────────────────────┐
│  Step 2 of 4: Fill Out the Strava Application Form      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  Fill out the form on Strava with these values:         │
│                                                          │
│  📝 Application Name:                                    │
│     Ride Optimizer (Personal)                           │
│                                                          │
│  📝 Category:                                            │
│     Other                                               │
│                                                          │
│  📝 Website:                                             │
│     http://localhost:8083                               │
│     [Copy to Clipboard] 📋                              │
│                                                          │
│  📝 Authorization Callback Domain:                       │
│     localhost                                           │
│     [Copy to Clipboard] 📋                              │
│                                                          │
│  ⚠️  Important: Use these exact values for local setup  │
│                                                          │
│  [Back]                              [Next Step] ──────> │
└─────────────────────────────────────────────────────────┘
```

#### Step 3: Copy Your API Credentials
```
┌─────────────────────────────────────────────────────────┐
│  Step 3 of 4: Copy Your API Credentials                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  After creating your app, Strava will show you two      │
│  important values. Copy them here:                       │
│                                                          │
│  Client ID:                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [Paste your Client ID here]                     │   │
│  └─────────────────────────────────────────────────┘   │
│  ✓ Looks good! (12345)                                  │
│                                                          │
│  Client Secret:                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [Paste your Client Secret here]                 │   │
│  └─────────────────────────────────────────────────┘   │
│  ⚠️  Keep this secret! Never share it publicly          │
│                                                          │
│  [Show/Hide Secret] 👁️                                  │
│                                                          │
│  [Back]                              [Verify & Save] ──> │
└─────────────────────────────────────────────────────────┘
```

#### Step 4: Verify & Authorize
```
┌─────────────────────────────────────────────────────────┐
│  Step 4 of 4: Authorize Ride Optimizer                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  ⏳ Verifying your credentials...                        │
│                                                          │
│  ✓ Client ID verified                                   │
│  ✓ Client Secret verified                               │
│  ✓ Credentials saved securely                           │
│                                                          │
│  Now we need your permission to access your Strava      │
│  data. Click below to authorize:                         │
│                                                          │
│  [Authorize with Strava] 🔐                             │
│                                                          │
│  This will open Strava in a new window. After you       │
│  approve, you'll be redirected back here.                │
│                                                          │
│  [Back]                                                  │
└─────────────────────────────────────────────────────────┘
```

### 3. Success & Next Steps
```
┌─────────────────────────────────────────────────────────┐
│  🎉 You're All Set!                                      │
│                                                          │
│  Ride Optimizer is now connected to your Strava         │
│  account. Here's what happens next:                      │
│                                                          │
│  1. ⏳ Fetching your activities (this may take a minute) │
│  2. 🗺️  Analyzing your routes                            │
│  3. 🌤️  Getting weather data                             │
│                                                          │
│  [View Dashboard] ──────────────────────────────────────>│
│                                                          │
│  💡 Tip: The first analysis takes longer. Subsequent     │
│     updates will be much faster!                         │
└─────────────────────────────────────────────────────────┘
```

---

## Technical Requirements

### Backend Changes

1. **New API Endpoint: `/api/setup/credentials`**
   - POST: Save Client ID and Client Secret
   - Validates format (numeric ID, alphanumeric secret)
   - Writes to `.env` file securely (or encrypted config)
   - Returns validation status

2. **New API Endpoint: `/api/setup/status`**
   - GET: Check if credentials are configured
   - Returns: `{ configured: boolean, valid: boolean, error?: string }`

3. **New API Endpoint: `/api/setup/verify`**
   - POST: Test credentials by making a test API call to Strava
   - Returns: `{ valid: boolean, error?: string, athlete_name?: string }`

4. **Enhanced OAuth Flow**
   - Detect first-time setup vs. re-authorization
   - Handle OAuth callback with better error messages
   - Store tokens securely after successful auth

### Frontend Changes

1. **New Component: `SetupWizard.vue` (or React/vanilla JS)**
   - Multi-step wizard with progress indicator
   - Form validation with real-time feedback
   - Copy-to-clipboard functionality
   - Show/hide password toggle for Client Secret
   - Loading states and error handling

2. **New Page: `/setup` or modal overlay**
   - Full-screen takeover for FTUE
   - Cannot be dismissed until setup is complete
   - Responsive design (mobile-friendly)

3. **Settings Integration**
   - Add "Re-configure Strava Connection" button in Settings
   - Allow users to update credentials without full FTUE

### Security Considerations

1. **Credential Storage**
   - Store in encrypted format (use existing encryption from `src/auth_secure.py`)
   - Never expose Client Secret in API responses
   - Use HTTPS in production (document in deployment guide)

2. **Validation**
   - Sanitize all user inputs
   - Validate Client ID format (numeric, 5-6 digits)
   - Validate Client Secret format (alphanumeric, 40 chars)
   - Rate limit setup endpoints to prevent abuse

3. **Error Handling**
   - Never expose internal errors to users
   - Provide actionable error messages
   - Log detailed errors server-side for debugging

---

## Design Requirements

### Visual Design
- **Color Scheme:** Use existing Ride Optimizer brand colors
  - Primary: `#007bff` (blue)
  - Success: `#28a745` (green)
  - Warning: `#ffc107` (yellow)
  - Danger: `#dc3545` (red)

- **Typography:** Use existing font stack
  - Headers: 600 weight
  - Body: 400 weight
  - Minimum 16px for inputs (prevent iOS zoom)

- **Spacing:** Generous whitespace for clarity
  - 2rem between major sections
  - 1rem between form fields
  - 0.5rem for inline elements

### Interaction Design
- **Progress Indicator:** Always visible, shows current step
- **Navigation:** Back button on all steps except first
- **Validation:** Real-time feedback (green checkmark, red X)
- **Loading States:** Spinner with descriptive text
- **Animations:** Smooth transitions between steps (300ms ease)

### Accessibility
- **WCAG 2.1 AA Compliance:**
  - All interactive elements have 44x44px touch targets
  - Color contrast ratio ≥ 4.5:1 for text
  - Keyboard navigation support (Tab, Enter, Escape)
  - Screen reader announcements for state changes
  - Focus indicators (3px outline)

- **ARIA Labels:**
  - `role="dialog"` for modal
  - `aria-labelledby` for step titles
  - `aria-describedby` for instructions
  - `aria-live="polite"` for validation messages

### Mobile Optimization
- **Responsive Breakpoints:**
  - Mobile: < 768px (single column, larger touch targets)
  - Tablet: 768px - 1024px (optimized layout)
  - Desktop: > 1024px (full wizard width)

- **Mobile-Specific:**
  - Bottom sheet for modals on mobile
  - Larger input fields (48px height)
  - Sticky progress bar at top
  - Swipe gestures for navigation (optional)

---

## Acceptance Criteria

### Functional Requirements
- [ ] Setup wizard appears automatically on first launch (no valid credentials)
- [ ] All 4 steps are clearly labeled and navigable
- [ ] External links open in new tabs with proper `rel` attributes
- [ ] Copy-to-clipboard buttons work on all browsers
- [ ] Client ID and Client Secret are validated before saving
- [ ] Credentials are saved securely (encrypted)
- [ ] OAuth flow completes successfully after credential entry
- [ ] Success screen shows and redirects to dashboard
- [ ] Users can re-run setup from Settings page
- [ ] Setup can be completed entirely from mobile device

### Non-Functional Requirements
- [ ] Setup wizard loads in < 1 second
- [ ] Credential validation completes in < 2 seconds
- [ ] OAuth redirect completes in < 5 seconds
- [ ] All interactions have loading states
- [ ] Error messages are clear and actionable
- [ ] No console errors or warnings
- [ ] Works in Chrome, Firefox, Safari, Edge (latest versions)
- [ ] Works on iOS Safari and Android Chrome

### Design Requirements
- [ ] Matches existing Ride Optimizer design system
- [ ] All text is legible (contrast, size)
- [ ] Touch targets are ≥ 44x44px
- [ ] Animations are smooth (60fps)
- [ ] Loading states are clear and informative
- [ ] Success state is celebratory and encouraging

### Security Requirements
- [ ] Client Secret is never exposed in API responses
- [ ] Credentials are stored encrypted
- [ ] Setup endpoints are rate-limited
- [ ] All inputs are sanitized
- [ ] HTTPS enforced in production
- [ ] No sensitive data in browser console or network tab

---

## Implementation Plan

### Phase 1: Backend API (2-3 days)
1. Create `/api/setup/*` endpoints
2. Implement credential validation logic
3. Add secure credential storage
4. Enhance OAuth flow for FTUE
5. Write unit tests for all endpoints

### Phase 2: Frontend Wizard (3-4 days)
1. Create SetupWizard component structure
2. Implement step navigation and progress indicator
3. Build form validation and error handling
4. Add copy-to-clipboard functionality
5. Integrate with backend APIs
6. Add loading states and animations

### Phase 3: Design Polish (1-2 days)
1. Apply design system styles
2. Add micro-interactions and animations
3. Optimize for mobile devices
4. Accessibility audit and fixes
5. Cross-browser testing

### Phase 4: Testing & Documentation (1-2 days)
1. End-to-end testing of full flow
2. User acceptance testing
3. Update README with FTUE screenshots
4. Create troubleshooting guide
5. Document API endpoints

**Total Estimated Time:** 7-11 days (1.5-2 weeks)

---

## Success Metrics

### Quantitative
- **Setup Completion Rate:** > 90% of users complete setup
- **Time to First Value:** < 5 minutes from landing to dashboard
- **Error Rate:** < 5% of setup attempts fail
- **Support Tickets:** < 10% of users need help with setup

### Qualitative
- Users report setup was "easy" or "very easy" (survey)
- No confusion about what to do next (user testing)
- Users feel confident their data is secure
- Setup feels professional and polished

---

## Future Enhancements (Out of Scope)

- **Social OAuth:** "Sign in with Strava" button (no manual API key entry)
- **Guided Tour:** Interactive tutorial after setup
- **Setup Video:** Embedded video walkthrough
- **Multi-User Support:** Allow multiple Strava accounts
- **Cloud Sync:** Store credentials in cloud for multi-device access
- **Setup Analytics:** Track where users drop off in funnel

---

## Related Issues
- #XXX - Improve error messages for authentication failures
- #XXX - Add Settings page for credential management
- #XXX - Document Strava API setup in README

---

## References
- [Strava API Documentation](https://developers.strava.com/docs/getting-started/)
- [OAuth 2.0 Best Practices](https://oauth.net/2/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Material Design - Onboarding](https://material.io/design/communication/onboarding.html)

---

**Priority:** P1-high (blocks new user adoption)  
**Effort:** Large (7-11 days)  
**Impact:** High (removes biggest barrier to entry)  
**Risk:** Low (well-defined scope, existing patterns)

**Assigned To:** Design Team (for mockups) → Engineering Team (for implementation)