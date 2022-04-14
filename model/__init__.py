from sqlalchemy import create_engine

engine = create_engine("sqlite:///database.db", echo=False)
connection = engine.raw_connection()
cursor = connection.cursor()
