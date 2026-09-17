---
name: research
description: Researching a question on the web and answering with sources. Use it for every question about people, companies, current events, recent releases, prices, exchange rates, facts you are not sure of or anything after your training data, and whenever the user asks you to look something up or read a URL.
---

# Research

Answer only from what you find on the web, never from memory. Researching needs a way to search
the web and a way to read a web page. If you cannot do both, tell the user that you cannot
research the question right now instead of answering.

## Workflow

1. **Plan.** Work out which facts the answer needs, and write one short keyword query for each,
   at most three. A query is a few keywords, e.g. `euro dollar exchange rate`, not a full
   sentence. If the user gave a URL, skip to step 4 with that URL.
2. **Search** the web for the first query. Ask for 5 results, and never more than 10.
3. **Select** the results whose title and description best match the question.
   Prefer official sites, primary sources and recent pages over forums and aggregators.
4. **Read** the best result, using its URL exactly as the search result or the user's message
   gives it. Read at most 4,000 characters of the page, and only raise that, up to 8,000, when the
   part you need was cut off. Read a second page only if the first one does not answer the
   question or you need to confirm an important fact. Never read more than three pages for one
   question.
5. **Repeat** steps 2 to 4 for the other queries, if any facts are still missing.
6. **Answer** as described below.

## Answering

- Start with a direct answer to the question, then give the supporting facts.
- Put the source URL after each fact, and use only facts from the search results and pages you read.
- If sources disagree, say so and name the more recent or more official one.
- If you could not find the answer, say what you searched for instead of guessing.

## Errors

- If a search fails instead of returning results, do not repeat it: tell the user that web search
  is unavailable right now and say what you were trying to look up.
- A search that returns no results has not failed. Try one different wording, then say you found
  nothing.
- If a page cannot be read, for example because access is denied, read the next result instead,
  or search again for a different source. Never fall back to memory.
