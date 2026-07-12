from langchain_core.prompts import ChatPromptTemplate

RESEARCH_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert research assistant. Your task is to take a user's research question "
                "and generate 2-3 distinct, non-redundant, and highly targeted search queries. "
                "These queries should be designed to gather comprehensive coverage of the topic from different angles. "
                "Do not simply restate the question. Focus on key terms, concepts, and synonyms."
            ),
        ),
        ("user", "Research question: {question}"),
    ]
)
