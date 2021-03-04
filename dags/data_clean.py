"""
### Data Cleaning Pipeline
A pipeline that cleans search log data.
(Based off of the Airflow 
[tutorial DAG](https://airflow.apache.org/docs/stable/tutorial.html)).
"""
from datetime import timedelta
from urllib.parse import urlparse
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.sqlite_operator import SqliteOperator

from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Connection
from airflow import settings
import pandas as pd
import sqlite3
import os

# [START default_args]
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(2),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}
# [END default_args]

# [START instantiate_dag]
dag = DAG(
    'clean_data',
    default_args=default_args,
    description='A simple tutorial DAG',
    schedule_interval=None,
)
# [END instantiate_dag]

tables = ['search_request', 'search_result_interaction']
db_con_str = os.getenv('AIRFLOW__CORE__SQL_ALCHEMY_CONN')
db_filepath = urlparse(db_con_str).path[1:]

def load_data():
    """Load the csv data into tables `search_request` and 
    `search_result_interaction` in the default db.
    """    
    # reuse the same sqlite db as airflow
    con = sqlite3.connect(db_filepath)
    
    data_dir = os.getenv('DATA_DIR')
    for table in tables:
        filename = os.path.join(data_dir, table + '.csv')
        if os.path.isfile(filename):
            df = pd.read_csv(filename)
            df.to_sql(table, con, if_exists='replace', index=False)
        else:
            raise Exception(f'{filename} does not exist')

load_data = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    dag=dag
)

"""SQL operator toy example
Demonstrates how to access the tables populated in `load_data`.
The task itself does nothing. You're most likely to use this operator
to modify the table (it doesn't return a result).
"""
for table in tables:
    summary_sql = f"""
        select count(*)
        from {table}
    """
    read_data = SqliteOperator(
        task_id=f'read_data_{table}',
        sqlite_conn_id=os.getenv('CONN_ID'),
        sql=summary_sql,
        dag=dag,
    )
    load_data >> read_data

"""Pandas DF toy example
Demonstrates how to access the tables populated in `load_data` with pandas.
If you used pandas to load/modify data, you can work off of this example.
Hmm doesn't seem super efficient. 
"""
def clean_data_df(tablename: str):
    db_con_str = os.getenv('AIRFLOW__CORE__SQL_ALCHEMY_CONN')
    con = sqlite3.connect(db_filepath)
    df = pd.read_sql(f"select * from {tablename}", con)
    
    # Drop "Unnamed" columns
    junk_columns = df.columns[df.columns.str.startswith('Unnamed')]
    df = df.drop(junk_columns, axis=1)
    
    for count, value in enumerate(df['ts']):
        if value[27:28] == '0':
            x = value[:19]
            y = value[24:]
            z = y[:3] + ':' + y[3:]
            cleaned = x + z
            df['ts'][count] = cleaned
            df['ts'] = pd.to_datetime(search_request['ts'], utc=True)
            total = df2.merge(df, on="search_id", how="left", copy=False)

    # Replace the table with a cleaned version
    

    df.to_sql(f'clean_{tablename}', con, if_exists='replace', index=False)
    
    try:
        df1 = pd.read_sql(f"select * from clean_search_result_interaction", con)
        df2 = pd.read_sql(f"select * from clean_search_request", con1)
        total = df1.merge(df2, on="search_id", how="left", copy=False)
        total = total.dropna()
        search_result_interaction = pd.DataFrame(total, columns = ['search_id', 'ts_x', 'cid', 'position'])
        search_result_interaction = search_result_interaction.rename(columns={'ts_x':'ts'})
        search_result_interaction.to_sql(f'clean_search_result_interaction', con, if_exists='replace', index=False)
    except:
        pass
    

for table in tables:
    clean_data = PythonOperator(
        task_id=f'clean_data_{table}',
        python_callable=clean_data_df,
        op_kwargs={
            'tablename': table
        },
        dag=dag,
    )
    load_data >> clean_data

# [START documentation]


load_data.doc_md = """\
#### Load Data 
This task loads data from the csv files in the data directory (set as 
an environment variable DATA_DIR) into the database Airflow creates.
"""

read_data.doc_md = """\
#### Read Data 
This task does nothing. It demonstrates how to use the SQLite operator.
"""

clean_data.doc_md =  """\ 
#### Clean Data 
This task removes a column with pandas. It demonstrates how to alter data 
and write it back into the same table.
[END documentation]
""" 
