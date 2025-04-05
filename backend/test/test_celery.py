"""
Script de prueba para verificar el funcionamiento de Celery
"""
import os
import time
import sys
import logging
import uuid
from tasks.tasks import test_task, execute_pipeline

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_celery")

def test_simple_task():
    """Test simple task with default parameters"""
    logger.info("Enviando tarea de prueba...")
    task = test_task.delay()
    
    # Esperar resultado (con timeout)
    try:
        result = task.get(timeout=5)
        logger.info(f"Resultado recibido: {result}")
        return result
    except Exception as e:
        logger.error(f"Error al obtener resultado: {e}")
        return None

def test_pipeline_execution():
    """Test pipeline execution"""
    # IDs de ejemplo
    pipeline_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    execution_id = str(uuid.uuid4())
    
    logger.info(f"Ejecutando pipeline {pipeline_id} con documento {document_id} y ejecución {execution_id}...")
    task = execute_pipeline.delay(pipeline_id, document_id, execution_id)
    
    # Esperar resultado (con timeout)
    try:
        result = task.get(timeout=10)
        logger.info(f"Resultado de ejecución: {result}")
        return result
    except Exception as e:
        logger.error(f"Error en ejecución: {e}")
        return None

def main():
    """Original test function"""
    print("======================================")
    print("     TEST DE CELERY WORKER")
    print("======================================")
    print("")
    
    # 1. Enviar tarea simple
    print("1. Enviando tarea simple con mensaje: 'prueba_celery'")
    task1 = test_task.delay("prueba_celery")
    print(f"Tarea enviada con ID: {task1.id}")
    
    # Esperar resultado (con timeout de 5 segundos)
    print("Esperando resultado (5s max)...")
    try:
        result1 = task1.get(timeout=5)
        print("✅ Tarea completada!")
        print(f"Resultado: {result1}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("")
    
    # 2. Enviar tarea de pipeline
    print("2. Enviando tarea de pipeline")
    task2 = execute_pipeline.delay("test_pipeline_123", "test_document_456")
    print(f"Tarea enviada con ID: {task2.id}")
    
    # Esperar resultado (con timeout de 10 segundos)
    print("Esperando resultado (10s max)...")
    try:
        result2 = task2.get(timeout=10)
        print("✅ Pipeline completado!")
        print(f"Resultado: {result2}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("")
    print("======================================")
    print("    TEST COMPLETADO")
    print("======================================")

if __name__ == "__main__":
    # Ejecutar tests
    logger.info("=== Iniciando tests de Celery ===")
    
    # Test simple
    logger.info("\n=== Test de tarea simple ===")
    simple_result = test_simple_task()
    
    # Test de pipeline
    logger.info("\n=== Test de ejecución de pipeline ===")
    pipeline_result = test_pipeline_execution()
    
    # Resumen
    logger.info("\n=== Resumen de tests ===")
    logger.info(f"Tarea simple: {'✅ OK' if simple_result else '❌ FALLÓ'}")
    logger.info(f"Pipeline: {'✅ OK' if pipeline_result else '❌ FALLÓ'}")
    
    # Ejecutar también la prueba original
    main() 