import os
import re
import requests

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from src.tools.tools import scrape_url, web_search

load_dotenv()


def _get_env_value(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return None


def get_llm() -> ChatGroq:
    api_key = _get_env_value("GROQ_API_KEY", "GROQ_TOKEN")
    if not api_key:
        raise RuntimeError(
            "Missing GROQ_API_KEY in .env or environment variables. "
            "Add it before running the research pipeline."
        )

    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    return ChatGroq(model=model_name, api_key=api_key, temperature=0.0)


llm = get_llm()

def build_search_agent():
    return create_react_agent(llm, tools=[web_search])

def build_reader_agent():
    return create_react_agent(llm, tools=[scrape_url])

def search_web(query: str) -> str:
    return web_search.invoke({"query": query})

reader_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research assistant. Given search results, extract only the single most relevant URL to scrape deeper. Return ONLY the URL, nothing else."),
    ("human", "Search Results:\n{search_results}\n\nBest URL to scrape:")
])

reader_chain = reader_prompt | llm | StrOutputParser()

def _is_valid_url(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=3, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


def _normalize_url_candidates(search_results: str):
    urls = re.findall(r'https?://[^\s)\]>\]"\']+', search_results)
    seen = set()
    for raw in urls:
        candidate = raw.rstrip(').,;!?:\'"')
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def extract_best_url(search_results: str) -> str:
    for candidate in _normalize_url_candidates(search_results):
        if _is_valid_url(candidate):
            return candidate

    try:
        llm_url = reader_chain.invoke({"search_results": search_results}).strip()
        for candidate in _normalize_url_candidates(llm_url):
            if _is_valid_url(candidate):
                return candidate
    except Exception:
        pass

    return ""

#writer chain 

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()




#critic_chain 

critic_prompt = ChatPromptTemplate.from_messages([
     ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()