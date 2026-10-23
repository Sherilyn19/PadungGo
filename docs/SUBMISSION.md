# Hackathon submission: video plan and checklist

Cebu Hacktoberfest 2026. Submission is due **October 23, 2026, 11:59 PM (Asia/Manila)**: the public GitHub repository plus a **1-minute video showing how PadungGo is used**, with no pitching. In-person attendance is on **October 25, 2026**.

## 60-second usage video

**Before recording:**
- Open https://padunggo-api.onrender.com/health about two minutes beforehand. The free API host sleeps when idle and takes about a minute to wake.
- Rehearse the journey once and record the same request. Use the 17D → 42D demo journey ([DEMO_JOURNEY_17D_42D.md](DEMO_JOURNEY_17D_42D.md)) or another request you have checked live.
- Use a clean browser window at a phone-like width or full desktop, and keep the same one throughout.

| Time | Show | On-screen action / caption |
|---|---|---|
| 0:00–0:05 | Home screen at https://padung-go.vercel.app | Caption: "PadungGo: jeepney journeys in Metro Cebu" |
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
- [ ] Production runs the latest `main`: the Render deploy shows commit 47cd42a or later, the Vercel deploy shows the latest frontend, and one live search works.

**AI explanation** (open-weight model: `openai/gpt-oss-20b`, Apache 2.0, via GroqCloud)
- [ ] `AI_API_KEY` is set in the Render dashboard (never in the repository, `render.yaml` or a `VITE_*` variable). `AI_BASE_URL` and `AI_MODEL` match `render.yaml`.
- [ ] Render runs a commit that includes `/api/v1/journeys/explain`, and the Vercel frontend is the matching build.
- [ ] On https://padung-go.vercel.app, one real explanation is produced for a live trip, labelled AI-generated, with the notices shown. Record the date and trip here: _not yet verified_.
- [ ] The itinerary still works with the key removed (the button reports "unavailable").
- [ ] The model is still `openai/gpt-oss-20b` on Groq's model list and the Hugging Face card still says Apache 2.0 (re-check on the submission day).
- [ ] The README, this file and the video do not claim more than was verified above.

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
