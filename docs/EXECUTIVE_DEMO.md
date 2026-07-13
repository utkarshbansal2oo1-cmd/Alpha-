# Executive Demo Guide — AlphaSource AI

Target runtime: **5 minutes**. Use **Guided Demo Mode** for the live run — it is deterministic and cannot fail. Switch to Live Pipeline mode only if a technical stakeholder specifically asks to see the real backend call.

## Opening statement (30 seconds)

> "Recruiters today spend hours searching across LinkedIn, Naukri, ATSs, and spreadsheets, manually filtering hundreds of similar profiles before they even start interviewing. AlphaSource AI replaces that with one thing: you describe the candidate you need, in plain English, and the AI understands your intent, searches intelligently, and explains exactly why each candidate is a fit. What you're about to see is the real product, not a mockup."

## Demo flow (3–3.5 minutes)

1. **(15s) Scroll past the hero.** Let the headline animation and neural network background land — don't narrate it, let it speak. Say: "This is the product experience, not a slide deck."
2. **(20s) Pause at the Problem section.** Point out that the AlphaSource chain visibly finishes before the traditional chain animates out. Say: "Every extra hop between a requirement and a hire costs you the best candidates to a faster competitor."
3. **(30s) Scroll through "How AlphaSource Thinks."** Narrate the six stages once, briefly: "Every recommendation can be traced through exactly these six steps — this isn't a black box."
4. **(90–120s) Live Product Demo — the centerpiece.**
   - Click one of the pre-loaded example queries (see below).
   - Narrate the AI Thinking sequence as it plays: "Watch — it's understanding the requirement, expanding it against our knowledge graph, building a search strategy, then searching."
   - When results land, open the **AI Understood** panel: "This is exactly what the AI extracted from that one sentence."
   - Click into one candidate card to open the **profile drawer**: "Full profile, experience timeline, education, why they matched — this is what a recruiter acts on."
5. **(20s) Enterprise Architecture section.** Hover one or two nodes: "Every one of these boxes is a real, already-built, tested module — not a diagram we drew for this meeting."
6. **(15s) Vision.** One line: "This is the MVP. Next is direct integration into AlphaRecrewt for assessments and interviews — search to hire, one continuous flow."

## Example searches (Guided Demo Mode — pick one before the meeting and rehearse it)

- "Find Backend Engineers with 5+ years, skilled in AWS and Kubernetes"
- "Product Engineers in Bangalore with strong system design experience"
- "Machine Learning engineers with production ML experience"
- "Platform engineers who have run Kubernetes at scale"

All four are deterministic — same result, same timing, every single run. Recommend rehearsing with the same one you'll use live so your narration lines up with what appears on screen.

## Talking points (have these ready, don't force all of them in)

- "This isn't keyword search — the Knowledge Engine understands that 'AWS' means EC2, Lambda, and S3, each with a weighted confidence score."
- "Every match is explainable — no black-box AI score with no reasoning behind it."
- "The AI layer is provider-agnostic by design — Gemini today, swappable to OpenAI or Claude later with no changes to the rest of the pipeline."
- "This connects directly into AlphaRecrewt for the next step: assessments and interviews."

## Architecture explanation (if asked, 30–60 seconds)

> "A recruiter's plain-English requirement goes through four stages: Query Understanding, an LLM-backed step that extracts role and skills into a validated, structured object; the Knowledge Engine, which expands each term into its real-world equivalents using a weighted taxonomy graph we built specifically for hiring; the Search Planner, which combines the literal requirement with those expansions into one executable plan; and the Candidate Repository, a single retrieval interface that today reads from a seed dataset and is built to scale to real connected sources. Every step is typed, tested — 110 automated tests — and independently swappable."

## Expected questions and suggested answers

**"Is this connected to real candidate data — LinkedIn, our ATS?"**
> "Not yet — today it runs against a seed dataset built for this demo. The retrieval layer is already built as a swappable interface specifically so we can plug in real sources next without touching the AI layer at all."

**"What happens if the AI gets it wrong?"**
> "Every result is explainable — you see exactly which skill or role matched, not a black-box score. And if the LLM call itself fails for any reason, the system returns a clear error rather than a wrong or silent result — we tested that specifically."

**"How is this different from just using ChatGPT to search LinkedIn?"**
> "ChatGPT doesn't have a hiring-specific knowledge graph, doesn't search your actual candidate sources, and doesn't produce an auditable, structured plan you can trace after the fact. This does all three, and it's built to plug directly into the hiring workflow via AlphaRecrewt."

**"What's the timeline to production?"**
> "The core pipeline — understanding, expansion, planning, retrieval — is built and tested today. What's ahead is connecting real candidate sources and the AlphaRecrewt handoff. That's a scoping conversation, not a research problem."

**"Is our data secure?"**
> "Today there's no authentication on the API — that's appropriate for an internal demo, not for production, and it's an explicit, known next step before any real deployment, not an oversight."

## Estimated timing

| Segment | Time |
|---|---|
| Opening statement | 0:30 |
| Hero + Problem section | 0:35 |
| How AlphaSource Thinks | 0:30 |
| Live Product Demo | 2:00 |
| Architecture + Vision | 0:35 |
| Buffer for one question | 0:50 |
| **Total** | **~5:00** |

If time is short, cut Architecture/Vision to a single sentence each and spend the saved time on the Live Product Demo and one Q&A — that section is what makes executives say "we need this," per the brief.
