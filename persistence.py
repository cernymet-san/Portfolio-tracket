import sqlite3

class PortfolioDatabase:
    def __init__(self, db_name='portfolio.db'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            value REAL NOT NULL
        )''')
        self.connection.commit()

    def add_asset(self, name, amount, value):
        self.cursor.execute('''INSERT INTO assets (name, amount, value) VALUES (?, ?, ?)''', (name, amount, value))
        self.connection.commit()

    def view_portfolio(self):
        self.cursor.execute('''SELECT * FROM assets''')
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()