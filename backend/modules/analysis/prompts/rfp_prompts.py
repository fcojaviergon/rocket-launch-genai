"""
Prompts para el análisis de RFPs
"""

# Prompt para extracción de criterios
CRITERIA_EXTRACTION_SYSTEM_PROMPT = """
You are a senior consultant with experience in analyzing RFPs and generating evaluation frameworks.
"""

def get_criteria_extraction_prompt(rfp_text):
    """Genera el prompt para la extracción de criterios"""
    
    return f"""
Analyze the following Request for Proposal (RFP) document and extract the key evaluation criteria for the proposals:

1. Identify 15 evaluation criteria based on the RFP requirements.
2. For each criterion:
    a) Provide a clear, specific title that reflects the core requirement.
    b) Write a detailed description that explains what exactly should be evaluated.
    c) List 3-5 key indicators that the evaluator will use to evaluate the criterion.
    d) Your task is to generate three different versions of the given criterion to retrieve relevant documents from a vector database. By generating multiple perspectives of the criterion search text, your goal is to help the next prompt to overcome some of the limitations of the distance-based similarity search.
    e) For each criterion, specify the type of evidence or information that would constitute a strong response.

Return the results in JSON format with the following structure:
{
    "criteria": [
        {{
            "title": "Specific Criterion Title",
            "description": "Detailed explanation of what should be evaluated",
            "key_indicators": [
                "Indicator 1",
                "Indicator 2",
                "Indicator 3",
                "Indicator 4",
                "Indicator 5"
            ],
              "retrieve_search_text": [
                "Retrieve search text 1",
                "Retrieve search text 2",
                "Retrieve search text 3"
            ],
            "evidence_of_strong_response": [
                "Strong response 1",
                "Strong response 2",
                "Strong response 3"
            ]
        }},
        ...
    ]
}
Ensure your response is a valid JSON object that can be parsed.
Respond in the same language as the RFP document.

Content of RFP:
{rfp_text}
"""

# Prompt para generación de framework de evaluación
FRAMEWORK_GENERATION_SYSTEM_PROMPT = """
You are a senior consultant with experience in analyzing RFPs and generating evaluation frameworks.
"""

def get_framework_generation_prompt(criteria):
    """Genera el prompt para la generación del framework de evaluación"""
    return f"""
Based on the following evaluation criteria for an RFP:
{criteria}
Please perform the following tasks:

1. Assign weights to each criterion:
    a) Allocate weights based on perceived importance
    b) Ensure weights total 100%

2. Establish a scoring scale:
    a) A score from 1-5 based on the following scale:
        1 = Poor (Does not meet requirements)
        2 = Fair (Partially meets requirements)
        3 = Good (Meets basic requirements)
        4 = Very Good (Exceeds requirements in some areas)
        5 = Excellent (Significantly exceeds requirements)
    b) Clearly define what each score represents

3. Provide a brief explanation of how to use this weighted scoring system for proposal evaluation.

Format your response as a JSON object with the following structure: 
{{
  "weighted_criteria": [
    {{
      "title": "Criterion name",
      "weight": "percentage"
    }},
    ...
  ],
  "scoring_scale": [
    {{
      "score": "number",
      "description": "Score description"
    }},
    ...
  ],
  "evaluation_guide": "Brief explanation on using the weighted scoring system"
}}
Ensure your response is a valid JSON object that can be parsed.
Respond in the same language as the criteria.
"""
