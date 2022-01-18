import sqlite3
import os
import sys

from constant import DATABASE_NAME
# utility functions for manipulating the database
# aka abstracting away all the sql


def database_connection():
    return sqlite3.connect(DATABASE_NAME)


def get_user(id):
    with database_connection() as conn:
        conn.row_factory = lambda c, r: dict(
            [(col[0], r[idx]) for idx, col in enumerate(c.description)])
        cursor = conn.cursor()
        sql = 'SELECT * FROM Users WHERE id=?'
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        conn.commit()
        if row:
            return row[0]
        else:
            return None


def get_users():
    with database_connection() as conn:
        cursor = conn.cursor()
        sql = f'SELECT id FROM Users'
        cursor.execute(sql)
        row = cursor.fetchall()
        conn.commit()
        if row:
            return [x[0] for x in row]
        else:
            return None


def update_user(id, field, value):
    with database_connection() as conn:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # really scuffed, dynamic type abuse
        if type(value) == str:
            sql = f'UPDATE Users SET {field}="{value}" WHERE id=?'
        else:
            sql = f'UPDATE Users SET {field}={value} WHERE id=?'
        cursor.execute(sql, (id,))
        conn.commit()


def get_field(id, field):
    with database_connection() as conn:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = lambda c, r: dict(
            [(col[0], r[idx]) for idx, col in enumerate(c.description)])
        cursor = conn.cursor()
        sql = f'SELECT * FROM Users WHERE id = ?'
        cursor.execute(sql, (id,))
        entry = cursor.fetchone()
        return entry[field]


def increment_field(id, field):
    entry = get_field(id, field)
    update_user(id, field, entry + 1)


def add_user(id):
    with database_connection() as conn:
        cursor = conn.cursor()
        # reset user if they reregister
        if get_user(id) != None:
            update_user(id, "error_count", 0)
            update_user(id, "active", "")
        else:
            sql = f'INSERT INTO Users(id) VALUES(?)'
            cursor.execute(sql, (id,))
            conn.commit()


def add_error(id, error):
    with database_connection() as conn:
        sql = f'INSERT INTO Errors(id, error) VALUES(?, ?)'
        conn.execute(sql, (id, error))
        conn.commit()


def remove_user(id):
    with database_connection() as conn:
        sql = f'DELETE FROM Users WHERE id=?'
        conn.execute(sql, (id,))
        conn.commit()


# TODO: Unit testing
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--test":
            print(get_field("fi14v4phgvmdiqk3g5t7cwsvz", "last_playlist"))



# def init_database():
#     conn = sqlite3.connect(DATABASE_NAME)
#     cursor = conn.cursor()
#     cursor.execute(
#         ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='Users' ''')
#     if cursor.fetchone()[0] == 0:
#         conn.execute(''' CREATE TABLE Users(
#             id TEXT,
#             update_count INTEGER DEFAULT 0,
#             error_count INTEGER DEFAULT 0,
#             last_error TEXT DEFAULT "",
#             last_playlist TEXT DEFAULT "",
#             last_update TEXT DEFAULT ""
#         ) ''')

#         print("Created table")
#         for filename in os.listdir(CACHE_PATH):
#             id = filename[len(".cache-"):]
#             add_user(id)

#     conn.execute(''' CREATE TABLE IF NOT EXISTS Errors (
#         id text
#             constraint Errors_Users_id_fk
#                 references Users (id),
#         error text
#     )''')
#     conn.close()
