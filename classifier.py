from client_claude import call_claude

def classify(query):
    prompt = f"""
Classify into [debug, cto, ceo, sales, default]
Return JSON: {{mode, confidence}}

Query: {query}
"""
    res = call_claude("", prompt)

    try:
        import json
        return json.loads(res)
    except:
        return {"mode": "default", "confidence": 0.5}