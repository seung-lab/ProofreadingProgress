from logging import root
from sqlalchemy import create_engine
from sqlalchemy import Column, String, BigInteger, Boolean
from sqlalchemy import MetaData, Table, text
import pandas as pd
import os

#SET ENVIRONMENTAL VARIABLES
os.environ['SECRET'] = 'C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//secret.txt'
os.environ['DATACSV'] = 'C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//cell_temp.csv'

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
        Column('published', Boolean, nullable=False)
    )
    meta.create_all(conn)

def import_csv(conn, path, exists ='append'):
    data = pd.read_csv(path)
    publish(conn, data, exists)

def connect_db(show = False):
    return create_engine(f"postgresql://postgres:{get_password()}@localhost:6000/{table_name}", echo=show)

def isPublished(conn, root_id):
    result = conn.execute(text(f'SELECT publish FROM "{table_name}" WHERE root_id={root_id}'))
    return result.rowcount > 0 and result.first()[0]

"""
def arePublished(conn, root_ids):
    result = publishedDict(conn, root_ids)
    if (len(result) == len(root_ids)):
        for i in result:
            print(i)
    
    return false
"""

def publishedDict(conn, root_ids, display = False):
    str_rids = [str(int) for int in root_ids]
    id_list = ','.join(str_rids)
    result = conn.execute(text(f'SELECT root_id, publish FROM "{table_name}" WHERE root_id=ANY(ARRAY[{id_list}])'))
    dictlist = {}
    for row in result:
        if (display): print(row)
        dictlist[row[0]] = row[1]
    return dictlist

def publishRootIds(conn, dataset, root_ids, exists="append"):
    data = {}
    for i in root_ids:
        data[i] = [dataset, i, True]

    df = pd.DataFrame.from_dict(data, orient='index',
    columns=['table_id', 'root_id', 'publish'])
    publish(conn, df, exists)

def publish(conn, data, exists = "append"):
    data.to_sql(table_name, conn, if_exists=exists, index=False,
    dtype={"table_id": String(), "root_id": BigInteger(), "publish": Boolean()})

def main():
    engine = connect_db(True)

    with engine.connect() as conn:
        DATACSV = os.getenv('DATACSV')
        create_table(conn)
        result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
        for row in result:
            print(row)

        import_csv(conn, DATACSV)
        print(publishedDict(conn, [720575940619258495]))
        print(publishedDict(conn, [720575940619258000]))
        #publishRootIds(conn, "fly_31", [720575940619258000])
        #print(publishedDict(conn, [720575940619258000]))

    #for deployment: need to add the proxy as a service
table_name = "test-publish"
if __name__ == "__main__":
    main()