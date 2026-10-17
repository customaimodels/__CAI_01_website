---
title: "RAG isn't a feature. It's an architecture."
subtitle: "Why a production retrieval system lives or dies on the telemetry and evaluation wrapped around it, not the prompt at its center."
date: 2026-10-14
author: "Yeriko Vargas"
tags: ["RAG", "Agents", "Architecture"]
canonical_url: "https://customaimodels.com/articles/rag-production-architecture/"
---

# RAG isn't a feature. It's an architecture.

Most RAG systems I see described in a sentence sound the same: embed the documents, retrieve the relevant ones, hand them to a model, get an answer. That sentence is true and it is also the least important part of the system. I've built one of these for real money, in production, since 2022, for financial decision support, paired with LSTM forecasting feeding the same decisions, and the part that took the work wasn't retrieval. It was everything wrapped around retrieval that makes it safe to trust.

## Why basic RAG chunking and vector search became a commodity

Chunking strategy, embedding model choice, vector store, reranking: this is the part with the most blog posts written about it, and it's also the part that's genuinely become a commodity. Pick a reasonable chunk size, pick a reasonable embedding model, and you'll retrieve something relevant most of the time. A retrieval-quality benchmark usually reports precision at 5 or recall at 10, numbers that look clean in a slide and tell you nothing about what happens in week 12. That's not nothing, but it's also not an architecture. It's a library call.

## Where production RAG breaks: semantic drift and stale documents

A retrieval system doesn't fail by returning nothing. It fails by returning something confident and wrong, 3 weeks after you shipped it, after the underlying documents changed shape and nobody updated the ingestion pipeline. It fails when a model grounds an answer in a document that's technically relevant and substantively stale. It fails silently, which is the only kind of failure that costs real money in a decision-support system. Hybrid search, metadata filtering and a faster vector database all help retrieval, and none of them notice that a document is relevant on paper and out of date in substance.

None of that shows up in a retrieval-quality benchmark run once before launch. It shows up in production, over weeks, as drift: in the data, in the query patterns, in what "correct" even means as the business changes around the system.

## A system that can't tell you when it's wrong isn't an AI system. It's a guess with good production values. Production RAG telemetry and continuous evaluation

Every step of the system I built, whether the call behind it goes to Claude, OpenAI, or a smaller fine-tuned model, logs what it retrieved, what it was given, what it generated, and, separately, whether that generation was later confirmed, corrected, or ignored by the person using it. That last signal is the one most teams skip, and it's the one that actually tells you if the system is getting better or quietly degrading. Evaluation isn't a notebook you run before a demo. It's a loop that runs the same way in week one and week fifty.

Concretely, that means three things live alongside the model call, not after it:

- **Grounding checks.** Does the generated answer actually trace back to the retrieved context, or did the model fill a gap with something plausible-sounding?

- **Confidence as a first-class output.** Not a number pulled from nowhere, a signal built from retrieval score, context coverage, and agreement across the forecasting side of the system where there is one.

- **Freshness next to every source.** When was the retrieved document last changed? An answer grounded in a stale document is the most dangerous kind, because it looks correct and cites its source.

- **A record of what happened after.** Was the output used, edited, or discarded? That's the only ground truth a production system ever gets.

A concrete version of this: a confidence score under 0.6 should block an unreviewed answer from reaching a client, not just get logged for later. That's one threshold, in a few lines of Python, and it does more for trust than another week of prompt tuning.

## Agents make this worse before they make it better

An agentic workflow multiplies every one of those failure points by however many steps the agent takes before it stops. 3 steps with a 10% error rate at each one compounds fast, and nobody sees it happen because every individual step looked fine in isolation. A single bad retrieval in a single-shot RAG answer is one wrong paragraph. The same bad retrieval three steps into an agent's plan can steer the entire remaining chain. The fix isn't a smarter agent. It's the same discipline applied recursively: telemetry and evaluation at every step, not just the last one, plus a way to interrupt and inspect the chain before it compounds.

## What I'd check before I trust a RAG system

If I'm evaluating someone else's system, or reviewing my own before it ships a new version, these are the questions that actually matter:

- Can I trace any answer back to the exact source it came from, in 1 click, in under 10 seconds, not a search?

- When the retrieved context is empty or weak, does the system say so, or does it generate anyway?

- Is there a number, tracked over time, for how often a human corrected the system's output?

- If the underlying documents changed today, how long until the system reflects that?

If a system can't answer those 4 questions, it isn't finished. It's a demo that happens to be running in production.

A few numbers I actually use

Drop anything under 0.3 relevance before it reaches the model. Flag anything between 0.3 and 0.6 for a human to glance at. Treat corrections above 5% of answers in a given week as a signal the pipeline needs attention, not the prompt. None of these are universal constants. They're starting points, tuned against real usage, not picked once and forgotten.

---

*Originally published at [customaimodels.com](https://customaimodels.com/articles/rag-production-architecture/).*
