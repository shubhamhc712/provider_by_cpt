#Check for balcklisted terms
BLACKLIST = [
    "reveral" , "guideline", "you are a", "<script", "'''", "configuration", "ignore", "disregard",
    "initial", "command", "bypass", "secret", "private", "sentive", "disclose", "expose", "hidden",
    "backdoor", "exploit", "debug", "admin", "root", "access", "dump", "extract", "leak","hack", "breach",
    "credentials","probe","intercept","monitor","traceback","stack","meta","metadata","source code","variable",
    "environment","directive","compile","runtime","execute","shell","script>","macro","payload","vector",
    "yaml.load","xml.parse","bin/bash","base64","curl"  
]

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
    
    #CHECK FOR BALCKLISTED TERMS
    if any(term in text_lower for term in blacklist):
        return "Your question contain term that cannot be processed. Please rephrese"
    
    return None