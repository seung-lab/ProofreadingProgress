from sqlalchemy import create_engine
from sqlalchemy import text, String, BigInteger, Boolean
import pandas as pd

def get_password():
    #move to environmental variable
    file = open('C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//secret.txt', "r")
    password = file.read()
    file.close()
    return password

def create_table(conn):
    conn.execute(text("""CREATE TABLE test-publish (
        table_id TEXT NOT NULL, 
        "root_id BIGINT NOT NULL PRIMARY KEY, 
        "public BOOLEAN NOT NULL)"""
        ))

def init_table(conn):
    data = pd.read_csv('C://wamp64//www//ProofreadingProgress//proofreadingprogress//app//cell_temp.csv')
    publishRootIds(conn, '', [], "replace")
    conn.execute(f'ALTER TABLE "{table_name}" ADD PRIMARY KEY ("root_id");')
    publish(conn, data)

def connect_db(show = False):
    return create_engine(f"postgresql://postgres:{get_password()}@localhost:6000/{table_name}", echo=show)

def isPublished(conn, root_id):
    result = conn.execute(text(f'SELECT publish FROM "{table_name}" WHERE root_id={root_id}'))
    return result.rowcount > 0 and result.first()[0]

def publishedDict(conn, root_ids):
    str_rids = [str(int) for int in root_ids]
    id_list = ','.join(str_rids)
    result = conn.execute(text(f'SELECT root_id, publish FROM "{table_name}" WHERE root_id=ANY(ARRAY[{id_list}])'))
    dictlist = {}
    for row in result:
        print(row)
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
    #engine = connect_db()
    engine = connect_db(True)

    with engine.connect() as conn:
        init_table(conn)
        result = conn.execute(text(f'SELECT * FROM "{table_name}"'))
        for row in result:
            print(row)
        print(publishedDict(conn, [720575940619258495]))
        print(publishedDict(conn, [720575940619258000]))
        #publishRootIds(conn, "fly_31", [720575940619258000])
        #print(publishedDict(conn, [720575940619258000]))

    #for deployment: need to add the proxy as a service
table_name = "test-publish"
if __name__ == "__main__":
    main()