import spacy
import re

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def nlp_to_opensearch_query(nlp_query):
    # Define field mappings
    field_mappings = {
        "ip": "ip.keyword",
        "country": "geo.country_name.keyword",
        "continent": "geo.continent_name.keyword",
        "city": "geo.city_name.keyword",
        "port": "port",
        "signature": "engine01.eve.alert.signature.keyword",
        # Agent mappings
        "agent name": "agent.name.keyword",
        "agent version": "agent.version.keyword",
        "agent hostname": "agent.hostname.keyword",
        "agent id": "agent.id.keyword",
        "agent type": "agent.type.keyword",
        # User agent mappings
        "user agent": "user_agent.original.keyword",
        "user agent name": "user_agent.name.keyword",
        "user agent version": "user_agent.version.keyword",
        "user agent device": "user_agent.device.name.keyword",
    }

    prefixes = ["source", "destination"]
    ignore_words = ["is", "are", "=", "equal", "equals", "and", "with"]

    tokens = custom_tokenize(nlp_query)

    must_clauses = []
    should_clauses = []
    current_prefix = None
    current_field = None
    current_values = []
    is_or_condition = False

    i = 0
    while i < len(tokens):
        token = tokens[i].lower()
        
        if token == 'or':
            is_or_condition = True
            i += 1
            continue

        if i + 2 < len(tokens) and f"{token} {tokens[i+1].lower()} {tokens[i+2].lower()}" in field_mappings:
            if current_field and current_values:
                clause = create_clause(current_prefix, current_field, clean_values(current_values), field_mappings, is_or_condition)
                add_clause(must_clauses, should_clauses, clause, current_field, is_or_condition)
            current_field = f"{token} {tokens[i+1].lower()} {tokens[i+2].lower()}"
            current_values = []
            i += 3
        elif i + 1 < len(tokens) and f"{token} {tokens[i+1].lower()}" in field_mappings:
            if current_field and current_values:
                clause = create_clause(current_prefix, current_field, clean_values(current_values), field_mappings, is_or_condition)
                add_clause(must_clauses, should_clauses, clause, current_field, is_or_condition)
            current_field = f"{token} {tokens[i+1].lower()}"
            current_values = []
            i += 2
        elif token in prefixes:
            current_prefix = token
            i += 1
        elif token in field_mappings:
            if current_field and current_values:
                clause = create_clause(current_prefix, current_field, clean_values(current_values), field_mappings, is_or_condition)
                add_clause(must_clauses, should_clauses, clause, current_field, is_or_condition)
            current_field = token
            current_values = []
            i += 1
        elif token in ignore_words:
            i += 1
        else:
            current_values.append(token)
            i += 1

    if current_field and current_values:
        clause = create_clause(current_prefix, current_field, clean_values(current_values), field_mappings, is_or_condition)
        add_clause(must_clauses, should_clauses, clause, current_field, is_or_condition)

    query = {"query": {"bool": {}}}
    if must_clauses:
        query["query"]["bool"]["must"] = must_clauses
    if should_clauses:
        query["query"]["bool"]["should"] = should_clauses
        query["query"]["bool"]["minimum_should_match"] = 1

    return query

def create_clause(prefix, field, values, field_mappings, is_or_condition):
    full_field = f"{prefix}.{field_mappings[field]}" if prefix and field != "agent name" else field_mappings.get(field, field)
    
    if "port" in full_field:
        values = [int(v) for v in values if v.isdigit()]
    elif "ip" in full_field:
        values = [v for v in values if is_valid_ip(v)]
    
    if is_or_condition and "ip" in full_field:
        return [{"term": {full_field: value}} for value in values]
    elif len(values) == 1:
        return {"term": {full_field: values[0]}}
    elif len(values) > 1:
        return {"terms": {full_field: values}}
    else:
        return None

def add_clause(must_clauses, should_clauses, clause, field, is_or_condition):
    if clause:
        if is_or_condition and "ip" in field:
            should_clauses.extend(clause)
        else:
            must_clauses.append(clause)

def clean_values(values):
    return [v.strip() for v in ' '.join(values).replace(',', ' ').split() if v.strip()]

def custom_tokenize(text):
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    parts = re.split(f'({ip_pattern}|\s+)', text)
    return [part for part in parts if part.strip()]

def is_valid_ip(ip):
    try:
        parts = ip.split('.')
        return len(parts) == 4 and all(0 <= int(part) < 256 for part in parts)
    except ValueError:
        return False