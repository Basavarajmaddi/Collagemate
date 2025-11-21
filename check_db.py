import sqlite3
import os
from datetime import datetime

def check_recent_activity():
    db_path = 'college.db'
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check most recent admissions
        print("\n=== MOST RECENT ADMISSIONS ===")
        cursor.execute("""
            SELECT * FROM admissions 
            ORDER BY application_date DESC 
            LIMIT 5
        """)
        admissions = cursor.fetchall()
        
        if admissions:
            cursor.execute("PRAGMA table_info(admissions)")
            columns = [col[1] for col in cursor.fetchall()]
            print("\nFound admissions:")
            for admission in admissions:
                print("\nAdmission Details:")
                for i, col in enumerate(columns):
                    print(f"{col}: {admission[i]}")
        else:
            print("No admissions found")

        # Check recent conversations
        print("\n=== RECENT CONVERSATIONS ===")
        cursor.execute("""
            SELECT * FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        conversations = cursor.fetchall()
        if conversations:
            cursor.execute("PRAGMA table_info(conversations)")
            columns = [col[1] for col in cursor.fetchall()]
            print("\nRecent conversations:")
            for conv in conversations:
                print("\nConversation:")
                for i, col in enumerate(columns):
                    if col == 'message_content':
                        print(f"{col}: {conv[i][:100]}..." if len(conv[i]) > 100 else f"{col}: {conv[i]}")
                    else:
                        print(f"{col}: {conv[i]}")
        else:
            print("No conversations found")

        # Check student details
        print("\n=== STUDENT DETAILS ===")
        cursor.execute("""
            SELECT * FROM student_details 
            ORDER BY last_interaction DESC 
            LIMIT 5
        """)
        students = cursor.fetchall()
        if students:
            cursor.execute("PRAGMA table_info(student_details)")
            columns = [col[1] for col in cursor.fetchall()]
            print("\nStudent records:")
            for student in students:
                print("\nStudent Details:")
                for i, col in enumerate(columns):
                    print(f"{col}: {student[i]}")
        else:
            print("No student details found")

        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def check_database_structure():
    db_path = 'college.db'
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        print("\n=== DATABASE TABLES ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in database")
            return
            
        for table in tables:
            table_name = table[0]
            print(f"\n--- Table: {table_name} ---")
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Number of rows: {count}")
            
            # Show sample data if any exists
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample = cursor.fetchone()
                print("Sample row:")
                for i, col in enumerate(columns):
                    print(f"  {col[1]}: {sample[i]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_recent_activity()
    check_database_structure() 