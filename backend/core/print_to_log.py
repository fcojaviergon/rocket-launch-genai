import inspect
import re
import os
from pathlib import Path
from typing import List, Tuple, Optional

def find_print_statements(directory: str, extensions: List[str] = [".py"]) -> List[Tuple[str, int, str]]:
    """
    Find print statements in Python files.
    
    Args:
        directory: Directory to search
        extensions: File extensions to search (default: .py)
    
    Returns:
        List of tuples (file_path, line_number, line_content)
    """
    results = []
    directory_path = Path(directory)
    
    for extension in extensions:
        for file_path in directory_path.glob(f"**/*{extension}"):
            # Skip virtual environment directories
            if "venv" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if re.search(r'print\s*\(', line):
                        results.append((str(file_path), i, line.strip()))
    
    return results

def convert_print_to_log(file_path: str, line_number: int, import_added: bool = False) -> bool:
    """
    Convert a print statement to a logger call.
    
    Args:
        file_path: Path to the file
        line_number: Line number of the print statement
        import_added: Whether the import for logger has been added
    
    Returns:
        bool: True if conversion was successful
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Extract the print statement
        print_line = lines[line_number - 1]
        
        # Skip if it's a commented line
        if print_line.strip().startswith('#'):
            return False
            
        # Extract content inside print()
        match = re.search(r'print\s*\((.*)\)', print_line)
        if not match:
            return False
            
        content = match.group(1)
        
        # Determine indentation
        indentation = re.match(r'^(\s*)', print_line).group(1)
        
        # Add import if needed
        if not import_added:
            # Find the last import line
            last_import_line = 0
            for i, line in enumerate(lines):
                if re.match(r'^\s*(import|from)\s+', line):
                    last_import_line = i
            
            # Add logger import after the last import
            lines.insert(last_import_line + 1, 'from core.logging_config import get_logger\n\n')
            lines.insert(last_import_line + 2, 'logger = get_logger(__name__)\n\n')
            
            # Adjust line_number since we added lines
            line_number += 2
            
        # Replace print with logger
        log_level = "debug"  # Default to debug level
        
        # Create logger statement depending on content
        if content:
            log_statement = f"{indentation}logger.{log_level}({content})\n"
        else:
            log_statement = f"{indentation}logger.{log_level}('')\n"
        
        lines[line_number - 1] = log_statement
        
        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        return True
        
    except Exception as e:
        print(f"Error converting print to log in {file_path}: {e}")
        return False

def bulk_convert_prints(directory: str, extensions: List[str] = [".py"], dry_run: bool = True) -> None:
    """
    Bulk convert print statements to logger calls.
    
    Args:
        directory: Directory to process
        extensions: File extensions to process (default: .py)
        dry_run: If True, just report what would be changed without making changes
    """
    print_statements = find_print_statements(directory, extensions)
    
    # Group by file
    files_dict = {}
    for file_path, line_number, line_content in print_statements:
        if file_path not in files_dict:
            files_dict[file_path] = []
        files_dict[file_path].append((line_number, line_content))
    
    print(f"Found {len(print_statements)} print statements in {len(files_dict)} files")
    
    if dry_run:
        for file_path, statements in files_dict.items():
            print(f"\nFile: {file_path}")
            for line_number, line_content in statements:
                print(f"  Line {line_number}: {line_content}")
        print("\nThis was a dry run. No files were modified.")
        print("To actually convert prints to logs, run with dry_run=False")
    else:
        for file_path, statements in files_dict.items():
            print(f"Processing {file_path}...")
            import_added = False
            
            # Process in reverse order to avoid line number changes
            for line_number, _ in sorted(statements, reverse=True):
                success = convert_print_to_log(file_path, line_number, import_added)
                if success and not import_added:
                    import_added = True
                    
        print(f"Converted print statements in {len(files_dict)} files")

if __name__ == "__main__":
    # Example usage
    print("Find and report print statements:")
    bulk_convert_prints("./backend", dry_run=True)
    
    # To actually convert prints to logs:
    # bulk_convert_prints("./backend", dry_run=False) 