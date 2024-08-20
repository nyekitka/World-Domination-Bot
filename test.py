import psycopg2
from dotenv import dotenv_values
env_config = dotenv_values()

db_connection = psycopg2.connect(
    dbname=env_config['DATABASE_NAME'],
    user=env_config['USER_NAME'],
    password=env_config['DATABASE_PASSWORD'],
    host=env_config['DATABASE_HOST'],
    port=env_config['PORT']
)
cursor = db_connection.cursor()

cursor.execute("SET SCHEMA 'myschema'")
cursor.execute("SELECT * FROM Game")
print(cursor.fetchone())