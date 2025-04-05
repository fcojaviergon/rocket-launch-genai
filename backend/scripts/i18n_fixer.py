#!/usr/bin/env python
"""
Utility to find and fix Spanish language strings in the codebase.
This helps standardize error messages for production.
"""

import os
import re
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional, Set

# Define common Spanish words/phrases to search for
SPANISH_INDICATORS = [

    # Additional Spanish indicators
    "Archivo",
    "Guardado en",
    "No encontré",
    "bytes",
    "para responder",
    "tu pregunta",
    "encontré documentos",
    "relevantes",
    "contenido",
    "Generando",
    "búsqueda",
    "documentos similares",
    "resultados similares",
    "resultados",
    "consulta",
    "usuario",
]

# Define Spanish to English replacements
REPLACEMENTS = {
    "Error in": "Error in",
    "Could not": "Could not",
    "Failed": "Failed",
    "All pipeline steps failed": "All pipeline steps failed",
    "Analyze sentiment (POSITIVE, NEGATIVE, NEUTRAL) and polarity (-1 to 1)": "Analyze sentiment (POSITIVE, NEGATIVE, NEUTRAL) and polarity (-1 to 1)",
    "POSITIVE": "POSITIVE",
    "NEGATIVE": "NEGATIVE",
    "NEUTRAL": "NEUTRAL",
    "Not found": "Not found",
    "Extract": "Extract",
    "Using": "Using",
    "polarity": "polarity",
    "Conversation not found": "Conversation not found",
    "executed with errors": "executed with errors",
    "failed": "failed",
    # Additional Spanish to English replacements
    "Archivo": "File",
    "Guardado en": "Saved in",
    "No encontré documentos relevantes para responder tu pregunta.": "No relevant documents found to answer your question.",
    "bytes": "bytes",
    "No encontré": "Not found",
    "Generando embedding para consulta": "Generating embedding for query",
    "Buscando documentos similares": "Searching similar documents",
    "Encontrados": "Found",
    "resultados similares": "similar results",
    "[Archivo {file_ext} - {file_size} bytes - Guardado en {file_name}]": "[File {file_ext} - {file_size} bytes - Saved in {file_name}]",
}

# Comment patterns to detect Spanish comments
COMMENT_PATTERNS = [
    re.compile(r'#\s*([^a-zA-Z]*[áéíóúüñÁÉÍÓÚÜÑ][^#\n]*)', re.UNICODE),  # Single line comments with Spanish accents
    re.compile(r'#\s*(.*(?:para|como|cuando|donde|porque|según|también|más|así|está|están).*)', re.UNICODE),  # Common Spanish words
    re.compile(r'"""(?:\s*\n)?(.*?)"""', re.DOTALL),  # Docstrings to check for Spanish
    re.compile(r"'''(?:\s*\n)?(.*?)'''", re.DOTALL),  # Alternative docstrings
]

def find_spanish_strings(directory: Path, extensions: List[str] = ['.py']) -> List[Tuple[Path, int, str]]:
    """
    Find Spanish strings in code files.
    
    Args:
        directory: Directory to search
        extensions: File extensions to search
        
    Returns:
        List of tuples (file_path, line_number, line_content)
    """
    results = []
    
    for ext in extensions:
        for filepath in directory.glob(f"**/*{ext}"):
            # Skip directories to ignore
            if any(part in str(filepath) for part in ['venv', '__pycache__', '.git']):
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    # Check for Spanish indicators
                    for indicator in SPANISH_INDICATORS:
                        if indicator in line:
                            results.append((filepath, i, line.strip()))
                            break
                    
                    # Check for Spanish comments
                    for pattern in COMMENT_PATTERNS:
                        if ext == '.py' and '#' in line or '"""' in line or "'''" in line:
                            matches = pattern.search(line)
                            if matches and any(c in 'áéíóúüñÁÉÍÓÚÜÑ' for c in line):
                                results.append((filepath, i, line.strip()))
                                break
    
    return results

def detect_string_type(line: str) -> str:
    """
    Detect if a line contains string literals, comments, or docstrings.
    
    Args:
        line: Line to check
        
    Returns:
        String type: 'string', 'comment', 'docstring', or 'code'
    """
    if '#' in line and not re.search(r'["\'].*#.*["\']', line):
        return 'comment'
    elif '"""' in line or "'''" in line:
        return 'docstring'
    elif re.search(r'["\']', line):
        return 'string'
    else:
        return 'code'

