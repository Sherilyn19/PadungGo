# Hackathon submission: video plan and checklist

Cebu Hacktoberfest 2026. Submission is due **October 23, 2026, 11:59 PM (Asia/Manila)**: the public GitHub repository plus a **1-minute video showing how PadungGo is used**, with no pitching. In-person attendance is on **October 25, 2026**.

## 60-second usage video

**Before recording:**
- Open https://padunggo-api.onrender.com/health about two minutes beforehand. The free API host sleeps when idle and takes about a minute to wake.
- Rehearse the journey once and record the same request. Use **Ayala Center Cebu → Colon Obelisk** (direct, five alternatives) and its return **Colon Obelisk → Ayala Center Cebu**, checked on the live API on October 24, 2026. Both gave a working AI explanation. Route codes change with the data (that day: 13C, 64C, 62B, 65B, 13B outbound; 17C, 04I, 04C, 62B, 65B back), so run the search once on the recording day and confirm it still gives direct options. The older 17D → 42D journey ([DEMO_JOURNEY_17D_42D.md](DEMO_JOURNEY_17D_42D.md)) no longer works because 42D is excluded.
- Use a clean browser window at a phone-like width or full desktop, and keep the same one throughout.

| Time | Show | On-screen action / caption |
|---|---|---|
| 0:00–0:05 | Home screen at https://padung-go.app | Caption: "PadungGo: jeepney journeys in Metro Cebu" |
| 0:05–0:15 | Choose the start | Type a place name and pick a suggestion, or tap the map. You can show that typing "osmeña" finds "Fuente Osmena". |
| 0:15–0:22 | Choose the destination and search | Pick the destination and press Search. The loading placeholders appear. |
| 0:22–0:35 | Results list | Show the options (direct or one transfer), route codes, the "Historic data · not field-verified" label and the Unknown fare or wait |
| 0:35–0:43 | Open one option | Scroll through the numbered steps (walk, board, transfer, get off) and point out the ride line on the map |
| 0:43–0:53 | **Explain this trip** (only if verified live, see below) | Press the button once. Show the loading state, then the text with its **AI-generated** label and the "Before you go" notes. |
| 0:53–0:56 | Return trip | Optional: swap to show the independent return result or its honest empty state. Drop this row first if time runs short. |
| 0:56–1:00 | End card | Repository URL, nothing else |

**Do not show or say:**
- that a route currently runs or is frequent;
- that a fare is official;
- the AI text as a recommendation: it restates the planner's result; the planner decides the trip. If the live explanation is unavailable or has not been verified, **leave out the 0:43–0:53 step** and do not mention AI;
- that the AI knows whether a route runs, how often, or what it costs;
- admin pages, `.env` files or dashboards containing settings.

## Submission checklist

Tick items only when they are done and checked.

**Code and checks**
- [x] PRs #15–#23 merged to `main` (47cd42a). CI passed on #23.
- [ ] Production runs the latest `main`: re-check on the day of recording. On October 24, 2026 Render ran `085d8c4` (#61) and `/api/v1/health` reported `trusted_proxy_hops: 3`; later merges need the same check.

**AI explanation** (open-weight model: `openai/gpt-oss-20b`, Apache 2.0, via GroqCloud)
- [x] `AI_API_KEY`, `AI_BASE_URL` and `AI_MODEL` are set on Render (shown by working explanations; the key is not in the repository or any `VITE_*` variable).
- [x] Render runs a commit with `/api/v1/journeys/explain`.
- [x] Real explanations from `openai/gpt-oss-20b`, October 24, 2026, called on the live API (`padunggo-api.onrender.com`): 04D + 10O, 17D + 10M and 04D + 10M (one transfer); Ayala Center Cebu → Colon Obelisk (13C), → Fuente Osmena (17C), and the two return trips. Each was labelled AI-generated with the server notices. Four early attempts failed the accuracy checks and were fixed in #53, #56, #57 and #58.
- [ ] **Owner:** press **Explain this trip** once in the browser on https://padung-go.app and confirm the text, the AI-generated label and the "Before you go" box appear. The API calls above were not made through the website.
- [ ] After #62 is merged, repeat one explanation and confirm it never says a route is "not scarce" (before #62 it did on two of four trips).
- [ ] The itinerary still works with the key removed (the button reports "unavailable").
- [ ] The model is still `openai/gpt-oss-20b` on Groq's model list and the Hugging Face card still says Apache 2.0 (re-check on the submission day).
- [ ] The README, this file and the video do not claim more than was verified above.

**Rate limiting** (protects the Geoapify and AI daily quotas)
- [x] Verified in production on October 24, 2026 with empty requests that use no provider quota: 60 allowed, then HTTP 429 with `Retry-After`; rotating fake `X-Forwarded-For` entries did not escape the limit; allowed again 65 seconds later. Cause and fix: #59, #60, #61 (Render sends three addresses per request, the visitor is the third from the right).
- [ ] Not verified live: two different real visitors having separate limits (only one test address was available); covered by unit tests and a two-worker gunicorn run.

**Credentials and privacy** (before making the repository public)
- [ ] Credential review finished, covering history, merge-resolution content, PR comments and CI logs. No credentials have been found so far; see the review notes in the PR.
- [ ] Right after making the repository public, turn on GitHub **Secret scanning** and **Push protection**, then check that the alerts list is empty.
- [ ] Decide whether a personal author email may appear in public commit history. Future commits can use GitHub's private noreply email.

**Data and licensing**
- [ ] The route-data source and its terms are stated honestly: Cebu DOTC GTFS via Transitland, licence not yet established. The app footer and README already name the source. The repository does not contain the feed file.
- [x] MIT licence is in place for original code and docs.

**Repository and submission**
- [ ] Repository made **public**; open it in a private window to confirm judges can see it.
- [ ] Video recorded (≤ 60 s, usage only), uploaded, and its link tested while logged out.
- [ ] Submission form sent with the repository URL and video link before **Oct 23, 11:59 PM**.
- [ ] Attend in person on **Oct 25**.
