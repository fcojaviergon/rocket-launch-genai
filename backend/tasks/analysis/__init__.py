"""
Analysis tasks module
"""
# Importar explícitamente las tareas para que Celery las descubra
from tasks.analysis.rfp_tasks import process_rfp_document
from tasks.analysis.proposal_tasks import process_proposal_document