def fix_spanish_strings(file_path: Path, line_number: int, dry_run: bool = True) -> Optional[Tuple[str, str]]:
    """
    Fix Spanish strings in a file.
    
    Args:
        file_path: Path to the file
        line_number: Line number to fix
        dry_run: If True, don't actually modify the file
        
    Returns:
        Tuple of (original_line, new_line) if a change was made, None otherwise
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if line_number > len(lines):
        return None
        
    original_line = lines[line_number - 1]
    new_line = original_line
    
    # Detect string type to apply appropriate fixes
    string_type = detect_string_type(original_line)
    
    # Apply replacements
    for spanish, english in REPLACEMENTS.items():
        if spanish in new_line:
            new_line = new_line.replace(spanish, english)
    
    # Handle string interpolation patterns like [Archivo {file_ext} - {file_size} bytes - Guardado en {file_name}]
    file_pattern = r'\[Archivo\s+\{([^}]+)\}\s+-\s+\{([^}]+)\}\s+bytes\s+-\s+Guardado\s+en\s+\{([^}]+)\}\]'
    new_line = re.sub(file_pattern, r'[File {\1} - {\2} bytes - Saved in {\3}]', new_line)
    
    # If no changes were made, return None
    if new_line == original_line:
        return None
        
    # If this is a dry run, don't actually modify the file
    if not dry_run:
        lines[line_number - 1] = new_line
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    return (original_line.strip(), new_line.strip())

def has_spanish_characters(text: str) -> bool:
    """
    Check if text contains Spanish-specific characters.
    
    Args:
        text: Text to check
        
    Returns:
        bool: True if text contains Spanish characters
    """
    spanish_chars = 'áéíóúüñÁÉÍÓÚÜÑ¿¡'
    return any(c in spanish_chars for c in text)

def main(directory: str = './backend', dry_run: bool = True, include_comments: bool = True):
    """
    Find and fix Spanish strings in the codebase.
    
    Args:
        directory: Directory to search
        dry_run: If True, don't actually modify files
        include_comments: If True, also search for Spanish comments
    """
    directory_path = Path(directory)
    
    # Find Spanish strings
    results = find_spanish_strings(directory_path)
    
    print(f"Found {len(results)} potential Spanish strings in {len(set(r[0] for r in results))} files")
    
    # Group by file
    files_dict = {}
    for file_path, line_number, line_content in results:
        if file_path not in files_dict:
            files_dict[file_path] = []
        files_dict[file_path].append((line_number, line_content))
    
    # Fix Spanish strings
    changes = []
    for file_path, lines in files_dict.items():
        print(f"\nFile: {file_path}")
        
        file_changes = []
        for line_number, line_content in lines:
            print(f"  Line {line_number}: {line_content}")
            
            result = fix_spanish_strings(file_path, line_number, dry_run)
            if result:
                original, new = result
                file_changes.append({
                    "line": line_number,
                    "original": original,
                    "new": new
                })
                print(f"    -> {new}")
        
        if file_changes:
            changes.append({
                "file": str(file_path),
                "changes": file_changes
            })
    
    # Print summary
    if dry_run:
        print("\nThis was a dry run. No files were modified.")
        print(f"Would have made {sum(len(c['changes']) for c in changes)} changes in {len(changes)} files")
        print("To actually fix Spanish strings, run with --dry-run=False")
    else:
        print(f"\nMade {sum(len(c['changes']) for c in changes)} changes in {len(changes)} files")
    
    # Generate report
    if changes:
        report = {
            "summary": {
                "total_files": len(changes),
                "total_changes": sum(len(c['changes']) for c in changes),
                "dry_run": dry_run
            },
            "changes": changes
        }
        
        with open('i18n_fixes_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report written to i18n_fixes_report.json")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find and fix Spanish strings in the codebase")
    parser.add_argument('--directory', '-d', type=str, default='./backend', help='Directory to search')
    parser.add_argument('--dry-run', action='store_true', help='Do not modify files, just report')
    parser.add_argument('--include-comments', action='store_true', default=True, help='Also search for Spanish comments')
    
    args = parser.parse_args()
    
    main(args.directory, args.dry_run, args.include_comments) 