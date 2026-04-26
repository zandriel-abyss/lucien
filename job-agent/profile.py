from __future__ import annotations

from typing import Dict, List

PROFILE: Dict[str, object] = {
    "personal": {
        "name": "Jzacksline Andreela Soosaiya",
        "preferred_name": "Zack",
        "location": "Amsterdam, Netherlands",
        "experience_years": "11+",
        "positioning": [
            "FinTech Product Leader",
            "AI & Compliance Innovation",
            "RegTech, AI Risk & Financial Crime Systems",
            "Product Executive | FinTech · AI · GRC | US · EU · APAC",
        ],
    },
    "experience": [
        {
            "company": "SafeSend (acquired by Thomson Reuters)",
            "role": "Senior Product Manager -> Portfolio Lead",
            "dates": "Jul 2020 - Aug 2024",
            "markets": "US, UK, Germany / US & EU",
            "facts": [
                "Led modernization of a regulated financial compliance and payments platform.",
                "Owned strategy and delivery for a 7-product financial platform spanning tax workflows, payments, treasury, and compliance.",
                "Re-architected fragmented legacy systems into a modular API-first platform.",
                "Enabled regulatory-aligned workflows across AML/CFT, GDPR, and DORA.",
                "Supported ISO 20022-compatible transaction processing across 50+ jurisdictions.",
                "Delivered 64% product adoption growth.",
                "Delivered 35% operational efficiency gains.",
                "Improved sprint velocity by 45%.",
                "Reduced QA defects by 59%.",
                "Reduced release timelines by 15%.",
                "Built and scaled a 20+ person product organization across PMs, POs, designers, engineers, and scrum masters.",
                "Partnered with compliance, engineering, commercial leadership, C-suite, and investors.",
                "Supported acquisition readiness prior to Thomson Reuters acquisition.",
                "Owned GTM execution for two flagship overhauls.",
                "Worked on KYC, SCA, RoPA, AML/CFT-aligned compliance, secure document exchange, and audit-ready workflows.",
                "Built a unified design system and improved delivery by 25%.",
                "Redesigned tax lifecycle dashboard, reduced developer effort by 30%, and improved client satisfaction by 20%.",
                "Released an Outlook add-in improving CSAT from 2.5 to 4.1.",
            ],
        },
        {
            "company": "Anakin / racetrack.ai",
            "role": "Senior Product Owner",
            "dates": "Mar 2018 - Jun 2020",
            "markets": "India, Germany",
            "facts": [
                "Built conversational AI and identity verification systems for regulated financial onboarding.",
                "Delivered AI-driven onboarding systems for digital banks and PSPs.",
                "Integrated identity verification, fraud detection, and compliance workflows into chatbot and voice interfaces.",
                "Designed NLP intent architecture using Dialogflow and Rasa.",
                "Integrated speech-to-text and VAD segmentation.",
                "Improved onboarding adoption by 45%.",
                "Reduced bounce rates from 85% to 60%.",
                "Implemented SEPA-aligned KYC workflows.",
                "Built programmable fallback logic combining automation with agent escalation.",
                "Partnered with CRM and backend teams for secure session handoffs, audit logging, and compliance traceability.",
            ],
        },
        {
            "company": "Cognizant Technology Solutions",
            "role": "QA/BA Specialist",
            "dates": "Sep 2013 - Oct 2017",
            "markets": "US, India, Singapore",
            "facts": [
                "Built regulatory testing frameworks for high-volume banking systems.",
                "Developed automated QA frameworks for SWIFT and ACH payment processing systems.",
                "Reduced regression testing time by 60%.",
                "Increased test coverage by 31%.",
                "Translated AML and regulatory requirements into system specs and testing workflows for Tier-1 US banks and insurance institutions.",
                "Implemented audit-ready traceability for transaction monitoring rules, compliance controls, and regulatory reporting workflows.",
            ],
        },
    ],
    "education": [
        "Master's in International Finance - FinTech Specialization, University of Amsterdam, 2024-2025, GPA 8.5",
        "B.Tech Engineering & Biotechnology, Anna University, 2009-2013, GPA 8.7",
    ],
    "strategic_projects": [
        {
            "name": "AI Treasury Copilot for CFOs",
            "summary": [
                "Designed an AI-native decision engine to optimize FX timing and liquidity exposure using real-time ERP and banking data.",
                "Developed modular ML architecture to analyze invoice and payment patterns and recommend optimal transfer windows.",
                "Integrated natural hedging logic and cash visibility across jurisdictions.",
                "Conducted 15+ CFO interviews and presented MVP at FinTech Ventures.",
            ],
        },
        {
            "name": "Modular Fraud Detection Framework / Noir Framework",
            "summary": [
                "Built a multi-layered ML framework for detecting illicit wallet behavior across Ethereum and Layer-2 networks.",
                "Engineered behavioral risk signals including circular flows, dormant wallet activation, mixer interactions, and transaction bursts.",
                "Implemented Isolation Forest, DBSCAN, Random Forest, and XGBoost.",
                "Integrated SHAP explainability and symbolic risk tags for interpretable AML detection.",
            ],
        },
        {
            "name": "Programmable Voice AI Infrastructure",
            "summary": [
                "Built voice-driven AI backend enabling natural-language control of EV charging infrastructure.",
                "Implemented STT, VAD, LLM intent recognition, and TTS with orchestrated REST services.",
                "Demonstrated scalable agentic architecture reducing support workload for common faults by approximately 70%.",
            ],
        },
    ],
    "competencies": {
        "leadership": [
            "Scaling cross-functional product and engineering teams",
            "C-suite, investor, and enterprise stakeholder engagement",
            "Engineering, design, and compliance collaboration",
            "Distributed team leadership across US, EU, APAC",
        ],
        "product": [
            "Product strategy",
            "Portfolio management",
            "Roadmap leadership",
            "Discovery-to-delivery systems",
            "Agile product operations",
            "Platform modernization",
            "Modular architecture design",
            "API-first product design",
            "GTM enablement",
        ],
        "regulatory": [
            "AML/KYC/KYB",
            "GDPR",
            "DORA",
            "ISO 20022",
            "PCI-DSS",
            "SOC 2",
            "Cross-border payments",
            "Treasury",
            "Financial crime detection",
            "Audit-ready infrastructure",
        ],
        "technical": [
            "Python",
            "SQL",
            "REST APIs",
            "Git",
            "Azure DevOps",
            "Power BI",
            "Jupyter",
            "Selenium",
            "Dialogflow",
            "Rasa",
            "Deepgram",
            "AssemblyAI",
            "LangChain",
            "Semantic Kernel",
        ],
    },
}

