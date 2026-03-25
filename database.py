import sqlite3
import csv
import io

def init_db():
    conn = sqlite3.connect('unemployment.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            governorate TEXT,
            unemployment_rate REAL,
            age INTEGER,
            job TEXT,
            employment_date TEXT,
            death_date TEXT,
            imprisonment_status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def update_from_csv(file_content: bytes):
    conn = sqlite3.connect('unemployment.db')
    c = conn.cursor()
    c.execute('DELETE FROM persons')
    stream = io.StringIO(file_content.decode('utf-8'))
    reader = csv.DictReader(stream)
    for row in reader:
        c.execute('''
            INSERT INTO persons 
            (name, governorate, unemployment_rate, age, job, employment_date, death_date, imprisonment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['الاسم'], row['المحافظة'], float(row['نسبة_البطالة']),
            int(row['العمر']), row['المهنة'], row['تاريخ_التوظيف'],
            row['تاريخ_الوفاة'], row['حالة_السجن']
        ))
    conn.commit()
    conn.close()
    return reader.fieldnames

def get_person_info(governorate, name):
    conn = sqlite3.connect('unemployment.db')
    c = conn.cursor()
    c.execute('''
        SELECT name, unemployment_rate, age, job, employment_date, death_date, imprisonment_status
        FROM persons
        WHERE governorate = ? AND name = ?
    ''', (governorate, name))
    result = c.fetchone()
    conn.close()
    return result
