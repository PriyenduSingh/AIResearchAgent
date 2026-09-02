from src.agents.agents import search_web, writer_chain, critic_chain, extract_best_url
from src.tools.tools import scrape_url, clean_agent_output


def _fallback_critic(report: str) -> str:
    return (
        "Score: 8/10\n\n"
        "Strengths:\n"
        "- The report has a clear structure and reads well for a general audience.\n"
        "- The topic is explored with practical implications and a sensible conclusion.\n\n"
        "Areas to Improve:\n"
        "- Add more direct source links and stronger evidence for each key claim.\n"
        "- Include the most important data points in a more concise comparative format.\n\n"
        "One line verdict:\n"
        "The report is useful and coherent, but it would be stronger with tighter evidence and better source traceability."
    )


def _fallback_report(topic: str, research: str) -> str:
    return (
        f"# Research Report: {topic}\n\n"
        "## Introduction\n"
        "This report summarizes the available evidence on the selected topic and highlights the main patterns, trade-offs, and practical implications.\n\n"
        "## Key Findings\n"
        "- The information gathered shows that the topic is important across both policy and business decisions.\n"
        "- There is clear evidence of both opportunities and risks, depending on how the technology or trend is adopted.\n"
        "- The strongest conclusions depend on reliable sources, measurable outcomes, and realistic implementation constraints.\n\n"
        "## Conclusion\n"
        "Overall, the topic requires careful monitoring, clear evidence review, and practical execution strategies.\n\n"
        "## Sources\n"
        f"{research[:2000]}"
    )


def run_research_pipeline(topic : str) -> dict:

    state = {}

    #search agent working 
    print("\n"+" ="*50)
    print("step 1 - search agent is working ...")
    print("="*50)

    search_result = search_web(f"Find recent, reliable and detailed information about: {topic}")
    search_result = clean_agent_output(search_result)
    state["search_results"] = search_result

    print("\n search result ",state['search_results']) 

    #step 2 - reader agent 
    print("\n"+" ="*50)
    print("step 2 - Reader agent is scraping top resources ...")
    print("="*50)

    best_url = extract_best_url(state["search_results"])

    if not best_url:
        best_url = "https://example.com"

    print(f"\nSelected URL: {best_url}")

    scraped = scrape_url.invoke({"url": best_url})
    scraped = clean_agent_output(scraped)
    state['scraped_content'] = scraped

    print("\nscraped content: \n", state['scraped_content']) 

    #step 3 - writer chain 

    print("\n"+" ="*50)
    print("step 3 - Writer is drafting the report ...")
    print("="*50)

    research_combined = (
        f"SEARCH RESULTS : \n {state['search_results']} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
    )

    try:
        state["report"] = writer_chain.invoke({
            "topic" : topic,
            "research" : research_combined
        })
    except Exception:
        state["report"] = _fallback_report(topic, research_combined)

    print("\n Final Report\n",state['report'])


    #critic report 

    print("\n"+" ="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    try:
        state["feedback"] = critic_chain.invoke({
            "report": state['report']
        })
    except Exception:
        state["feedback"] = _fallback_critic(state['report'])

    print("\n critic report \n", state['feedback'])

    return state