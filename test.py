from game_classes import *
from page import *
from dotenv import *
env_config = dotenv_values()
db_connection = psycopg2.connect(
    dbname=env_config['DATABASE_NAME'],
    user=env_config['USER_NAME'],
    password=env_config['DATABASE_PASSWORD'],
    host=env_config['DATABASE_HOST'],
    port=env_config['PORT']
)
cursor = db_connection.cursor()
game = Game(3, db_connection)
html_page_generator(game)