STAR_STORIES: List[Dict[str, str]] = [
    {
        "title": "SafeSend Transformation",
        "situation": "Fragmented 7-product financial compliance and payments suite.",
        "task": "Unify systems into a scalable API-first platform.",
        "action": "Led platform modernization, modular architecture design, compliance alignment, and cross-functional execution.",
        "result": "64% adoption growth, 35% efficiency gains, 45% velocity improvement, 59% QA defect reduction, 15% faster releases, and acquisition readiness before Thomson Reuters deal.",
    },
    {
        "title": "Noir Fraud Detection",
        "situation": "Fraud detection in blockchain ecosystems is difficult due to privacy and fraud ambiguity.",
        "task": "Build an explainable ML fraud detection framework.",
        "action": "Engineered wallet features, anomaly and supervised models, SHAP explainability, and symbolic risk tags.",
        "result": "Delivered interpretable fraud detection, wallet risk scoring, and compliance-ready alert logic.",
    },
    {
        "title": "Kairo Treasury Copilot",
        "situation": "Mid-market firms face FX exposure and poor payment timing.",
        "task": "Design an AI decision-support tool for treasury optimization.",
        "action": "Used ERP/bank data concepts, FX timing models, natural hedging logic, and CFO discovery interviews.",
        "result": "Validated direction with 15+ CFO interviews and MVP showcased at FinTech Ventures.",
    },
    {
        "title": "Anakin Onboarding AI",
        "situation": "Digital onboarding had high drop-off rates.",
        "task": "Improve KYC onboarding effectiveness in regulated environments.",
        "action": "Built conversational AI with NLP, STT, VAD, fallback escalation, and compliance traceability.",
        "result": "Improved onboarding adoption by 45% and reduced bounce rate from 85% to 60%.",
    },
]

RESUME_MODES: Dict[str, Dict[str, object]] = {
    "general": {
        "label": "General Product Resume",
        "headlines": [
            "Product Executive | FinTech · AI · GRC | 11+ Yrs | US · EU · APAC",
            "FinTech Product Leader | AI & Compliance Innovation",
            "Product Leader | Payments, AI & Platform Transformation",
        ],
        "focus": "Product leadership, platform modernization, 7-product ownership, GTM, design systems, product org scaling, payments, treasury, and AI systems.",
    },
    "regtech": {
        "label": "RegTech Resume",
        "headlines": [
            "FinTech Product Leader | RegTech, AI Risk & Financial Crime Systems",
            "RegTech Product Leader | AML, AI Risk & Financial Crime Analytics",
            "AI Risk & Compliance Systems Leader | FinTech · RegTech · AML",
        ],
        "focus": "Regulated systems, AML/KYC/KYB, compliance operations, GDPR/DORA, financial crime detection, and audit-ready workflows.",
    },
    "hybrid": {
        "label": "Hybrid Resume",
        "headlines": [
            "Product Executive | FinTech Infrastructure, AI Risk & Compliance",
            "FinTech Product Leader | Payments, Compliance, and AI Transformation",
            "AI-Enabled Product Leader | Financial Infrastructure & Risk Systems",
        ],
        "focus": "Blend of product/platform leadership with AI, data, compliance, and financial infrastructure transformation.",
    },
}
