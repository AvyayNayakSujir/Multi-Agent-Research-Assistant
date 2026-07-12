from langchain_core.prompts import ChatPromptTemplate

READER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert reader and researcher. Your task is to analyze the provided scraped text "
                "and extract only the information, specific facts, figures, statistics, and claims "
                "that are directly relevant to the user's research query.\n\n"
                "Instructions:\n"
                "1. Focus on high-fidelity extraction of data (numbers, dates, names, key claims).\n"
                "2. Do not write a generic summary of the entire page; summarize/extract only what is relevant to the query.\n"
                "3. If the page does not contain any relevant information, specify that it is not relevant."
            ),
        ),
        ("user", "Research Query: {query}\n\nScraped Text:\n{text}"),
    ]
)
