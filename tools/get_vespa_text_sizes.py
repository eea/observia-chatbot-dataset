import os
import psycopg
from psycopg.rows import namedtuple_row

from vespa.application import Vespa

vespa_url = os.environ["VESPA_URL"]
app = Vespa(url=vespa_url)

pg_dbname = os.environ["PG_DBNAME"]
pg_user = os.environ["PG_USER"]
pg_password = os.environ["PG_PASSWORD"]
pg_host = os.environ["PG_HOST"]
pg_port = os.environ["PG_PORT"]

db_config = {
    "dbname": pg_dbname,
    "user": pg_user,
    "password": pg_password,
    "host": pg_host,
    "port": pg_port,
}


def extract_document_ids():
    conn = psycopg.connect(**db_config, row_factory=namedtuple_row)
    ids = []
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM document")
        rows = cur.fetchall()

        for row in rows:
            ids.append(row.id)


    conn.close()

    return ids

def get_doc_size(document_id, session):
    offset = 0
    size = 400
    doc_size = 0
    total_chunk_nr = 0
    while True:
        query = f"""
            select *
            from sources *
            where document_id in ("{document_id}")
            and chunk_id >= {offset}
            order by chunk_id
            limit {size}
        """
        try:
            response = session.query(yql=query)

        except Exception:
            print(f"Error in {document_id}")
            return
        assert response.is_successful()
        data = response.get_json()
        for chunk in data["root"].get("children", []):
            doc_size += len(chunk.get("fields",[]).get("content",""))
        chunk_nr = len(data["root"].get("children", []))
        total_chunk_nr += chunk_nr
        offset += size
        if chunk_nr < 400:
            break
    return {"size":doc_size, "nr":total_chunk_nr}


document_ids = extract_document_ids()

total_size = 0
total_ids = len(document_ids)
for i in range(total_ids):
    with app.syncio() as session:
        doc_id = document_ids[i]
        info = get_doc_size(doc_id, session)
        total_size += info["size"]
        print(f"{total_ids}/{i},{doc_id},{info['size']},{info['nr']}")

print(total_size)