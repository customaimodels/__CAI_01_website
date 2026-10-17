---
title: "From statistics to LLMs: the same job, different tools"
subtitle: "Eight and a half years across biostatistics, deep learning, and agentic systems taught one thing: the tools changed four times. The job never did."
date: 2026-10-14
author: "Yeriko Vargas"
tags: ["Career", "Architecture"]
canonical_url: "https://customaimodels.com/articles/_04_ar_stats-to-llms_career_ai-engineering/"
---

# From statistics to LLMs: the same job, different tools

My first real analysis was mixed-effects models and survival analysis on longitudinal cardiovascular data, at Beaumont Health, during a statistics internship. My most recent is an agent framework making decisions for a financial services business. Those sound like two different careers. They're the same job, done with 4 different generations of tooling.

## Statistics first, not as a credential but a habit

An MS and BS in Applied Statistics from Oakland University gave me something more durable than any specific technique: the habit of asking what a result would look like if it were wrong, before I trust that it's right. Cox proportional hazards models and Bayesian reasoning don't come up often in a conversation about LLM agents, but the instinct they built (a result isn't true because the output looks clean) carried through every system I've built since.

## Deep learning, at the scale where it actually breaks

At FCA, I built deep learning models across roughly 250,000 vehicle configurations to optimize profitability, and the real work was reducing 108 predictors down to the 14 that actually drove the decision. That's a statistics problem wearing a deep learning coat: more inputs is not more insight, and the job of the model is as much about what it's allowed to ignore as what it attends to. At Ford, the same instinct showed up as unsupervised learning surfacing defect patterns across large-scale automotive datasets, with the pipeline work (SQL, Hadoop, AWS SageMaker) existing entirely to make that one insight reliable and repeatable.

## The throughline shows up again in fraud detection

At Soothsayer, building fraud-detection and segmentation models across automotive and insurance data meant Random Forest and clustering doing the modeling, and SHAP doing something just as important: making the finding legible to the people who had to act on it. A model that flags a high-risk location but can't say why doesn't get used. That's not a modeling failure. It's a communication failure wearing a modeling costume, and it's the same failure a RAG system has when it can't show its sources.

## The tools kept changing. The question underneath never did: can I trust this, and can I explain why. Why the jump to LLMs and agents didn't feel like a jump

Since 2022, as sole architect at Custom AI Models and on contract for an automotive supply company, the systems I've built run on retrieval, agent orchestration, and real-time decision logic instead of regressions and random forests. The statistics never left. Evaluation loops, confidence as a signal rather than an afterthought, telemetry that tells you when a system is drifting, all of that is applied statistics with a different vocabulary. The people who treat LLM engineering as a clean break from everything that came before it tend to be the ones shipping systems that can't explain themselves when something goes wrong.

## What this means if you're hiring

A lot of AI hiring right now optimizes for familiarity with the newest framework. I'd argue the better signal is whether someone has had to be accountable for a model's output before "AI" was the word anyone used for it: biostatistics, fraud detection, demand forecasting, anywhere being wrong had a cost attached. That's the background that makes someone design for the failure case first, not the demo. 8.5 years, 4 generations of tools, 1 habit that didn't change.

---

*Originally published at [customaimodels.com](https://customaimodels.com/articles/_04_ar_stats-to-llms_career_ai-engineering/).*
