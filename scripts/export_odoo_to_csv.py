#!/usr/bin/env python3
"""
Export Odoo HR employees to CSV for MidPoint import
"""
import csv
import xmlrpc.client

# Configuration Odoo
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USERNAME = "midpoint_service"
ODOO_PASSWORD = "midpoint123"

def connect_odoo():
    """Connect to Odoo"""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    
    if not uid:
        raise Exception("Failed to authenticate to Odoo")
    
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def export_employees_to_csv(output_file='/srv/projet/iam-iga-tp/data/hr/hr_clean.csv'):
    """Export employees to CSV"""
    print(f"🚀 Connecting to Odoo at {ODOO_URL}...")
    uid, models = connect_odoo()
    print("✅ Connected!")
    
    # Search for all employees
    print("📋 Fetching employees...")
    employee_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'hr.employee', 'search',
        [[]]
    )
    
    print(f"   Found {len(employee_ids)} employees")
    
    # Read employee data
    employees = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'hr.employee', 'read',
        [employee_ids],
        {'fields': ['id', 'name', 'work_email', 'department_id', 'job_title', 'active']}
    )
    
    # Write to CSV
    print(f"📝 Writing to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['personalNumber', 'givenName', 'familyName', 'email', 'department', 'title', 'status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for emp in employees:
            # Split name into first and last
            name_parts = emp['name'].split(' ', 1)
            given_name = name_parts[0] if name_parts else 'Unknown'
            family_name = name_parts[1] if len(name_parts) > 1 else 'Unknown'
            
            # Get department name
            department = emp['department_id'][1] if emp['department_id'] else 'Unassigned'
            
            # Prepare row
            row = {
                'personalNumber': str(1000 + emp['id']),
                'givenName': given_name,
                'familyName': family_name,
                'email': emp['work_email'] or f"{given_name.lower()}.{family_name.lower()}@example.com",
                'department': department,
                'title': emp['job_title'] or 'Employee',
                'status': 'Active' if emp['active'] else 'Suspended'
            }
            
            writer.writerow(row)
            print(f"   ✓ {emp['name']}")
    
    print(f"\n✅ Export completed! {len(employees)} employees written to {output_file}")
    print(f"\n📂 You can now view the file:")
    print(f"   cat {output_file}")

if __name__ == '__main__':
    try:
        export_employees_to_csv()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
