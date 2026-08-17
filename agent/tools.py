import re
import math
import language_tool_python

# Lazy-load the grammar tool so it doesn't block script startup unnecessarily
_grammar_tool = None

def get_tool():
    global _grammar_tool
    if _grammar_tool is None:
        print("\n[System] Initializing LanguageTool (this may download a Java server on first run)...")
        _grammar_tool = language_tool_python.LanguageTool('en-US')
    return _grammar_tool

# tools: JSON Schema definitions passed to the LLM so it knows what actions are available.
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

# Informal words that signal a non-professional tone (kept from previous implementation)
INFORMAL_WORDS = {"u", "ur", "r", "wanna", "gonna", "cuz", "btw", "idk", "lol",
                   "asap", "omg", "ngl", "tbh", "fyi", "plz", "pls", "thx", "ty",
                   "y'all", "ya", "yea", "yep", "nope", "rn", "tho"}


def analyze_text(parameters: dict) -> dict:
    """
    Analyzes text using language_tool_python.
    """
    text = parameters.get("text", "")
    target_tone = parameters.get("target_tone", "professional")
    
    tool = get_tool()
    matches = tool.check(text)
    
    issues = [f"{m.message} (Context: '{m.context}')" for m in matches]
    
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
            "status": "success",
            "issue_count": 0
        }
        
    return {
        "issues": issues,
        "issue_count": len(issues),
        "verdict": f"Found {len(issues)} issue(s) to fix for a {target_tone} tone.",
        "status": "success"
    }


def rewrite_text(parameters: dict) -> dict:
    """
    Rewrites text using language_tool_python.
    To preserve the 'Agentic Loop' demo requirement, this tool is artificially
    constrained to only fix half of the errors per iteration (rounded up). 
    This forces the agent to loop and reflect multiple times for complex sentences.
    """
    text = parameters.get("text", "")
    tool = get_tool()
    
    # First, handle informal words using simple regex replacement
    # to ensure they are cleaned up alongside strict grammar.
    rewritten = text
    lower_words = set(re.findall(r"\b\w+\b", rewritten.lower()))
    if lower_words & INFORMAL_WORDS:
        replacements = {
            r"\bu\b": "you", r"\bur\b": "your", r"\br\b": "are", 
            r"\bwanna\b": "want to", r"\bgonna\b": "going to", r"\bcuz\b": "because",
            r"\bidk\b": "I do not know", r"\basap\b": "as soon as possible"
        }
        for pattern, repl in replacements.items():
            rewritten = re.sub(pattern, repl, rewritten, flags=re.IGNORECASE)
    
    # Now run the grammar engine
    matches = tool.check(rewritten)
    
    if matches:
        # MAGIC TRICK: Only fix a subset of the errors per loop iteration!
        num_to_fix = max(1, math.ceil(len(matches) / 2.0))
        matches_to_apply = matches[:num_to_fix]
        
        # language_tool_python automatically handles applying replacements backwards
        rewritten = language_tool_python.utils.correct(rewritten, matches_to_apply)
        
    # Capitalize the first letter safely
    if rewritten and rewritten[0].islower():
        rewritten = rewritten[0].upper() + rewritten[1:]
        
    # Ensure sentence ends with a period if it doesn't end with punctuation
    rewritten = rewritten.strip()
    if rewritten and rewritten[-1] not in ".!?":
        rewritten += "."
        
    return {
        "rewritten_text": rewritten,
        "original_text": text,
        "status": "success",
        "total_matches": len(matches) if matches else 0
    }

tool_handlers = {
    "analyze_text": analyze_text,
    "rewrite_text": rewrite_text
}
