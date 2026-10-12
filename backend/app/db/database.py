from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from app.config import settings

#for our won db query
pool = ConnectionPool(settings.DATABASE_URL, min_size=1, max_size=10,
                      kwargs={"row_factory": dict_row}, open=False)

# For LangGraph's checkpointer (it requires these exact settings).
checkpoint_pool = ConnectionPool(settings.DATABASE_URL, min_size=1, max_size=5, open=False,
                                 kwargs={"autocommit": True, "prepare_threshold": 0,
                                         "row_factory": dict_row})