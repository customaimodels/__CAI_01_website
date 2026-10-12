# Custom AI Market Pricing in 2026

Research published by CAI in the article "What Custom AI Actually Costs in 2026".
Six development firms published 2026 pricing guides; read together and converted to
one currency, they resolve into three bands. These are market ranges, not a CAI
price list. CAI quotes each engagement after a scope call.

## The three market bands

Indicative 2026 build cost, in US dollars, across the published guides:

- Band 1, simple AI chatbot: $10,000 to $30,000. Answers questions in natural
  language, with one or two systems behind it.
- Band 2, custom RAG and business chatbot: $30,000 to $70,000. Answers from the
  company's own documents, prices, policies and history.
- Band 3, advanced AI system with integrations and support: $60,000 to $150,000+.
  Takes actions, connects to live systems, and is maintained and optimised over time.

Below band 1 sits the plain FAQ widget at roughly $3,800 to $7,600, which is on a
different ladder entirely. Above band 3, full enterprise deployments are published
at $76,000 to $317,000 and up.

## What moves a build between bands

The band is decided by how much of the business the system has to understand and
safely act on. It is not decided by which AI model is behind it.

Three questions place a build:

- How much of your own information does it need to know? None, and it is band 1.
  Your documents, prices and policies, and it is band 2.
- Does it need to do things, or only say things? Actions, integrations and live
  systems are what move a project into band 3.
- Who keeps it correct next year? Every guide charges for that separately.

Most small businesses do not need band 3, and are quoted for it anyway.

## Why a chatbot and an AI system are different products

A chatbot is cheap. A widget answering from a list of pre-written responses is a
small piece of software. An AI system knows the company: it retrieves documents,
prices and policies accurately, follows the business rules and tone, connects to
the tools already in use, and stays correct as the business changes underneath it.

Same conversation box on the screen. Different thing behind it, by an order of
magnitude in engineering and in price. A quote should make clear which of the two
it is for.

## Why RAG changes the price

RAG, retrieval-augmented generation, is the step that lets a system answer from a
company's own information instead of from whatever the model absorbed in training.
Answering from a company's own information is the single biggest jump on the
ladder, and the reason is not the model. The work being paid for is selecting and
structuring the documents the system may see, building and tuning the retrieval so
it returns the right passage rather than a plausible one, an evaluation harness
that proves it keeps doing so, guardrails for what must never be said or invented,
and the authentication, logging and update paths that let it be changed safely.

One firm prices that layer alone at $25,400 to $69,900 for production. The model
subscription inside it costs a few dollars a month.

This is the step that makes a custom system expensive, and it is expensive for
reasons that have nothing to do with the model subscription. Retrieval is where a
build stops being a widget and starts being infrastructure.

## Where the money actually goes

Six blocks of work, and only one of them is the AI model:

- Business data: which documents, databases and policies the system may see.
- Retrieval: search that pulls the right context for every question.
- The model: the cheapest line on the invoice.
- Interface: the chat surface, internal tools and APIs people actually touch.
- Testing: evaluation sets and iteration, so accuracy is a number, not a feeling.
- Monitoring: logs, guardrails and adjustment as rules and teams keep changing.

Two systems can run the same model and cost wildly different amounts. The
difference is the shape and depth of the other five blocks.

## Why "just use ChatGPT or Claude" is not enough

General models are trained on the public internet. They do not know a specific
business: not its pricing rules, not its contract terms, not its edge cases, not
the tone its team uses when something has gone wrong. Used raw they generalise,
they guess, and under pressure they invent. That is survivable in an internal
brainstorm. It is not survivable in a system that talks to customers or touches
money.

Four things change that, and all four are engineering rather than licensing:
retrieval makes the model read approved content before it answers, guardrails set
what it may say and do, testing turns "it seems good" into a number, and
monitoring allows it to be tightened when the real world pushes back.

Every serious 2026 guide is organised around data, retrieval, testing and
integration, not around which model was chosen. The model is necessary. It is
nowhere near sufficient.

## What a quoted range does not include

A published range usually prices one layer, not the whole stack. A retrieval price
does not buy the website, the environment where it can be changed under
supervision with previews and rollback, the integrations, or anyone maintaining it
next year. Those are separate line items in every guide. The only honest way to
read a price is to ask what fraction of the stack it covers.

## Add-ons priced on top

Published separately, once a client asks for anything beyond conversation:

- Agentic workflows, meaning tools and multi-step execution: $20,000 to $60,000.
- Each major live-system integration: $10,000 to $30,000.
- Multimodal input: $15,000 to $40,000.
- Multi-language support: $8,000 to $25,000.
- Annual maintenance: 15 to 25 percent of the build, every year.

The first line is the one to read twice. The ability for the system to actually do
things, the step from band 2 to band 3, is priced on its own at up to $60,000.

## Running cost after launch

Build price is not the whole number. Ongoing operation is published at $1,000 to
$15,000 a month, and annual maintenance at 15 to 25 percent of the build. On a
$75,000 system that is $11,250 to $18,750 a year before anyone writes a new line
of code.

A system that is genuinely maintained carries a running cost everywhere in this
market. Any quote without one is either excluding it or hiding it.

## How serious firms structure the money

- A year-one project fee covering design, build, rollout and an agreed period of
  support, usually six to twelve months. This is the band 1, 2 or 3 number.
- Year-one support and tooling bundled into that fee.
- Optional years after that, as a separately scoped annual package rather than a
  quiet assumption.
- A reconnection fee if support stops and the client returns later, because the
  system, its data and its guardrails have to be brought back to a safe state.

## Where these numbers come from

Nine published ranges from six firms: Kellton, Cleveroad, Sharp Code, Fulminous,
Emvigo and Seven Solvers. Sterling figures were converted at one pound to $1.27.
Every figure is linked to its source page in the published article, so any of them
can be checked. Prices move; the article notes that if a guide has been revised
since, its page will say so.

The spread between the guides is not disagreement. It is six firms pricing
different products and calling them all a chatbot.

## The one line worth keeping

You are not paying for access to an AI model. You are paying to turn a general
model into a reliable system built around your business. The engineering is the
product.
