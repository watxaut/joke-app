import logging

import src.db.core as db


def put_validated_jokes_in_joke_db():

    logger = logging.getLogger(__name__)

    conn = db.get_jokes_app_connection()

    logger.info("Select validated jokes")
    sql_query = "select * from validate_jokes where deleted_at is null and is_joke is true"
    df_validated_jokes = db.execute_read(conn, sql_query)

    if not df_validated_jokes.empty:

        # drop columns that we do not want and rename cols
        col_exclude = [
            "id",
            "hash_id",
            "user_str_id",
            "user_name",
            "is_joke",
            "validated_by_user_id",
            "updated_at",
            "deleted_at",
        ]
        df_jokes = df_validated_jokes.drop(columns=col_exclude)

        # add all the records to Jokes DB
        db.add_records(conn, "jokes_to_send", df_jokes)

        # put soft-delete in validate_jokes
        update_query = "update validate_jokes set deleted_at = NOW() where deleted_at is null and is_joke is true"
        db.execute_update(conn, update_query)

        logger.info("Updated '{}' jokes. New jokes in Jokes DB".format(len(df_jokes.index)))

    else:
        logger.info("No new validated jokes to put into the DB")

    return True
