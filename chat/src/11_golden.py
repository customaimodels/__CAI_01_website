"""Golden questions: each must land its top chunk in the expected corpus file. Run: python3 run.py --check"""

GOLDEN = [
    ("How much analyst time does this save?", "faq.md"),
    ("What does it cost?", "faq.md"),
    ("How much do you charge for a project?", "faq.md"),
    ("How do we get started?", "faq.md"),
    ("Do you work with small teams?", "faq.md"),
    ("Show me proof of audio work", "proof_projects.md"),
    ("Tell me about the M&A deal hub", "proof_projects.md"),
    ("How do engagements run?", "how_engagements_run.md"),
    ("What happens after the scope call?", "how_engagements_run.md"),
    ("Can you build a RAG for our deal documents?", "service_lines.md"),
    ("anomaly detection and ML pipelines", "service_lines.md"),
    ("Who is behind Custom AI Models?", "services_overview.md"),
    ("Is my data kept private and confidential?", "services_overview.md"),
    # Pricing article. The two cost queries above must stay on faq.md: it holds
    # the authoritative short answer, this doc holds the evidence behind it.
    ("What are the three price bands?", "what_custom_ai_costs.md"),
    ("Why is custom AI so expensive?", "what_custom_ai_costs.md"),
    ("Is a chatbot the same as an AI system?", "what_custom_ai_costs.md"),
    ("Why can't I just use ChatGPT?", "what_custom_ai_costs.md"),
    ("What are the add-ons priced at?", "what_custom_ai_costs.md"),
    # AI-Local Systems article.
    ("What is an AI-Local System?", "ai_local_systems.md"),
    ("Why connect AI to my website?", "ai_local_systems.md"),
]
