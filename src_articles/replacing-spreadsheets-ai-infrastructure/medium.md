---
title: "What replacing four spreadsheets actually took"
subtitle: "Building a company's AI infrastructure from zero means the hard part was never the model. It was registration, retention, and who's allowed to see what."
date: 2026-10-14
author: "Yeriko Vargas"
tags: ["Systems", "RAG", "Agents"]
canonical_url: "https://customaimodels.com/articles/replacing-spreadsheets-ai-infrastructure/"
---

# What replacing four spreadsheets actually took

When a distribution company asked me to build a training hub and assistant, the request sounded like one project: "give us an AI tool for training." What actually existed underneath that request was 4 separate spreadsheets, a paper sign-up process, and no single place that knew who had attended what, who was certified, or what the company's own policies actually said when someone asked. The AI assistant was the last thing I built. It was also the smallest part of the work.

## Enterprise data silos: the model is not the bottleneck

Every company I've worked with that wanted "an AI tool" already had a reasonably good sense of what they wanted a model to say. What they didn't have was one trustworthy place for the model to say it from. 4 spreadsheets fail in 4 predictable ways:

- **4 sources of truth.** Which in practice means 0 sources of truth.

- **Always slightly out of date.** Each one is updated on its own schedule, by hand.

- **4 owners.** Each sheet is maintained by a different person, with a different idea of what a column means.

- **Contradictions by default.** By the time anyone needs an answer, at least one sheet disagrees with the others.

So before anything resembling retrieval or an assistant got built, the actual first job was data infrastructure and data pipeline ingestion: 1 registration system, 1 attendance record, 1 retention record, 1 place the role-based access rules live. Natural-language access to business data only works if the data underneath it is actually unified. Point a well-built RAG system at 4 contradicting spreadsheets and you've built a very articulate way to be wrong.

## Replacing a paper process is a trust problem, not a technical one

The paper sign-up process wasn't slow because paper is slow. It was trusted because everyone could see it, and because nobody had to wonder whether a system was quietly deciding who counted as "trained" and who didn't. Replacing it meant the new system had to be more legible than the thing it replaced, not just faster. That shaped real decisions: what the assistant is allowed to say with certainty versus what it should hand off to a person, what gets logged, and where a human can always see the underlying record a given answer came from.

## A system nobody trusts gets routed around, quietly, until it's just an expensive dashboard nobody opens. Owning the data pipeline end to end: fewer handoffs, fewer seams

As the sole architect, with 1 person accountable for every layer instead of 5, I didn't have the option of treating this as "build the model, hand off the integration." Registration, training delivery, attendance, retention, and natural-language access to all of it are 1 system, not 5 handoffs between 5 teams, and the seams between those pieces are exactly where most AI projects I've seen elsewhere quietly fail. Owning the whole thing meant the data model, the access rules, and the assistant were designed together, from the start, instead of a model bolted onto whatever data happened to exist.

That's also why it's still running, and still mine. A system designed as 5 separate handoffs tends to need 5 separate people to keep it alive. One designed as a single system, by the person who understands every layer of it, doesn't.

## What actually mattered, in order

- **One data model.** Registration, attendance, retention, and access as 1 structure, not 4 spreadsheets reconciled by hand.

- **Legible rules.** Who can see what, and why, written down and enforced the same way every time, not a judgment call buried in someone's head.

- **The assistant last.** Natural-language access to business data is the payoff of unified data, not a substitute for it.

---

*Originally published at [customaimodels.com](https://customaimodels.com/articles/replacing-spreadsheets-ai-infrastructure/).*
