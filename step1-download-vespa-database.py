#!/usr/bin/env python

import json
import os

import psycopg
from psycopg.rows import namedtuple_row
from tqdm import tqdm
from vespa.application import Vespa

# import jq
# from vespa.io import VespaQueryResponse

# document_set = "8th EAP 2023 progress report"
# document_id = "https://water.europa.eu/freshwater/europe-freshwater/water-framework-directive/surface-water-chemical-status/priority-substances-causing-failure-to-good-chemical-status/de-3rd-cybutryne"

url = "http://10.50.5.60:64797/"
app = Vespa(url=url)

db_config = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "password",
    "host": "10.50.5.60",
    "port": 59124
}

EMPTY = ['no-document-set']


def extract_document_ids():
    conn = psycopg.connect(**db_config, row_factory=namedtuple_row)
    ids = []
    with conn.cursor() as cur:
        # Example query
        cur.execute("SELECT * FROM document")
        rows = cur.fetchall()

        # Process results
        for row in rows:
            # print(f"ID: {row.id}")
            ids.append(row.id)

    with open("document_ids.json", "w") as f:
        json.dump(ids, f)

    conn.close()


def download_document(document_id, session):
    query = f"""
        select *
        from sources *
        where document_id in ("{document_id}")
        order by chunk_id
        limit 400
    """
    try:
        response = session.query(yql=query)
    except Exception:
        print(f"Error in {document_id}")
        return
    assert response.is_successful()
    data = response.get_json()

    for chunk in data['root'].get('children', []):
        for document_set in chunk['fields'].get('document_sets', EMPTY):
            parent = os.path.join('data-download', document_set)
            if not os.path.exists(parent):
                os.makedirs(parent)
            fname = f"{chunk['id']}.json"
            with open(os.path.join(parent, fname), 'w') as f:
                json.dump(chunk, f)
                # print(f"Downloaded {chunk['id']}")


def download_database():
    print("Extracting document ids")
    extract_document_ids()

    document_ids = None

    with open('document_ids.json') as f:
        document_ids = json.load(f)

    print(f"Got {len(document_ids)} documents")

    for i in tqdm(range(len(document_ids)), desc="Downloading documents"):
        with app.syncio() as session:
            doc_id = document_ids[i]
            download_document(doc_id, session)

if __name__ == "__main__":
    download_database()
