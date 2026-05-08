# CLI Report Template Design Audit

## Design Characteristics to Incorporate into Web App

### 1. Color Palette
- **Primary Gradient**: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Primary Color**: `#667eea` (purple-blue)
- **Secondary Color**: `#764ba2` (purple)
- **Success**: `#d4edda` (light green for selected)
- **Warning**: `#fff3cd` (light yellow for highlighted)
- **Hover**: `#f0f0f0` (light gray)
- **Text Muted**: `#6c757d`
- **Background**: `#f8f9fa`

### 2. Spacing Scale (Design System)
- **xs**: 4px
- **sm**: 8px
- **md**: 16px
- **lg**: 24px
- **xl**: 32px

Applied consistently:
- Container padding: 16px (md)
- Header padding: 24px (lg)
- Card margin-bottom: 12px
- Card body padding: 16px (md)
- Table cell padding: 8px 12px (sm vertical, optimized horizontal)

### 3. Typography
- **Font Family**: Arial, sans-serif
- **Metric Value**: 2em, bold, color #667eea
- **Metric Label**: 0.9em, color #6c757d
- **Nav Tabs**: font-weight 500

### 4. Border Radius
- **Standard**: 10px (cards, header, map-container)
- **Small**: 6px (activity items)
- **Button Groups**: 5px (first/last child)

### 5. Shadows
- **Card**: `0 2px 4px rgba(0,0,0,0.1)`
- **Button Group**: `0 2px 4px rgba(0,0,0,0.1)`
- **Modal**: `0 10px 40px rgba(0,0,0,0.3)`

### 6. Transitions
- **Route Row**: `all 0.2s ease`
- **Route Name Link**: `color 0.2s`
- **Uses Count**: `color 0.2s`

### 7. Interactive States
- **Route Row Hover**: background #f0f0f0
- **Route Row Selected**: background #d4edda, font-weight bold
- **Route Row Highlighted**: background #fff3cd
- **Link Hover**: color #764ba2, underline

### 8. Table Sorting
- **Sortable Headers**: cursor pointer, user-select none, padding-right 20px
- **Sort Indicator**: position absolute, right 8px, opacity 0.3
- **Sort Icons**: ⇅ (default), ↑ (asc), ↓ (desc)
- **Hover**: background #f0f0f0

### 9. Loading States
- **Spinner**: 20px, border 3px, color #667eea with 0.3 opacity
- **Animation**: spin 1s ease-in-out infinite
- **Overlay**: rgba(255, 255, 255, 0.9)

### 10. Modal Design
- **Backdrop**: rgba(0,0,0,0.5), z-index 9998
- **Modal**: max-width 800px, width 90%, max-height 80vh
- **Header**: padding 20px, border-bottom 1px solid #dee2e6
- **Body**: padding 20px, max-height 60vh, overflow-y auto
- **Close Button**: font-size 24px, color #6c757d, hover #000

### 11. Map Container
- **Height**: 600px (reduced from 800px)
- **Position**: sticky, top 20px
- **Border Radius**: 10px
- **Overflow**: hidden

### 12. Comparison Section Layout
- **Display**: flex
- **Gap**: 20px
- **Table**: flex 1
- **Map Pane**: flex 1, min-width 500px

### 13. Pagination Controls
- **Margin**: 8px 0 (sm)
- **Display**: flex, justify-content space-between
- **Button Margin**: 0 5px
- **Page Info**: color #6c757d

### 14. Direction Filter
- **Margin Bottom**: 12px
- **Button Group**: box-shadow, rounded corners on first/last

### 15. Tooltips & Help
- **Cursor**: help
- **Border Bottom**: 1px dotted #667eea
- **Score Link**: cursor pointer, color #667eea, underline

## Missing from Web App

### Critical
1. ❌ Primary gradient header (linear-gradient)
2. ❌ Consistent spacing scale (xs/sm/md/lg/xl)
3. ❌ Table sorting with visual indicators
4. ❌ Loading spinner with overlay
5. ❌ Modal design for activity details
6. ❌ Sticky map positioning
7. ❌ Min-width constraint on map pane (500px)

### Important
8. ❌ Metric cards with large values
9. ❌ Direction filter button group
10. ❌ Pagination controls styling
11. ❌ Tooltip styling with dotted underline
12. ❌ Activity item cards in modals
13. ❌ Consistent border radius (10px)
14. ❌ Consistent shadows

### Nice-to-Have
15. ❌ Coming soon placeholder styling
16. ❌ Nav tabs active state styling
17. ❌ Route name link hover effects

## Action Items

1. Update `static/css/main.css` with CLI design system
2. Add missing interactive states
3. Implement table sorting UI
4. Add loading states and spinners
5. Create modal component styles
6. Update dashboard.html with gradient header
7. Add metric cards with proper styling
8. Implement sticky map positioning
9. Add pagination controls
10. Create direction filter component