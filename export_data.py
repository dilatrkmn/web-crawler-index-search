import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "web_crawler"),
)

cursor = conn.cursor()

query = """
SELECT
    pt.term AS word,
    p.url,
    p.origin_url AS origin,
    p.depth,
    pt.frequency
FROM page_terms pt
JOIN pages p ON pt.page_id = p.id
LIMIT 1000;
"""

cursor.execute(query)

output_path = BASE_DIR / "data" / "storage" / "p.data"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    for row in cursor.fetchall():
        line = " ".join(str(x) for x in row)
        f.write(line + "\n")

cursor.close()
conn.close()

print(f"Export completed: {output_path}")