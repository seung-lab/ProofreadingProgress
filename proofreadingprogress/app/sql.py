from logging import root
from sqlalchemy import create_engine
from sqlalchemy import Column, String, Integer, BigInteger, Boolean
from sqlalchemy import MetaData, Table, text
import pandas as pd
import os
import json

#SET ENVIRONMENTAL VARIABLES
os.environ['SECRET'] = 'C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//secret.txt'
os.environ['DATACSV'] = 'C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//cell_tempv3.csv'

def get_password():
    SECRET = os.getenv('SECRET')
    file = open(SECRET, "r")
    password = file.read()
    file.close()
    return password

def create_table(conn):
    meta = MetaData()
    Table(
        'publishtable', meta, 
        Column('root_id', BigInteger, primary_key=True),
        Column('table_id', String(100), nullable=False),
        Column('user_id', Integer, nullable=False, default=0),
        Column('published', Boolean, nullable=False),
        Column('doi', String(100), nullable=True),
        Column('paper_name', String(100), nullable=True),
    )
    meta.create_all(conn)

def import_csv(conn, path, exists = "replace"):
    data = pd.read_csv(path)
    publish(conn, data, exists)

def connect_db(show = False):
    return create_engine(f"postgresql://postgres:{get_password()}@localhost:6000/{table_name}", echo=show)

def tableDump(conn):
    return pd.read_sql_table(table_name, conn)

def isPublished(conn, root_id):
    result = conn.execute(text(f'SELECT published FROM "{table_name}" WHERE root_id={root_id}'))
    return result.rowcount > 0 and result.first()[0]



def publishedDict(conn, root_ids, display = False):
    str_rids = [str(int) for int in root_ids]
    id_list = ','.join(str_rids)

    if (len(id_list)>0): 
        result = conn.execute(text(f'SELECT * FROM "{table_name}" WHERE root_id=ANY(ARRAY[{id_list}])'))
    else:
        return {}

    dictlist = {}
    for row in result:
        if (display): print(row)
        dictlist[row[1]] = dict(row)
    return dictlist

def publishRootIds(conn, dataset, root_ids, doi = '', paper = '', exists="append", user=0):
    data = {}
    for i in root_ids:
        data[i] = [dataset, i, user, True, doi, paper]

    df = pd.DataFrame.from_dict(data, orient='index',
    columns=['table_id', 'root_id', 'user_id', 'published', 'doi', 'paper_name'])
    publish(conn, df, exists)

def publish(conn, data, exists = "append"):
    data.to_sql(table_name, conn, if_exists=exists, index=False,
    dtype={"table_id": String(), "root_id": BigInteger(), "user_id": Integer(), "published": Boolean(), "doi": String(), "paper_name": String()})

def testInit(conn):
    publishRootIds(conn, "fly_v31", [720575940635737572, 720575940606772949, 720575940630804013])

def main():
    engine = connect_db(True)

    with engine.connect() as conn:
        DATACSV = os.getenv('DATACSV')
        create_table(conn)
        import_csv(conn, DATACSV)
        result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
        for row in result:
            print(row)

        print(publishedDict(conn, [720575940621039145,720575940622573752,720575940606760643,720575940613535430], display=True))
        #publishRootIds(conn, "fly_31", [720575940619258000])
        #print(publishedDict(conn, [720575940619258000]))

    #for deployment: need to add the proxy as a service
table_name = "test-publish"
if __name__ == "__main__":
    main()