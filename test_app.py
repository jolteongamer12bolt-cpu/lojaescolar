import unittest
from app import app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_finalizar_pedido_returns_json(self):
        response = self.client.post('/finalizar_pedido', data={
            'produto_nome': 'Lanche Teste',
            'produto_preco': '10.00',
            'forma_pagamento': 'PIX',
            'nome_aluno': 'Aluno Teste',
            'serie': '2A',
            'sala': 'Sala 1',
            'turno': 'Manhã'
        })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['sucesso'])
        self.assertEqual(data['resumo']['produto'], 'Lanche Teste')


if __name__ == '__main__':
    unittest.main()
