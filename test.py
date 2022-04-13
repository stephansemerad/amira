from numpy import number
import pandas as pd
from sqlalchemy import create_engine
import csv

engine = create_engine("sqlite:///database.db", echo=False)
connection = engine.raw_connection()
cursor = connection.cursor()

df = pd.read_csv("./static/csv/backtesting.csv")
headers = list(df.columns.values)
data_types = list(df.dtypes.astype("str"))

print()
print(headers)
print(data_types)

number_of_headers = len(headers)

# check if table exists
table_name = "backtesting"
sql = f"SELECT name FROM sqlite_master WHERE name='{table_name}';"

cursor.execute(sql)
results = list(cursor.fetchall())
print(results)
connection.commit()


if results:
    # delete table
    sql = f"drop table {table_name}"
    cursor.execute(sql)
    connection.commit()

# create table

sql = "create table backtesting ("
for i in range(number_of_headers):
    sql += f" {headers[i]} {data_types[i]},"

sql = sql[:-1]
sql += ");"

print()
print("sql:")
print(sql)


cursor.execute(sql)
results = list(cursor.fetchall())
print(results)
connection.commit()
print("table created")

print("insert into db")
data = df.to_dict("records")
print(data)
for i in data:
    keys = [x for x in i]
    vals = ["'" + str(x) + "'" for x in i.values()]
    sql = (
        f"""insert into {table_name} ({', '.join(keys)}) values ({', '.join(vals)});"""
    )
    print(sql)

    cursor.execute(sql)
    connection.commit()

print("select table to check upload")
sql = f"select * from {table_name}"
cursor.execute(sql)
results = list(cursor.fetchall())
print(results)
connection.commit()
