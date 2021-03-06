import logging

from airflow.operators.postgres_operator import PostgresHook

from utils.hooks import PostgresUpdateApiHook


def check_validated_jokes(conn_id_extract, conn_id_load):
    logger = logging.getLogger(__name__)

    sql_get_jokes = "select joke, created_at from validate_jokes where deleted_at is null and is_joke is true"
    logger.info(f"Running postgres query: '{sql_get_jokes}'")
    conn_extract = PostgresHook(postgres_conn_id=conn_id_extract, schema="jokes-app")
    df_validated_jokes = conn_extract.get_pandas_df(sql=sql_get_jokes)

    logging.info(f"n Validated jokes: {len(df_validated_jokes)} ")
    if not df_validated_jokes.empty:

        # load validated jokes to Load connection - jokes_to_send
        conn_load = PostgresHook(postgres_conn_id=conn_id_load, schema="jokes-app")
        conn_load.insert_rows(
            table="jokes_to_send",
            rows=df_validated_jokes.values.tolist(),
            target_fields=list(df_validated_jokes.keys()),
        )

        # put soft-delete in validate_jokes
        sql_update_query = "update validate_jokes set deleted_at = NOW() where deleted_at is null and is_joke is true"
        logger.info(f"Running postgres query: '{sql_update_query}'")
        conn_extract.run(sql=sql_update_query)

        logger.info(f"Updated '{len(df_validated_jokes)}' jokes. New jokes in Jokes DB")

    else:
        logger.info("No new validated jokes to put into the DB")


def put_tags_jokes(conn_id_extract, conn_id_load):
    logger = logging.getLogger(__name__)
    sql_extract = """
    select
        jt.joke_id as id,
        string_agg(t.name, ',') as tags
    from
        joke_tags jt
    left join
        tags t
    on
        t.id = jt.tag_id
    where
        jt.joke_id in (select jts.id from jokes_to_send jts where jts.tags is null)
    group by
        jt.joke_id;
    """

    conn_extract = PostgresHook(postgres_conn_id=conn_id_extract, schema="jokes-app")
    df_joke_tags = conn_extract.get_pandas_df(sql=sql_extract)

    logging.info(f"n Jokes to update tags: {len(df_joke_tags)}")
    if not df_joke_tags.empty:
        conn_load = PostgresUpdateApiHook(postgres_conn_id=conn_id_load, schema="jokes-app")

        conn_load.update_column(table="jokes_to_send", column_name="tags", df=df_joke_tags, id_column_name="id")
        logger.info(f"Done updating tags for '{len(df_joke_tags)}' jokes")
    else:
        logger.info("No new tags for jokes")
