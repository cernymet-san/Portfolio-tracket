import sqlite3

class PortfolioDatabase:
    def __init__(self, db_name='portfolio.db'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                purchase_price REAL NOT NULL,
                date_purchased TEXT NOT NULL
            )
        ''')
        self.connection.commit()

    def add_asset(self, asset_name, quantity, purchase_price, date_purchased):
        self.cursor.execute('''INSERT INTO portfolio (asset_name, quantity, purchase_price, date_purchased) VALUES (?, ?, ?, ?)''', (asset_name, quantity, purchase_price, date_purchased))
        self.connection.commit()

    def view_portfolio(self):
        self.cursor.execute('SELECT * FROM portfolio')
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()

# Example usage:
if __name__ == '__main__':
    db = PortfolioDatabase()
    db.add_asset('Bitcoin', 1.5, 45000.0, '2026-03-05')
    print(db.view_portfolio())
    db.close()