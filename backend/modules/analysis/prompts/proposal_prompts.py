"""
Prompts para el análisis de propuestas
"""

# Prompt para el evaluador de criterios
CRITERION_EVALUATOR_SYSTEM_PROMPT = """
You are a senior consultant with experience in evaluating proposals against RFP criteria.
"""

def get_criterion_evaluation_prompt(criterion_title, criterion_description, relevant_text, scoring_scale_text):
    """Genera el prompt para evaluar un criterio específico"""
    return f"""
Evaluate how the proposal addresses the following RFP criterion:

CRITERION: {criterion_title}
DESCRIPTION: {criterion_description}

RELEVANT CONTEXT FROM THE PROPOSAL:
{relevant_text}

SCORING SCALE (1-5):
{scoring_scale_text}

Return your evaluation in the following JSON format:
{{
"score": (number between 1 and 5),
"justification": "Detailed justification for the score",
"strengths": ["strength 1", "strength 2", ...],
"weaknesses": ["weakness 1", "weakness 2", ...],
"confidence": (float between 0 and 1)
}}
"""

# Prompt para evaluación técnica
TECHNICAL_EVALUATION_SYSTEM_PROMPT = """
You are a technical expert with experience in evaluating the technical quality of proposals.
"""

def get_technical_evaluation_prompt(proposal_text):
    """Genera el prompt para la evaluación técnica"""
   
    
    return f"""
Evaluate the technical quality of the following proposal:

PROPOSAL:
{proposal_text}

Return your evaluation in the following JSON format:
{{
"technical_score": (number between 1 and 5),
"key_findings": ["finding 1", "finding 2", ...],
"technical_risks": ["risk 1", "risk 2", ...],
"implementation_concerns": ["concern 1", "concern 2", ...],
"technical_strengths": ["strength 1", "strength 2", ...],
"recommendations": ["recommendation 1", "recommendation 2", ...]
}}
"""

# Prompt para evaluación gramatical
GRAMMAR_EVALUATION_SYSTEM_PROMPT = """
You are a writing and grammar expert with experience in evaluating the writing quality of proposals.
"""

def get_grammar_evaluation_prompt(proposal_text):
    """Genera el prompt para la evaluación gramatical"""

    return f"""
Evaluate the writing quality of the following proposal:

PROPOSAL:
{proposal_text}

Return your evaluation in the following JSON format:
{{
"writing_quality_score": (number between 1 and 5),
"grammar_issues": ["issue 1", "issue 2", ...],
"style_issues": ["issue 1", "issue 2", ...],
"clarity_concerns": ["concern 1", "concern 2", ...],
"improvement_suggestions": ["suggestion 1", "suggestion 2", ...]
}}
"""

# Prompt para evaluación de consistencia
CONSISTENCY_EVALUATION_SYSTEM_PROMPT = """
You are a consistency analysis expert with experience in evaluating the internal coherence of proposals.
"""

def get_consistency_evaluation_prompt(proposal_text):
    """Genera el prompt para la evaluación de consistencia"""
    
    return f"""
Evaluate the internal consistency of the following proposal:

PROPOSAL:
{proposal_text}

Return your evaluation in the following JSON format:
{{
"consistency_score": (number between 1 and 5),
"contradictions": ["contradiction 1", "contradiction 2", ...],
"misalignments": ["misalignment 1", "misalignment 2", ...],
"conflicting_promises": ["conflicting promise 1", "conflicting promise 2", ...],
"recommendations": ["recommendation 1", "recommendation 2", ...]
}}
"""
