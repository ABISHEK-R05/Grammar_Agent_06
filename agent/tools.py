import re

# tools: JSON Schema definitions passed to the LLM so it knows what actions are available.
# tool_handlers: actual Python functions that execute each tool.
tools = {
    "analyze_text": {
        "description": "Analyze text for grammar mistakes and tone mismatches. Returns a list of identified issues.",
        "parameters": {
            "text": {"type": "string", "description": "The text to analyze"},
            "target_tone": {"type": "string", "description": "The desired tone (e.g. professional, casual)"}
        }
    },
    "rewrite_text": {
        "description": "Rewrite the given text to fix grammar and match the target tone using rule-based corrections.",
        "parameters": {
            "text": {"type": "string", "description": "Text to rewrite"},
            "instructions": {"type": "string", "description": "Specific instructions on how to rewrite (used as context)"}
        }
    }
}

# ==========================================
# GRAMMAR RULES
# Each rule is: (regex_pattern, replacement, issue_description)
# ==========================================
GRAMMAR_RULES = [
    # Pronoun / possessive errors
    (r"\bIts\b(?=\s+\w)", "It is", "Incorrect use of 'Its' (possessive) — should be 'It is'"),
    (r"\bits\b(?=\s+\w+ing|\s+very|\s+important|\s+crucial|\s+going|\s+gonna)", "it is", "Incorrect use of 'its' — should be 'it is'"),

    # Subject-verb agreement MUST come before subject-only swap rules
    # (more specific patterns first, to avoid partial matches)
    (r"\bme and my team is\b", "my team and I are", "Subject-verb disagreement — 'me and my team is' should be 'my team and I are'"),
    (r"\bme and my team are\b", "my team and I are", "Incorrect subject pronoun in 'me and my team are'"),
    (r"\bme and (the team|our team) is\b", r"\1 and I are", "Subject-verb disagreement"),
    (r"\bme and \w+ is\b", "we are", "Subject-verb disagreement"),
    (r"\bshe are\b", "she is", "Subject-verb disagreement — 'she are' should be 'she is'"),
    (r"\bhe are\b", "he is", "Subject-verb disagreement — 'he are' should be 'he is'"),
    (r"\bi is\b", "I am", "Subject-verb disagreement — 'i is' should be 'I am'"),

    # Subject-object order swap (general — runs AFTER compound rules above)
    (r"\bme and my team\b", "my team and I", "Incorrect subject pronoun — 'me and my team' should be 'my team and I'"),
    (r"\bme and (the team|our team)\b", r"\1 and I", "Incorrect subject pronoun"),

    # Informal shorthand
    (r"\bu\b", "you", "Informal shorthand 'u' — replace with 'you'"),
    (r"\bur\b", "your", "Informal shorthand 'ur' — replace with 'your'"),
    (r"\br\b", "are", "Informal shorthand 'r' — replace with 'are'"),
    (r"\bwanna\b", "want to", "Informal word 'wanna' — replace with 'want to'"),
    (r"\bgonna\b", "going to", "Informal word 'gonna' — replace with 'going to'"),
    (r"\bcuz\b", "because", "Informal word 'cuz' — replace with 'because'"),
    (r"\bbtw\b", "by the way", "Informal shorthand 'btw'"),
    (r"\bidk\b", "I do not know", "Informal shorthand 'idk'"),
    (r"\basap\b", "as soon as possible", "Informal shorthand 'asap'"),
    (r"\bASAP\b", "as soon as possible", "Informal shorthand 'ASAP'"),

    # Tone: overly informal intensifiers
    (r"\bvery crucial\b", "critical", "Redundant intensifier — 'very crucial' should be 'critical'"),
    (r"\bvery important\b", "essential", "Redundant intensifier — 'very important' should be 'essential'"),
    
    # Common typos
    (r"\beveryday\b(?=\s*$|\s*\.)", "every day", "'Everyday' is an adjective, 'every day' is an adverb of time"),
]

# Informal words that signal a non-professional tone
INFORMAL_WORDS = {"u", "ur", "r", "wanna", "gonna", "cuz", "btw", "idk", "lol",
                   "asap", "omg", "ngl", "tbh", "fyi", "plz", "pls", "thx", "ty",
                   "y'all", "ya", "yea", "yep", "nope", "rn", "tho"}

def analyze_text(parameters: dict) -> dict:
    """
    Pure Python rule-based grammar and tone analyzer.
    No external API calls — uses regex rules and word lists.
    """
    text = parameters.get("text", "")
    target_tone = parameters.get("target_tone", "professional")

    issues = []

    # Check each grammar rule
    for pattern, replacement, description in GRAMMAR_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(description)

    # Check for informal words
    words_in_text = set(re.findall(r"\b\w+\b", text.lower()))
    found_informal = words_in_text & INFORMAL_WORDS
    if found_informal:
        issues.append(f"Informal words detected: {', '.join(sorted(found_informal))}. Replace for a {target_tone} tone.")

    # Check if sentence ends with proper punctuation
    stripped = text.strip()
    if stripped and stripped[-1] not in ".!?":
        issues.append("Sentence does not end with proper punctuation.")

    if not issues:
        return {
            "issues": [],
            "verdict": "No significant issues found.",
            "status": "success"
        }

    return {
        "issues": issues,
        "issue_count": len(issues),
        "verdict": f"Found {len(issues)} issue(s) to fix for a {target_tone} tone.",
        "status": "success"
    }


def rewrite_text(parameters: dict) -> dict:
    """
    Pure Python rule-based text rewriter.
    Applies all grammar rules sequentially via regex substitution.
    No external API calls.
    """
    text = parameters.get("text", "")

    rewritten = text

    # Apply all grammar rules in order
    for pattern, replacement, _ in GRAMMAR_RULES:
        rewritten = re.sub(pattern, replacement, rewritten)

    # Capitalize the first letter
    if rewritten:
        rewritten = rewritten[0].upper() + rewritten[1:]

    # Ensure sentence ends with a period if it doesn't end with punctuation
    rewritten = rewritten.strip()
    if rewritten and rewritten[-1] not in ".!?":
        rewritten += "."

    return {
        "rewritten_text": rewritten,
        "original_text": text,
        "status": "success"
    }


# Map action names to pure Python handler functions
tool_handlers = {
    "analyze_text": analyze_text,
    "rewrite_text": rewrite_text
}
