---
title: "Listening to a room in real time"
subtitle: "A production audio-intelligence platform runs on 100+ DSP features and a continuous evaluation loop, not a clever model alone. Most of the engineering is in the loop."
date: 2026-10-14
author: "Yeriko Vargas"
tags: ["Signal & ML", "Architecture"]
canonical_url: "https://customaimodels.com/articles/real-time-audio-machine-learning/"
---

# Listening to a room in real time

Not every production AI system is an LLM with a nice wrapper around it. I built one that listens to a live music venue and adapts in real time: over 100 DSP features run through PCA and KMeans into a similarity score, with a continuous evaluation loop checking its own output. No prompt anywhere in that sentence. It's still running in production, and it taught me more about what "production AI" actually means than most of the LLM work I've shipped since.

## DSP feature engineering and dimensionality reduction with PCA

A lot of current AI conversation assumes the hard problem is always "which foundation model." For a real-time audio system, the hard problem was deciding which of the 100-plus features, pulled out with Librosa, Essentia, and Aubio, actually carried signal about what was happening in the room, versus which were just correlated noise that would fall apart the moment the venue changed its sound system. Feature engineering didn't go away. It just got less fashionable. Dimensionality reduction through PCA wasn't a step before the "real" model: choosing what to keep and what to discard was most of the actual engineering judgment in the system.

The audio stack

- **The math underneath.** Short windows of sound, a fast Fourier transform (FFT) on each, and spectral features built from what comes out.

- **Librosa.** Spectral features, MFCCs, onsets and tempo.

- **Essentia.** Loudness, rhythm and tonal descriptors.

- **Aubio.** Fast onset, pitch and beat tracking, light enough to run live.

- **Feature scaling, then PCA.** 100-plus features put on one scale, then reduced to the few that carry signal.

## Unsupervised KMeans clustering for real-time audio, on purpose

There's no labeled dataset of "this is what a good night sounds like" for a specific venue, and building one would have meant months of human annotation, likely 300 to 500 labeled examples at minimum, before a single useful output. KMeans-based similarity scoring sidesteps that: the system learns the structure of what's actually happening acoustically, usually settling into somewhere between 5 and 10 real clusters, and flags what's similar to, or diverging from, established patterns, without needing someone to have hand-labeled the answer first. The tradeoff is real: unsupervised systems are harder to explain in a sentence, and they demand a different kind of evaluation than a model with ground-truth labels and a clean accuracy number.

## When there's no ground truth to score against, the evaluation loop has to become the ground truth. The evaluation loop is the actual product

Here's the part that doesn't show up in a demo: a real-time system that adapts has to be checked against itself, continuously, because the thing it's adapting to (the room, the crowd, the equipment) never holds still. A set that opens quiet and builds for 2 hours is not the same signal as a set that's loud from minute 1, and a system that scores them the same way is broken, even if nobody files a bug. That meant building a loop that doesn't just score a single moment but tracks whether the system's own similarity judgments stay coherent as conditions shift over a night, a week, a season. Without that loop, "adapts in real time" is just a phrase. With it, it's a claim you can actually stand behind, backed by weeks of logged sets, not 1 good demo night.

A few numbers from that loop

Anything inside 2 standard deviations of a cluster's center reads as normal. Anything past 3 gets flagged for review. A cluster that hasn't been hit in 14 days gets re-checked before anyone trusts it again.

## Why this is relevant even if you're hiring for LLM work

The specific techniques here (DSP feature extraction, PCA, KMeans) aren't what most companies are hiring an AI architect to build in 2026. The discipline underneath them is exactly what's missing from a lot of LLM-only engineering: treating evaluation as part of the system instead of a step you run once, being honest about when there's no ground truth and designing for that instead of pretending there is one, and reducing a noisy, high-dimensional problem to the few signals that actually matter. That's the same judgment that makes a RAG system trustworthy or an agent pipeline safe to run unattended. The tools change. The discipline doesn't.

---

*Originally published at [customaimodels.com](https://customaimodels.com/articles/real-time-audio-machine-learning/).*
