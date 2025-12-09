def validate_user_input(prompt:str) -> str | None:
    """
    Validate user input against guardrails rules.
    Return error message if validation fails. None if input is valid
    """
    text_lower = prompt.lower()
    word_count = len(prompt.split())

    #check length
    if word_count > 100:
        return "Your question is too long. Please provide a concise query about provider or gap excpetion."
    
    #Check for balcklisted terms
    blacklist = [
        "reveral" , "guideline", "you are a", "<script", "'''", "configuration", "ignore", "disregard",
        "initial", "command", "bypass", "secret", "private", "sentive", "disclose", "expose", "hidden",
        "backdoor", "exploit", "debug", "admin", "root", "access", "dump", "extract", "leak",  
    ]
    if any(term in text_lower for term in blacklist):
        return "Your question contain term that cannot be processed. Please rephrese"
    
    #check for domain relevance
    domain_kewords = [
        "provider", "gap", "gap exception" , "cpt", "cpt code", "network", "state", "city", "plan", "uhc", "doctor"
        ,"clinic", "optum", "zip code", "npi", "radius"
    ]
    if not any(kw in test_lower for kw in domain_kewords):
        return "Your question is outside the scope of the provider/gap-exception domain"
    
    return None