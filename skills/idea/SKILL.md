---
name: idea
description: Surveys a codebase and proposes one meaningful improvement theme plus 2-4 concrete small wins under it, grounded in real code the skill actually read. Built to be run repeatedly for continuous improvement, so each run deliberately picks a fresh angle instead of repeating itself. Use whenever the user asks for an idea to improve the codebase, what could be better, where to invest next, a continuous-improvement suggestion, or runs `/idea` — even if they don't say the word "idea" (e.g. "what would you improve here", "give me something to work on", "where's the low-hanging fruit"). Proposes only; never implements. Not for debugging a specific error (use a debugging skill), reviewing a specific diff/PR (use a review skill), or building a feature the user already decided on.
---

# idea

Look at a codebase and propose **one meaningful improvement theme** plus **2-4 concrete small wins** that ladder up to it. Every idea must be anchored to code you actually read — file paths, function names, real observations. This skill proposes; it never implements.

The whole point is continuous improvement: this gets run again and again. So your job each run is not just "an idea" but a *fresh* idea — one the codebase would genuinely benefit from now, that you haven't obviously just suggested or that hasn't just been done.

## What makes this hard (read before starting)

Two failure modes kill this skill. Avoid both.

1. **Generic advice.** "Add more tests", "improve error handling", "consider TypeScript", "add documentation" — these are worthless because they apply to every codebase and point at nothing. An idea is only meaningful if a reader can see the exact code that motivated it. If you can't name the file and the specific thing you saw, you haven't earned the suggestion. Delete it.

2. **Repetition across runs.** Because this runs repeatedly, the lazy outcome is proposing the same theme every time. Use git history and any prior-ideas the user points you at to steer *away* from recently-touched or already-suggested areas, and deliberately rotate which dimension you examine (see step 3).

## Process

### 1. Scope the run

- Target is the current repo / working directory unless the user names a path.
- If the user named a focus area ("something about the test suite", "DX ideas", "the parser"), honor it — scope your survey there.
- If the user pointed at a file of past ideas (e.g. `/idea ideas.md`), read it first and treat everything in it as off-limits — your job is to find what's *not* already on that list.
- Output goes to the conversation by default. Only write to a file if the user asked you to, and write where they said.

### 2. Survey the codebase

Build a real mental model — don't skim. Look at:

- **Shape**: directory layout, languages, entry points, the README/docs if present, how the thing is built and run.
- **The core**: open the files that actually carry the load (the main module, the hot path, the biggest files, the most-imported module). Read them, don't just `ls`.
- **Recent momentum**: `git log --oneline -30` and `git log --stat -5`. This tells you what the maintainers care about right now and — critically — what was *just done* so you don't propose it back to them.
- **Friction signals**: TODO/FIXME/HACK comments, duplicated blocks, a test dir that's thin relative to the code, config sprawl, long functions, commented-out code, inconsistent patterns between modules.

For a large or unfamiliar repo, spawn an Explore agent to map it rather than burning the main context — but you must still read the specific files your ideas rest on yourself.

### 3. Pick a fresh angle

Before forming the theme, choose which dimension to look through this run. Rotating the lens is what keeps repeated runs valuable. Candidate lenses:

- **Architecture & boundaries** — coupling, a module doing too much, a missing seam.
- **Developer experience** — setup friction, slow feedback loop, confusing entry points, missing scripts.
- **Testing & confidence** — an untested critical path (name it), brittle tests, no way to reproduce a class of bug.
- **Consistency** — two parts of the codebase solving the same problem differently.
- **Performance** — a concrete hot path doing obviously redundant work.
- **Robustness** — a real failure mode in real code (not hypothetical).
- **Maintainability** — a sharp edge that will keep costing time.

Steer toward what the codebase actually needs and away from whatever was just worked on (per git history) or already proposed (per any prior-ideas file). If nothing in a lens is grounded in real observed code, drop that lens — don't manufacture a problem to fit it.

### 4. Form the theme

State one improvement theme: what it is, why it matters *for this codebase specifically* (cite the evidence you found), and what better looks like. A good theme is a direction worth a few sessions of work, not a one-liner and not a vague aspiration. Be honest about cost vs. payoff — if it's a big lift, say so.

### 5. Find the small wins

Under that theme, identify 2-4 concrete, low-risk improvements that each:

- point at a specific file (and line/function where you can),
- could realistically land in a single small change,
- move the codebase a step toward the theme.

These are the "do it this afternoon" items that make the big theme tractable. They should feel like obvious next steps, not a rewrite.

### 6. Present

Use this structure:

```
## Theme: <short title>

<2-4 sentences: what, why it matters here, what better looks like.
Cite the specific evidence — files, patterns, what you saw.>

**Cost/payoff:** <one honest line>

### Small wins
- **<title>** — `path/to/file.ext:line` — <what to change and the concrete benefit>
- **<title>** — `path/to/file.ext` — <...>
- ...
```

The small wins are an unordered set, not a plan — don't rank them, sequence them, or tag one as the place to start.

Then, optionally, one closing line that *describes* the angle you took this run and any angle you deliberately left unexplored. Keep it observational ("this run looked at robustness; the engine's size is untouched"), not directive — it orients the next run without telling anyone what to do.

## Behavior notes

- **Propose only.** Never edit code, never start implementing. If the user likes an idea and says "do it", that's a separate task with a different skill — hand off, don't silently begin.
- **Outline, don't prescribe.** Present the theme and the small wins and stop. No recommended order, no priority ranking, no "do this first", no "suggested scope" or "minimal first pass", no "what I'd do next". Deciding what to act on and in what sequence is the user's call, not yours — your job is to surface the idea clearly enough that they can make that call.
- **Evidence or it's cut.** If an idea isn't tied to code you actually read, it doesn't ship. Quality over quantity: one well-grounded small win beats four generic ones.
- **Don't invent problems.** If the codebase is genuinely clean in the dimension you picked, switch lenses or say so plainly. A forced suggestion is worse than an honest "this area is solid; the real opportunity is over here."
- **Stay terse.** This is a working note for the user, not an essay. No throat-clearing, no restating the obvious about what the project is.
