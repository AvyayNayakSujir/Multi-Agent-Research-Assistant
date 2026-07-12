from langchain_core.prompts import ChatPromptTemplate

CRITIQUE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert research editor and fact-checker. Your task is to critique the provided research draft "
                "against the user's research query and the allowed sources.\n\n"
                "You must evaluate the draft against three criteria:\n"
                "1. Completeness: Does it fully answer the original research query?\n"
                "2. Clarity & Structure: Is the draft well-structured, logical, and easy to read?\n"
                "3. Factual Grounding (Crucial): Is every factual claim in the draft strictly supported by the provided sources? "
                "You must verify that no information has been fabricated, hallucinated, or extrapolated beyond the sources.\n\n"
                "If the draft contains any unsupported claims, generic formatting issues, or incomplete answers, "
                "set approved to False and write specific, actionable feedback detail (pointing out exactly which paragraph "
                "or claim is unsupported or what part of the query was missed). If the draft is completely accurate and "
                "grounded, set approved to True and provide a brief positive feedback statement."
            ),
        ),
        (
            "user",
            (
                "Research Query: {query}\n\n"
                "Research Draft:\n{draft}\n\n"
                "Provided Sources:\n{sources_context}"
            ),
        ),
    ]
)
