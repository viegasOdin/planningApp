import sqlite3
import pytest

# Função de exemplo para salvar dados no banco
def save_data(db_connection, data):
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS scenarios (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        description TEXT)''')
    cursor.execute('INSERT INTO scenarios (name, description) VALUES (?, ?)', (data['name'], data['description']))
    db_connection.commit()

# Função para recuperar dados
def get_data(db_connection, name):
    cursor = db_connection.cursor()
    cursor.execute('SELECT name, description FROM scenarios WHERE name = ?', (name,))
    return cursor.fetchone()

@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(':memory:')
    yield conn
    conn.close()

class TestDataProcessing:
    def test_save_mock_scenario(self, in_memory_db):
        # Dados mock
        mock_data = {'name': 'Cenário Teste', 'description': 'Descrição de teste'}
        
        # Salvar dados
        save_data(in_memory_db, mock_data)
        
        # Verificar se foi salvo corretamente
        result = get_data(in_memory_db, 'Cenário Teste')
        assert result is not None
        assert result[0] == 'Cenário Teste'
        assert result[1] == 'Descrição de teste'