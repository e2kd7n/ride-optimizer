# Engineer B Review: Product, UX, and Cyclist Workflow

**Reviewer Role:** Senior product-minded engineer and cyclist focused on decision quality, interaction design, ride planning workflows, and feature usefulness  
**Review Target:** [`docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md`](docs/PERSONAL_WEB_PLATFORM_PROPOSAL.md)  
**Date:** 2026-05-06

---

## Executive Summary

This proposal is compelling because it is not trying to become Strava, Komoot, or a generic ride planner. It is trying to become the rider’s best personal decision tool. That is exactly the right framing.

From a cyclist’s perspective, the document is strongest when it does the following:
- helps answer “what should I ride today?”
- explains why a recommendation is good
- adapts to practical constraints like weather, time, surface, and workouts
- works well from a phone without feeling like a reduced desktop app

I support the proposal overall, including its ambitious v1. My main recommendation is to sharpen the user journeys and make sure every major feature feels like part of the same decision loop rather than a set of adjacent tools.

---

## What the Proposal Gets Right

### 1. The Product Thesis Is Strong
The three key questions are excellent:
- best commute in the next 24 hours
- best ride today given intent and conditions
- how commute advice changes when a TrainerRoad workout needs to fit outdoors

That set of questions is differentiated, practical, and personal.

### 2. TrainerRoad Integration Is a Legitimately Useful Feature
This is not gimmicky. For riders who sometimes take structured workouts outside, the hardest thing is often not the workout itself but figuring out:
- whether the commute is long enough
- whether to extend the ride
- whether to shift departure time
- whether weather makes the outdoor version a poor choice

This is exactly the kind of value a personal platform should provide.

### 3. The Proposal Understands the Importance of Explainability
Cyclists do not just want rankings. They want tradeoffs:
- faster vs calmer
- drier vs longer
- flatter vs more efficient
- familiar vs better for today’s wind
- enough volume for the workout vs too short

The proposal is right to make explanation part of the product.

---

## Main Product Concerns

### 1. The Proposal Blurs Three Different Planner Concepts
Right now the document gestures toward:
- choosing from historically proven rides
- finding route variants near a start location
- discovering entirely new routes

These should be separated clearly in the product language. A rider understands the differences immediately:
- “show me rides I already know”
- “show me close cousins of rides I know”
- “invent something new for me”

Those are very different trust levels. The app should not overpromise on the third unless it can deliver it with confidence.

### 2. The Dashboard Needs More Than Status
The proposal’s dashboard includes system freshness and access to flows, which is good. But to feel like a daily-use product, the dashboard should immediately answer:
- what should I ride right now?
- do I need to leave earlier or later?
- is my commute enough for today’s workout?
- if not, what is the best extension?

The dashboard should surface recommendations, not just navigation.

### 3. The Commute Flow Needs “Decision Outcome” Language
A useful commute page should not merely present options; it should present a call:
- **Best route**
- **Why it wins**
- **What you give up**
- **Whether it fits today’s workout**
- **What to change if it does not**

That framing makes the app feel decisive and practical.

### 4. The Long Ride Planner Needs Better Trust Framing
If the planner recommends rides from your history, it should say so. If it recommends near-neighbor rides, it should say so. If it suggests something more speculative, that should also be explicit.

I recommend labels like:
- **Proven ride**
- **Strong historical match**
- **Variant of known route**
- **Experimental suggestion**

That creates product honesty and reduces disappointment.

---

## UX Recommendations

## 1. Design Around “Today Cards”
The home screen should have cards such as:
- **Today’s best commute**
- **Workout fit**
- **Best departure window**
- **Best long ride option today**
- **Repeat a favorite ride**

This lets the app feel helpful immediately.

## 2. Add Recommendation Explanation Blocks
Every major recommendation should include:
- top reason
- second-order tradeoff
- data freshness
- confidence level
- whether the suggestion is history-based or exploratory

Example:
> Best evening commute: Lakefront variant  
> Why: lowest headwind penalty and strongest historical consistency  
> Tradeoff: 6 minutes longer than the fastest option  
> Workout fit: too short for today’s 75-minute TrainerRoad session unless extended southbound

## 3. Make Workout Accommodation a First-Class UX Pattern
For TrainerRoad-aware days, the commute page should clearly state one of:
- commute alone is sufficient
- commute plus small extension is sufficient
- commute requires major extension
- indoor workout remains the better fit today

That last one is important. A good product does not force the outdoor interpretation if it is clearly inferior.

## 4. Separate Commute Recommendation and Long Ride Recommendation Emotionally
Commute mode should feel:
- practical
- confident
- fast to read

Long ride mode should feel:
- exploratory
- motivating
- comparative

The same underlying engine can support both, but the tone and interaction model should differ.

---

## Feature-Level Feedback

### Strongly Support
- route library in v1
- repeat-a-past-ride flow
- weather risk flags
- departure window suggestions
- ride intent presets
- workout-aware commute extension
- mobile-first experience

### Support with Changes
- “routes based on where people tend to ride” should be reframed unless there is a clear data source and recommendation method
- “entirely new ride routes” should be treated as exploratory and not equal to proven rides
- GPX export is useful, but not more important than trust and explanation

### Lower Priority Than It Appears
- system status detail as a prominent user-facing feature
- advanced settings depth in early v1
- broad route generation claims without proven quality

---

## Product Acceptance Criteria I Recommend

A feature should not be considered complete unless it answers the cyclist’s actual question clearly.

### Commute Recommendation
A completed commute feature should show:
- best route
- why it is best
- at least one meaningful alternative
- departure window guidance when relevant
- workout fit when TrainerRoad data exists

### Long Ride Planner
A completed planner should show:
- recommendation type
- why each result matches the request
- weather suitability
- route familiarity level
- confidence
- whether the result is realistically rideable for the desired intent

### Repeat a Past Ride
A completed repeat flow should show:
- similarity to the chosen reference ride
- what changed today
- whether a better departure window exists
- whether the route still fits the intended workout or duration

---

## Key Disagreements / Decisions for Owner

These are the main product questions that should be decided explicitly:

1. Should v1 claim true new-route discovery, or focus on high-trust historical and near-historical suggestions?
2. Should the dashboard act primarily as navigation/status, or as a recommendation-first decision surface?
3. Should workout-aware commute extension be considered part of the commute core or an advanced optional layer?
4. Should the product ever recommend “do the workout indoors” when outdoor fit is poor?

I recommend:
- recommendation-first dashboard
- workout-aware commute as core
- historical/variant suggestions in v1
- explicit permission for the system to say outdoor fit is poor

---

## Final Verdict

This is a strong proposal and potentially a genuinely differentiated personal cycling product.

My strongest recommendation is this: optimize the product for **decision confidence**, not feature count. If every major screen helps a rider confidently choose what to do next, the rest of the platform will feel coherent.