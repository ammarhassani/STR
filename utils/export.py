"""Export functionality for reports"""
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


def export_to_csv(
    data: List[Any],
    headers: List[str],
    filename: str
) -> Path:
    """
    Export data to CSV with UTF-8 BOM for Arabic support
    
    Args:
        data: List of data rows
        headers: List of column headers
        filename: Output filename
        
    Returns:
        Path to created CSV file
    """
    filepath = Path(filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)
    
    return filepath


def export_reports(
    db_manager,
    filters: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None
) -> Path:
    """
    Export reports with optional filters
    
    Args:
        db_manager: DatabaseManager instance
        filters: Optional filter dictionary
        output_dir: Output directory (default: current directory)
        
    Returns:
        Path to created CSV file
    """
    # Build query
    query = "SELECT * FROM reports WHERE is_deleted = 0"
    params = []
    
    if filters:
        if filters.get('status'):
            query += " AND status = ?"
            params.append(filters['status'])
        
        if filters.get('date_from'):
            query += " AND report_date >= ?"
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            query += " AND report_date <= ?"
            params.append(filters['date_to'])
        
        if filters.get('search_term'):
            query += """ AND (
                report_number LIKE ? OR 
                reported_entity_name LIKE ? OR 
                cic LIKE ?
            )"""
            search_pattern = f"%{filters['search_term']}%"
            params.extend([search_pattern] * 3)
    
    query += " ORDER BY report_id DESC"
    
    # Execute query
    results = db_manager.execute_with_retry(query, tuple(params))
    
    # Get column names
    headers = list(results[0].keys()) if results else []
    
    # Convert to list of lists
    data = [list(row) for row in results]
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fiu_reports_{timestamp}.csv"
    
    if output_dir:
        filepath = Path(output_dir) / filename
    else:
        filepath = Path(filename)
    
    # Export
    return export_to_csv(data, headers, str(filepath))
